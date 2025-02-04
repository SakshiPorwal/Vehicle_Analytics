# Vehicle Analytics Dashboard

This Streamlit-based web application provides detailed insights into vehicle performance and usage by analyzing telematics data. The application enables users to filter data based on OEM (Manufacturer), chassis number, and date range to generate actionable insights and visualizations.

## Features

- **Data Fetching**: Retrieves vehicle telematics data from BigQuery based on user inputs.
- **Actionable Insights**: Displays key metrics like average distance, high/low utilization days, and deep discharges.
- **Visualizations**: Generates interactive plots using Plotly to visualize daily distance, charging events, FCE cycles, and more.
- **Narrative Insights**: Provides data-driven recommendations and observations based on vehicle usage.

## Prerequisites

- Python 3.8 or later
- Google Cloud BigQuery credentials (JSON file)
- Required Python libraries listed in `requirements.txt`

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. **Set up a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # For MacOS/Linux
   venv\Scripts\activate    # For Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Google Cloud credentials:**
   - Place the BigQuery JSON credentials file in a secure location.
   - Update the path in the app code (`os.environ["GOOGLE_APPLICATION_CREDENTIALS"]`).

## Running the Application

```bash
streamlit run app.py
```

## Project Structure

```
.
├── app.py                # Main Streamlit application file
├── requirements.txt      # List of Python dependencies
├── README.md             # Project documentation
├── insights.py           # Logic for generating dynamic and narrative insights
├── bigquery.py           # Data fetching functions from BigQuery
└── other_files/          # Any additional scripts or assets
```

## User Inputs

- **OEM (Manufacturer)**: Select the vehicle manufacturer.
- **Chassis Number**: Enter the unique chassis number of the vehicle.
- **Date Range**: Select the time period for data analysis.

## Key Visualizations

- **Daily Average Utilization**: Line plot showing daily distance covered.
- **FCE Cycles**: Visual representation of charging and discharging cycles.
- **Day vs. Night Running Hours**: Stacked bar chart showing vehicle usage by time of day.
- **Charging Events**: Bar and line plots showing daily charging amounts and event counts.
- **SOC Changes When Idle**: Scatter plot tracking state-of-charge changes when the vehicle is not running.

## Dependencies

Ensure the following Python libraries are installed (or listed in `requirements.txt`):

```plaintext
streamlit
pandas
plotly
bigquery
```

## Deployment

1. Ensure that the application runs locally using `streamlit run app.py`.
2. If deploying to **Streamlit Cloud**, ensure the `requirements.txt` is present.
3. For other servers, deploy the app and install dependencies using:
   ```bash
   pip install -r requirements.txt
   ```

## License

This project is licensed under the MIT License.

## Contact

For any issues or suggestions, please contact [Your Name] at [Your Email].
