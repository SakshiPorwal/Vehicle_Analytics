import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import os
from bigquery import load_data_from_bigquery
from insights import generate_dynamic_insights
from insights import generate_narrative_insights

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "C:/Users/Sakshi/Documents/cker-finance-bb95088c8e3f.json"
OEM = ["Piaggio", "Altigreen", "Euler", "Bajaj", "Mahindra"]

#@st.cache_data
#def load_data(filepath):
#    return pd.read_csv(filepath)

#df = load_data('C:/Users/Sakshi/ckers/notebook/loan_completion/df')


st.title("Vehicle Analytics Dashboard")
st.sidebar.header("Filters")
oem = st.sidebar.selectbox("Select OEM (Manufacturer)", OEM)
chassis_number = st.sidebar.text_input("Enter Chassis Number", "")
date_range = st.sidebar.date_input("Select Date Range", [])

if st.sidebar.button("Enter"):
    if not chassis_number or len(date_range) != 2:
        st.error("Please enter both a chassis number and a valid date range.")
    else:
        start_date = pd.to_datetime(date_range[0]).strftime('%Y-%m-%d %H:%M:%S')
        end_date = pd.to_datetime(date_range[1]).strftime('%Y-%m-%d %H:%M:%S')

        try:
            df = load_data_from_bigquery(oem, chassis_number, start_date, end_date)

            if df.empty:
                st.error("No data available for the selected chassis number and date range.")
            else:
                st.success(f"Data loaded successfully for {oem}!")
                df['recorded_at'] = pd.to_datetime(df['recorded_at'])
                vehicle_date_range = (df['recorded_at'].min(), df['recorded_at'].max())
                st.metric(label="Vehicle Date Range", value=f"{vehicle_date_range[0].date()} to {vehicle_date_range[1].date()}")

                df_filtered = df[df['chassis_number'] == chassis_number]
                df_filtered['recorded_at'] = pd.to_datetime(df_filtered['recorded_at']).dt.tz_localize(None)

                vehicle_date_range = (df_filtered['recorded_at'].min(), df_filtered['recorded_at'].max())
                df_filtered = df_filtered[
                    (df_filtered['recorded_at'] >= pd.to_datetime(date_range[0])) &
                    (df_filtered['recorded_at'] <= pd.to_datetime(date_range[1]))
                ]

                if df_filtered.empty:
                    st.error("No data available for the selected chassis number and date range.")
                else:
                    st.success("Data filtered and processed successfully!")


                    # Daily Avg Utilization

                    Q1, Q3 = df_filtered['odometer'].quantile([0.25, 0.75])
                    IQR = Q3 - Q1
                    lower_bound = Q1 - 1.5 * IQR
                    upper_bound = Q3 + 1.5 * IQR
                    df_clean = df_filtered[
                        (df_filtered['odometer'] >= lower_bound) &
                        (df_filtered['odometer'] <= upper_bound)
                    ]
                    df_clean['distance_covered'] = df_clean['odometer'].diff().fillna(0)
                    df_clean['date'] = df_clean['recorded_at'].dt.date
                    df_clean['soc_diff'] = df_clean['soc'].diff()

                    # Daily Average Utilization Plot
                    df_daily = df_clean.groupby(df_clean['recorded_at'].dt.date)['distance_covered'].sum().reset_index()
                    df_daily.columns = ['date', 'distance_covered']
                    average_distance_covered = df_daily['distance_covered'].mean()

                    try:                
                        # Generate and display actionable insights
                        insights = generate_dynamic_insights(df_clean)
                        st.header("Actionable Insights")
                        st.write(f"**Average Daily Distance**: {insights['avg_daily_distance']:.2f} km")
                        st.write(f"**Total Distance Covered**: {insights['total_distance']:.2f} km")
                        st.write(f"**Day with Maximum Distance**: {insights['max_distance_day']}")
                        st.write(f"**Day with Minimum Distance**: {insights['min_distance_day']}")
                        st.write(f"**High Utilization Days**: {insights['high_util_days']}")
                        st.write(f"**Low Utilization Days**: {insights['low_util_days']}")
                        st.write(f"**Deep Discharges**: {insights['deep_discharge_count']}")
                        st.write(f"**Average Charging Per Day**: {insights['avg_charging_per_day']:.2f}%")
                        st.write(f"**Long Idle Days**: {insights['long_idle_days']}")

                        # Generate narrative insights
                        narrative_insights = generate_narrative_insights(
                            insights,
                            daily_distance=df_clean.groupby('date')['distance_covered'].sum(),
                            charging_events=df_clean.groupby('date')['soc_diff'].sum(),
                            idle_periods=df_clean[df_clean['key_on'] == 0].groupby('date').size()
                        )

                        st.header("Customer Insights")
                        for insight in narrative_insights:
                            st.write(f"- {insight}")

                    except Exception as e:
                        st.error(f"Failed to generate insights: {e}")

                    # Proceed with visualization plots after displaying insights
                    st.header("Visualizations")

                    st.metric(label="Complete Loan Journey", value=f"{vehicle_date_range[0].date()} to {vehicle_date_range[1].date()}")
                    st.metric(label="Average Distance Covered (km)", value=f"{average_distance_covered:.2f} km")

                    fig_utilization = go.Figure(
                        data=go.Scatter(
                            x=df_daily['date'],
                            y=df_daily['distance_covered'],
                            mode='lines+markers',
                            marker=dict(size=6, color='blue'),
                            name="Daily Distance Covered",
                            hovertemplate="Date: %{x}<br>Distance Covered: %{y} km<extra></extra>"
                        )
                    )

                    fig_utilization.update_layout(
                        title="Daily Average Utilization",
                        xaxis_title="Date",
                        yaxis_title="Distance Covered (km)",
                        template="plotly_white",
                        hovermode="x unified",
                        width=1000,
                        height=600
                    )

                    st.plotly_chart(fig_utilization)


                    # FCE Cycles
                    
                    df_clean['date'] = df_clean['recorded_at'].dt.date
                    df_clean = df_clean.sort_values(by='recorded_at')

                    fce_per_day = {}
                    distance_per_day = {}

                    for day, day_data in df_clean.groupby('date'):
                        daily_discharge = 0
                        daily_distance = 0
                        for i in range(1, len(day_data)):
                            prev_row = day_data.iloc[i-1]
                            curr_row = day_data.iloc[i]
                            soc_drop = max(0, prev_row['soc'] - curr_row['soc'])
                            daily_discharge += soc_drop
                            distance_covered = max(0, curr_row['odometer'] - prev_row['odometer'])
                            daily_distance += distance_covered

                        fce_per_day[day] = daily_discharge / 100
                        distance_per_day[day] = daily_distance

                    summary_df = pd.DataFrame({
                        'Date': list(fce_per_day.keys()),
                        'Cumulative FCE': list(fce_per_day.values()),
                        'Distance Covered (km)': list(distance_per_day.values())
                    })

                    summary_df['Date'] = pd.to_datetime(summary_df['Date'])

                    cumulative_fce = 0
                    cycle_colors = ['skyblue', 'salmon', 'lightgreen', 'orange', 'purple']
                    cycle_index = 0
                    bar_segments = []

                    for idx, fce in enumerate(summary_df['Cumulative FCE']):
                        while fce > 0:
                            if cumulative_fce + fce < 1:
                                bar_segments.append({'date': summary_df['Date'].iloc[idx], 'fce': fce, 'color': cycle_colors[cycle_index]})
                                cumulative_fce += fce
                                fce = 0
                            else:
                                first_part = 1 - cumulative_fce
                                bar_segments.append({'date': summary_df['Date'].iloc[idx], 'fce': first_part, 'color': cycle_colors[cycle_index]})
                                fce -= first_part
                                cycle_index = (cycle_index + 1) % len(cycle_colors)
                                cumulative_fce = 0

                    fig_fce = go.Figure()

                    for segment in bar_segments:
                        fig_fce.add_trace(
                            go.Bar(
                                x=[segment['date']],
                                y=[segment['fce']],
                                name=f"Cycle {cycle_index}",
                                marker=dict(color=segment['color']),
                                showlegend=False,
                                hovertemplate=f"Date: {segment['date']}<br>FCE Segment: {segment['fce']:.2f}<extra></extra>"
                            )
                        )

                    fig_fce.add_trace(
                        go.Scatter(
                            x=summary_df['Date'],
                            y=summary_df['Distance Covered (km)'],
                            mode='lines+markers',
                            name='Distance Covered (km)',
                            line=dict(color='green', width=2),
                            hovertemplate='Date: %{x}<br>Distance Covered: %{y} km<extra></extra>',
                            yaxis='y2'
                        )
                    )

                    fig_fce.update_layout(
                        title="Daily Cumulative FCE with Segmented Cycles and Distance Covered",
                        xaxis_title="Date",
                        yaxis=dict(
                            title='Cumulative FCE',
                            titlefont=dict(color='skyblue'),
                            tickfont=dict(color='skyblue')
                        ),
                        yaxis2=dict(
                            title='Distance Covered (km)',
                            titlefont=dict(color='green'),
                            tickfont=dict(color='green'),
                            overlaying='y',
                            side='right'
                        ),
                        xaxis=dict(
                            tickformat='%Y-%m-%d',
                            tickangle=45
                        ),
                        barmode='stack',
                        hovermode='x unified',
                        template='plotly_white',
                        width=1000,
                        height=600
                    )

                    st.plotly_chart(fig_fce)


                    # Daily usage with day and night hours segmentation 

                    df_clean['date'] = df_clean['recorded_at'].dt.date
                    df_clean_running = df_clean[df_clean['key_on'] == 1]

                    daytime_hours = []
                    nighttime_hours = []
                    running_time_ranges = {}

                    for day, day_data in df_clean_running.groupby('date'):
                        start_time = day_data['recorded_at'].min()
                        end_time = day_data['recorded_at'].max()
                        running_time_ranges[day] = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"

                        day_hours = 0
                        night_hours = 0

                        for time in day_data['recorded_at']:
                            if 12 <= time.hour < 24:
                                day_hours += 1
                            else:
                                night_hours += 1

                        daytime_hours.append(day_hours / 60) 
                        nighttime_hours.append(night_hours / 60)  

                    running_hours_df = pd.DataFrame({
                        'Date': list(running_time_ranges.keys()),
                        'Daytime Hours': daytime_hours,
                        'Nighttime Hours': nighttime_hours,
                        'Running Time Range': list(running_time_ranges.values())
                    })

                    fig_day_night = go.Figure()
                    fig_day_night.add_trace(
                        go.Bar(
                            x=running_hours_df['Date'],
                            y=running_hours_df['Daytime Hours'],
                            name='Daytime Running Hours (12 PM - 12 AM)',
                            marker=dict(color='dodgerblue'),
                            hovertemplate=(
                                'Date: %{x}<br>'
                                'Daytime Running Hours: %{y:.2f} hours<extra></extra>'
                            )
                        )
                    )

                    fig_day_night.add_trace(
                        go.Bar(
                            x=running_hours_df['Date'],
                            y=running_hours_df['Nighttime Hours'],
                            name='Nighttime Running Hours (12 AM - 12 PM)',
                            marker=dict(color='darkorange'),
                            hovertemplate=(
                                'Date: %{x}<br>'
                                'Nighttime Running Hours: %{y:.2f} hours<extra></extra>'
                            )
                        )
                    )

                    fig_day_night.update_layout(
                        title='Daily Running Hours with Daytime and Nighttime Segmentation',
                        xaxis_title='Date',
                        yaxis_title='Running Hours',
                        barmode='stack',
                        xaxis=dict(
                            tickformat='%Y-%m-%d',
                            tickangle=45,
                            showgrid=True
                        ),
                        yaxis=dict(
                            showgrid=True,
                            titlefont=dict(size=12)
                        ),
                        hovermode='x unified',
                        template='plotly_white',
                        width=1000,
                        height=600
                    )

                    st.plotly_chart(fig_day_night)


                    # Number and Amount of Charge Per Day Plot

                    df_clean['soc_diff'] = df_clean['soc'].diff()
                    df_clean['charging_amount'] = df_clean['soc_diff'].apply(lambda x: x if x > 0 else 0)

                    daily_charging_amount = df_clean.groupby('date')['charging_amount'].sum().reset_index()
                    daily_charging_amount.columns = ['Date', 'Total Charging Amount (%)']

                    df_clean['is_charging_event'] = df_clean['soc_diff'] > 0
                    charging_events_per_day = df_clean.groupby('date')['is_charging_event'].sum().reset_index()
                    charging_events_per_day.columns = ['Date', 'Charging Events']

                    combined_df = pd.merge(daily_charging_amount, charging_events_per_day, on='Date')

                    fig_charging = go.Figure()
                    fig_charging.add_trace(
                        go.Bar(
                            x=combined_df['Date'],
                            y=combined_df['Total Charging Amount (%)'],
                            name='Total Charging Amount (%)',
                            marker=dict(color='mediumseagreen'),
                            hovertemplate='Date: %{x}<br>Total Charging Amount: %{y}%<extra></extra>'
                        )
                    )

                    fig_charging.add_trace(
                        go.Scatter(
                            x=combined_df['Date'],
                            y=combined_df['Charging Events'],
                            mode='lines+markers',
                            name='Charging Events',
                            yaxis='y2',
                            marker=dict(color='salmon'),
                            hovertemplate='Date: %{x}<br>Charging Events: %{y}<extra></extra>'
                        )
                    )

                    fig_charging.update_layout(
                        title='Daily Charging Events and Total Charging Amount',
                        xaxis_title='Date',
                        yaxis=dict(
                            title='Total Charging Amount (%)',
                            titlefont=dict(color='mediumseagreen'),
                            tickfont=dict(color='mediumseagreen')
                        ),
                        yaxis2=dict(
                            title='Charging Events',
                            titlefont=dict(color='salmon'),
                            tickfont=dict(color='salmon'),
                            overlaying='y',
                            side='right'
                        ),
                        xaxis=dict(tickformat='%Y-%m-%d', tickangle=45),
                        hovermode='x unified',
                        template='plotly_white',
                        width=1000,
                        height=600
                    )

                    st.plotly_chart(fig_charging)


                    # Positive SOC Changes When the Vehicle is Not Running

                    df_not_running = df_clean[df_clean['key_on'] == 0]
                    df_not_running['soc_change'] = df_not_running['soc'].diff().fillna(0)

                    positive_soc_changes = df_not_running[df_not_running['soc_change'] > 0]
                    total_positive_soc_change = positive_soc_changes['soc_change'].sum()

                    st.metric(label="Total Positive SOC Change While Not Running (%)", value=f"{total_positive_soc_change:.2f}%")
                    fig_soc_not_running = go.Figure()

                    fig_soc_not_running.add_trace(
                        go.Scatter(
                            x=positive_soc_changes['recorded_at'],
                            y=positive_soc_changes['soc_change'],
                            mode='lines+markers',
                            marker=dict(color='blue', size=6),
                            line=dict(color='blue', width=1),
                            name='Positive SOC Change',
                            hovertemplate='Time: %{x}<br>SOC Change: %{y:.2f}%<extra></extra>'
                        )
                    )

                    fig_soc_not_running.update_layout(
                        title='Positive SOC Changes While Vehicle is Not Running',
                        xaxis_title='Timestamp',
                        yaxis_title='SOC Change (%)',
                        hovermode='x unified',
                        template='plotly_white',
                        width=1000,
                        height=600
                    )

                    st.plotly_chart(fig_soc_not_running)


                    # Moving Averages: Daily Utilization

                    daily_utilization = df_clean.groupby('date')['odometer'].max().diff().fillna(0)
                    utilization_df = pd.DataFrame({
                        'Date': daily_utilization.index,
                        'Daily Utilization (km)': daily_utilization.values
                    })

                    utilization_df['7-Day MA'] = utilization_df['Daily Utilization (km)'].rolling(window=7).mean()
                    utilization_df['30-Day MA'] = utilization_df['Daily Utilization (km)'].rolling(window=30).mean()
                    fig_moving_avg = go.Figure()

                    fig_moving_avg.add_trace(
                        go.Scatter(
                            x=utilization_df['Date'],
                            y=utilization_df['Daily Utilization (km)'],
                            mode='lines+markers',
                            name='Daily Utilization',
                            marker=dict(size=4),
                            hovertemplate='Date: %{x}<br>Daily Utilization: %{y} km<extra></extra>'
                        )
                    )

                    fig_moving_avg.add_trace(
                        go.Scatter(
                            x=utilization_df['Date'],
                            y=utilization_df['7-Day MA'],
                            mode='lines',
                            name='7-Day Moving Average',
                            line=dict(color='orange', width=2),
                            hovertemplate='Date: %{x}<br>7-Day MA: %{y} km<extra></extra>'
                        )
                    )

                    fig_moving_avg.add_trace(
                        go.Scatter(
                            x=utilization_df['Date'],
                            y=utilization_df['30-Day MA'],
                            mode='lines',
                            name='30-Day Moving Average',
                            line=dict(color='green', width=2),
                            hovertemplate='Date: %{x}<br>30-Day MA: %{y} km<extra></extra>'
                        )
                    )

                    fig_moving_avg.update_layout(
                        title='Daily Utilization and Moving Averages',
                        xaxis_title='Date',
                        yaxis_title='Utilization (km)',
                        hovermode='x unified',
                        template='plotly_white',
                        width=1000,
                        height=600
                    )

                    st.plotly_chart(fig_moving_avg)
        except Exception as e:
            st.error(f"Failed to fetch data from BigQuery: {e}")

        