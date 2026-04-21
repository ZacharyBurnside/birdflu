import requests
import pandas as pd
from io import StringIO
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import logging
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
import plotly.express as px
from bs4 import BeautifulSoup
import sqlite3
import plotly.graph_objs as go
import io

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Get today's date
today_date = datetime.now().strftime('%Y-%m-%d')

def fetch_hpai_wild_birds():
    url = "https://www.aphis.usda.gov/sites/default/files/hpai-wild-birds.csv"
    try:
        df = pd.read_csv(url)
        print(f"Wild birds dataset loaded: {len(df)} rows, {len(df.columns)} columns")
        return df
    except Exception as e:
        print(f"Error fetching wild bird data: {e}")
        return pd.DataFrame()

def fetch_hpai_mammals():
    url = "https://www.aphis.usda.gov/sites/default/files/hpai-mammals.csv"
    try:
        df = pd.read_csv(url)
        print(f"Mammals dataset loaded: {len(df)} rows, {len(df.columns)} columns")
        return df
    except Exception as e:
        print(f"Error fetching mammal data: {e}")
        return pd.DataFrame()

def fetch_flock_data():
    try:
        url = (
            "https://publicdashboards.dl.usda.gov/t/MRP_PUB/views/"
            "VS_Avian_HPAIConfirmedDetections2022/"
            "HPAI2022ConfirmedDetections.csv"
            "?%3Aformat=crosstab&%3Asheet=List%20of%20Detections%20by%20Day"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.text

        # Read into DataFrame
        df = pd.read_csv(
            io.StringIO(data),
            parse_dates=["Confirmed", "Control Area Released"],
            thousands=","
        )

        # Rename and convert the 'Confirmed' column to a proper datetime field
        df = df.rename(columns={"Confirmed": "Outbreak Date"})
        df["Outbreak Date"] = pd.to_datetime(df["Outbreak Date"], errors="coerce")

        # —— NEW: Rename & cast Birds Affected → Flock Size ——
        df = df.rename(columns={"Birds Affected": "Flock Size"})
        df["Flock Size"] = (
            df["Flock Size"]
              .astype(str)
              .str.replace(",", "")
              .astype(int)
        )
        # —— END NEW ——

        # State name → abbreviation map
        state_abbrev = {
            'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
            'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
            'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
            'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
            'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
            'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
            'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE',
            'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
            'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC',
            'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR',
            'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
            'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
            'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
            'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'
        }

        # Map full state names to abbreviations
        df["State Abbreviation"] = df["State"].map(state_abbrev)

        return df

    except Exception as e:
        print(f"Error fetching flock data: {e}")
        return pd.DataFrame()

# Fetch and store in a DataFrame
df_flock = fetch_flock_data()

# Function to fetch Bird Flu data for a given date range
def fetch_data(start_date, end_date):
    logging.info(f"Fetching bird flu data from {start_date} to {end_date}")
    url = (
        f"https://europe-west1-fao-empresi.cloudfunctions.net/getLatestEventsByDate"
        f"?animal_type=all&diagnosis_status=confirmed&disease=avian_influenza"
        f"&start_date={start_date}&end_date={end_date}"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
        data_csv = response.content.decode('utf-8')
        return pd.read_csv(StringIO(data_csv))
    except Exception as e:
        logging.error(f"Failed to fetch data for {start_date} to {end_date}: {e}")
        return pd.DataFrame()

# Pagination setup for Bird Flu data
start_date = datetime.strptime("2020-01-01", "%Y-%m-%d")
step_days = 365  # Fetch data in 1-year chunks
date_ranges = []

while start_date < datetime.now():
    range_end = min(start_date + timedelta(days=step_days), datetime.strptime(today_date, "%Y-%m-%d"))
    date_ranges.append((start_date.strftime('%Y-%m-%d'), range_end.strftime('%Y-%m-%d')))
    start_date = range_end + timedelta(days=1)

# Fetch all Bird Flu data in parallel
all_data_frames = []
with ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(lambda dates: fetch_data(*dates), date_ranges)

for result in results:
    if not result.empty:
        all_data_frames.append(result)

# Combine all Bird Flu data chunks into a single DataFrame
df = pd.concat(all_data_frames, ignore_index=True) if all_data_frames else pd.DataFrame()

# Ensure critical columns exist
required_columns = ['observation_date', 'report_date', 'latitude', 'longitude', 'id_event', 'region', 'country', 'species']
for col in required_columns:
    if col not in df.columns:
        df[col] = None

# Process the Bird Flu data
df['observation_date'] = pd.to_datetime(df['observation_date'], errors='coerce')
df['report_date'] = pd.to_datetime(df['report_date'], errors='coerce')
df['reporting_delay'] = (df['report_date'] - df['observation_date']).dt.days
df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

# Filter for valid lat/lon
df_map = df[(df['latitude'].between(-90, 90)) & (df['longitude'].between(-180, 180))]
df_infections = df  # Use the full dataset for counting infections

# Aggregate Bird Flu data for the map
map_data = (
    df_map.groupby(['locality', 'latitude', 'longitude', 'region'])['id_event']
    .nunique()
    .reset_index()
    .rename(columns={'id_event': 'Unique Cases'})
)

# Aggregate Bird Flu data for worldwide time series
time_series = (
    df_infections.groupby('report_date')['id_event']
    .nunique()
    .reset_index()
    .rename(columns={'id_event': 'Unique Infections'})
)

# Aggregate Bird Flu data for time series by country
time_series_by_country = (
    df_infections.groupby(['report_date', 'country'])['id_event']
    .nunique()
    .reset_index()
    .rename(columns={'id_event': 'Unique Infections'})
)

# Total infections count
total_infections = len(df_infections['id_event'].unique())

# Aggregate Bird Flu deaths for worldwide time series
if 'humans_deaths' in df.columns:
    df['humans_deaths'] = pd.to_numeric(df['humans_deaths'], errors='coerce').fillna(0)
    time_series_deaths = (
        df.groupby('report_date', as_index=False)['humans_deaths']
        .sum()
        .rename(columns={'humans_deaths': 'Unique Deaths'})
    )
    time_series_deaths_by_country = (
        df.groupby(['report_date', 'country'], as_index=False)['humans_deaths']
        .sum()
        .rename(columns={'humans_deaths': 'Unique Deaths'})
    )
else:
    time_series_deaths = pd.DataFrame()
    time_series_deaths_by_country = pd.DataFrame()

# Prepare top 10 bird species data
def get_top_bird_counts(dataframe, top_n=10):
    if 'species' not in dataframe.columns:
        return pd.DataFrame(columns=['Species', 'Infections'])
    species_series = dataframe['species'].dropna()
    species_counts = species_series.value_counts().reset_index()
    species_counts.columns = ['Species', 'Infections']
    return species_counts.head(top_n)


# Define database path
DB_PATH = '/home/zburnside/birdflu/egg_prices.db'
TABLE_NAME = 'target_eggs_all'

# Fetch Egg Price Data
def fetch_egg_prices():
    try:
        conn = sqlite3.connect(DB_PATH)
        query = f"SELECT date, state, current_price FROM {TABLE_NAME}"
        df = pd.read_sql(query, conn)
        conn.close()
        df["date"] = pd.to_datetime(df["date"])
        df_grouped = df.groupby(["date", "state"], as_index=False)["current_price"].mean()
        return df_grouped
    except Exception as e:
        logging.error(f"Error fetching egg price data: {e}")
        return pd.DataFrame(columns=["date", "state", "current_price"])

def fetch_urner_barry_prices():
    try:
        url = 'https://www.urnerbarry.com/history/4850'
        headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
          }
        response = requests.get(url, headers = headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        rows = soup.find_all('tr')
        data = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) == 3:
                date = cols[1].text.strip()
                price = cols[2].text.strip()
                data.append({'Date': date, 'Urner Barry Price': price})
        urner_barry_df = pd.DataFrame(data)
        urner_barry_df['Date'] = pd.to_datetime(urner_barry_df['Date'], format='%m/%d/%Y', errors='coerce')
        urner_barry_df['Urner Barry Price'] = pd.to_numeric(urner_barry_df['Urner Barry Price'], errors='coerce')
        return urner_barry_df.dropna()
    except Exception as e:
        logging.error(f"Failed to fetch Urner Barry egg price data: {e}")
        return pd.DataFrame(columns=['Date', 'Urner Barry Price'])

# Combine Target and Urner Barry data
logging.info("Fetching and combining egg price data...")

# Fetch data
df_egg_prices = fetch_egg_prices()
df_urner_barry = fetch_urner_barry_prices()

# Ensure correct datetime conversion
df_urner_barry['Date'] = pd.to_datetime(df_urner_barry['Date'], errors='coerce')
df_egg_prices['date'] = pd.to_datetime(df_egg_prices['date'], errors='coerce')

# Handle missing values by setting sensible defaults
min_date = df_urner_barry['Date'].min() if not df_urner_barry.empty else pd.to_datetime("2024-01-01")
max_date = df_egg_prices['date'].max() if not df_egg_prices.empty else pd.to_datetime("2024-01-01")


combined_data = pd.merge(
    df_egg_prices, df_urner_barry, left_on='date', right_on='Date', how='outer'
).sort_values('date') if not df_egg_prices.empty and not df_urner_barry.empty else pd.DataFrame()


combined_data = pd.merge(
    df_egg_prices, df_urner_barry, left_on='date', right_on='Date', how='outer'
).sort_values('date')

# Calculate Growth Rates
average_daily_growth_rate = time_series['Unique Infections'].pct_change().mean() * 100
average_weekly_growth_rate = (
    time_series['Unique Infections']
    .rolling(7)
    .apply(lambda x: (x[-1] - x[0]) / x[0] * 100 if x[0] > 0 else 0, raw=True)
    .mean()
)
average_monthly_growth_rate = (
    time_series['Unique Infections']
    .rolling(30)
    .apply(lambda x: (x[-1] - x[0]) / x[0] * 100 if x[0] > 0 else 0, raw=True)
    .mean()
)

daily_growth_rate = "N/A"
weekly_growth_rate = "N/A"
monthly_growth_rate = "N/A"

if len(time_series) > 1:
    today_infections = time_series['Unique Infections'].iloc[-1]
    yesterday_infections = time_series['Unique Infections'].iloc[-2]
    if yesterday_infections > 0:
        daily_growth_rate = ((today_infections - yesterday_infections) / yesterday_infections) * 100

if len(time_series) > 7:
    last_week_infections = time_series['Unique Infections'].iloc[-8]
    if last_week_infections > 0:
        weekly_growth_rate = ((today_infections - last_week_infections) / last_week_infections) * 100

if len(time_series) > 30:
    last_month_infections = time_series['Unique Infections'].iloc[-31]
    if last_month_infections > 0:
        monthly_growth_rate = ((today_infections - last_month_infections) / last_month_infections) * 100

logging.info(f"Combined data has {len(combined_data)} rows.")

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

app.title = "Bird Flu Tracker"

app.index_string = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bird Flu Tracker</title>

    <!-- Google AdSense Script -->
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-5023671045770129"
        crossorigin="anonymous"></script>

    {%metas%}
    {%favicon%}
    {%css%}
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
'''

# Layout
app.layout = dbc.Container(fluid=True, children=[
    # Title Row
    dbc.Row(
        dbc.Col(
            html.H1("Impact of H5N1", className="text-center text-primary mb-4"),
            width=12
        )
    ),

    # Summary Cards
    dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Total Infections", className="text-center bg-primary text-white"),
                dbc.CardBody([
                    html.H2(f"{total_infections:,}" if total_infections > 0 else "N/A",
                            className="text-danger text-center"),
                    html.P("Confirmed cases worldwide",
                           className="text-muted text-center", style={"fontSize": "0.9em"})
                ]),
            ], className="shadow-sm mb-3"),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Total Deaths", className="text-center bg-danger text-white"),
                dbc.CardBody([
                    html.H2(f"{int(df['humans_deaths'].sum()):,}" if 'humans_deaths' in df.columns and not df['humans_deaths'].isna().all() else "N/A",
                            className="text-light text-center"),
                    html.P("Reported fatalities due to bird flu",
                           className="text-muted text-center", style={"fontSize": "0.9em"})
                ]),
            ], className="shadow-sm mb-3"),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Growth Rates", className="text-center bg-warning text-white"),
                dbc.CardBody([
                    html.P(f"Daily: {daily_growth_rate:.2f}% (Avg: {average_daily_growth_rate:.2f}%)" if daily_growth_rate else "Daily: N/A",
                           className="text-success text-center", style={"fontSize": "1.1em"}),
                    html.P(f"Weekly: {weekly_growth_rate:.2f}% (Avg: {average_weekly_growth_rate:.2f}%)" if weekly_growth_rate else "Weekly: N/A",
                           className="text-warning text-center", style={"fontSize": "1.1em"}),
                    html.P(f"Monthly: {monthly_growth_rate:.2f}% (Avg: {average_monthly_growth_rate:.2f}%)" if monthly_growth_rate else "Monthly: N/A",
                           className="text-info text-center", style={"fontSize": "1.1em"})
                ]),
            ], className="shadow-sm mb-3"),
            width=3
        ),
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("Average Reporting Time", className="text-center bg-info text-white"),
                dbc.CardBody([
                    html.H2(f"{df['reporting_delay'].mean():.2f} days" if not df['reporting_delay'].isna().all() else "N/A",
                            className="text-warning text-center"),
                    html.P("Average delay in reporting cases",
                           className="text-muted text-center", style={"fontSize": "0.9em"})
                ]),
            ], className="shadow-sm mb-3"),
            width=3
        ),
    ]),

    # Tabs
    dbc.Tabs([
        # Infection Map Tab
        dbc.Tab(
            label="Infection Map",
            tab_id="infection-map",
            children=[
                dbc.Row([
                    dbc.Col(
                        html.Div([
                            dcc.Dropdown(
                                id='region-filter',
                                options=[{'label': region, 'value': region} for region in df['region'].unique()],
                                placeholder="Filter by Region",
                                style={'color': '#000', 'backgroundColor': '#FFF'}
                            )
                        ]),
                        width=12,
                        style={'marginBottom': '15px'}
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        dcc.Loading(
                            dcc.Graph(
                                id='world-map',
                                config={'scrollZoom': True, 'displayModeBar': True}
                            ),
                            type="circle"
                        ),
                        width=12, lg=6,
                        style={'padding': '10px'}
                    ),
                    dbc.Col(
                        dcc.Loading(
                            dcc.Graph(id='bird-species-chart', config={'displayModeBar': False}),
                            type="circle"
                        ),
                        width=12, lg=6,
                        style={'padding': '10px'}
                    )
                ]),
            ],
            tab_style={"color": "white", "backgroundColor": "#007BFF", "padding": "10px"},
            active_tab_style={"color": "black", "backgroundColor": "#D3D3D3", "padding": "10px"}
        ),

        # Time Series Tab
        dbc.Tab(
            label="Time Series",
            tab_id="time-series",
            children=[
                dbc.Row([
                    dbc.Col(
                        dcc.Dropdown(
                            id='country-filter',
                            options=[{'label': 'All', 'value': 'All'}] + [
                                {'label': country, 'value': country} for country in df['country'].dropna().unique()
                            ],
                            value='All',
                            placeholder="Select a Country",
                            style={'color': '#000', 'backgroundColor': '#FFF'}
                        ),
                        width=3,
                        style={'padding': '10px'}
                    ),
                    dbc.Col(
                        dcc.DatePickerRange(
                            id='time-range-picker',
                            start_date=min_date,
                            end_date=max_date,
                            display_format='YYYY-MM-DD'
                        ),
                        width=3,
                        style={'padding': '10px'}
                    ),
                    dbc.Col(
                        dcc.RadioItems(
                            id='toggle-view',
                            options=[
                                {'label': 'Unique', 'value': 'Unique'},
                                {'label': 'Cumulative', 'value': 'Cumulative'}
                            ],
                            value='Unique',
                            labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                        ),
                        width=3,
                        style={'padding': '10px'}
                    ),
                    dbc.Col(
                        dcc.RadioItems(
                            id='data-type',
                            options=[
                                {'label': 'Infections', 'value': 'Infections'},
                                {'label': 'Deaths', 'value': 'Deaths'}
                            ],
                            value='Infections',
                            labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                        ),
                        width=3,
                        style={'padding': '10px'}
                    )
                ]),
                dbc.Row([
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader("Time Series Chart", className="text-center bg-primary text-white"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id='time-series-chart'),
                                    type="circle"
                                )
                            )
                        ], className="shadow-sm mb-3"),
                        width=9,
                        style={'padding': '10px'}
                    ),
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader("Summary within Last 7 Days", className="text-center bg-info text-white"),
                            dbc.CardBody([
                                html.Div(id='country-stats-box', className="mb-3 text-white"),
                                html.H6("Last 7 Days of Data", className="text-center text-success mt-2"),
                                html.Div(id='last-7-days-table', className="table-responsive")
                            ])
                        ], className="shadow-sm mb-3"),
                        width=3,
                        style={'padding': '10px'}
                    )
                ])
            ],
            tab_style={"color": "white", "backgroundColor": "#28A745", "padding": "10px"},
            active_tab_style={"color": "black", "backgroundColor": "#D3D3D3", "padding": "10px"}
        ),

        # Egg Price Tracker Tab
        dbc.Tab(
            label="Egg Price Tracker",
            tab_id="egg-price-tracker",
            children=[
                dbc.Row([
                    dbc.Col(
                        dcc.DatePickerRange(
                            id='time-series-date-picker',
                            start_date=min_date,
                            end_date=max_date,
                            display_format='YYYY-MM-DD'
                        ),
                        width=6,
                        style={'padding': '10px'}
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        dcc.Loading(
                            dcc.Graph(id='target-egg-price-chart', config={'displayModeBar': True}),
                            type="circle"
                        ),
                        width=6,
                        style={'padding': '10px'}
                    ),
                    dbc.Col(
                        dcc.Loading(
                            dcc.Graph(id='urner-barry-price-chart', config={'displayModeBar': True}),
                            type="circle"
                        ),
                        width=6,
                        style={'padding': '10px'}
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader("Price Statistics", className="text-center bg-info text-white"),
                            dbc.CardBody(
                                html.Div(id='egg-price-stats-box', className="text-white")
                            )
                        ], className="shadow-sm mb-3"),
                        width=12,
                        style={'padding': '10px'}
                    ),
                ]),
            ],
            tab_style={"color": "white", "backgroundColor": "#FFC107", "padding": "10px"},
            active_tab_style={"color": "black", "backgroundColor": "#D3D3D3", "padding": "10px"}
        ),

        # 🆕 **Updated Flock Infections Tab**
        dbc.Tab(
            label="Flock Infections",
            tab_id="flock-infections",
            children=[
                dbc.Alert(
                    "⚠️ Data is subject to delayed reporting",
                    color="warning",
                    className="text-center",
                    dismissable=False
                ),

                # Total Outbreak Counter
                dbc.Row([
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader(
                                "Total Outbreaks",
                                className="text-center bg-danger text-white"
                            ),
                            dbc.CardBody([
                                html.H2(
                                    id="total-outbreaks-count",
                                    className="text-center text-light"
                                ),
                                html.P(
                                    "Total confirmed flock infections",
                                    className="text-muted text-center"
                                )
                            ]),
                        ], className="shadow-sm mb-3"),
                        width=4,
                        className="mx-auto"
                    ),
                ], style={'padding': '10px'}),

                # **Toggle for Daily vs Cumulative Flock Infections**
                dbc.Row([
                    dbc.Col(
                        dcc.RadioItems(
                            id='flock-infections-toggle',
                            options=[
                                {'label': 'Daily', 'value': 'Daily'},
                                {'label': 'Cumulative', 'value': 'Cumulative'}
                            ],
                            value='Daily',
                            labelStyle={'display': 'inline-block', 'marginRight': '10px'}
                        ),
                        width=4
                    ),
                ], style={'padding': '10px'}),

                # **Side-by-Side: Flock Infections Over Time & Incident Count Time Series**
                dbc.Row([
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader("Flock Infections Over Time", className="text-center bg-primary text-white"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id='flock-infections-chart'),
                                    type="circle"
                                )
                            )
                        ], className="shadow-sm mb-3"),
                        width=6,
                        style={'padding': '10px'}
                    ),
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader("Incident Count Over Time", className="text-center bg-info text-white"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id='incident-count-chart'),
                                    type="circle"
                                )
                            )
                        ], className="shadow-sm mb-3"),
                        width=6,
                        style={'padding': '10px'}
                    ),
                ]),

                # **Side-by-Side: Flock Infection Density Map & Infections by State Bar Chart**
                dbc.Row([
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader("Density of Flock Infections", className="text-center bg-danger text-white"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id='flock-infection-map'),
                                    type="circle"
                                )
                            )
                        ], className="shadow-sm mb-3"),
                        width=6,
                        style={'padding': '10px'}
                    ),
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader("Infections by State", className="text-center bg-warning text-white"),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(id='infections-by-state-bar'),
                                    type="circle"
                                )
                            )
                        ], className="shadow-sm mb-3"),
                        width=6,
                        style={'padding': '10px'}
                    ),
                ]),
            ],
            tab_style={"color": "white", "backgroundColor": "#6C757D", "padding": "10px"},
            active_tab_style={"color": "black", "backgroundColor": "#D3D3D3", "padding": "10px"}
        ),
    ]),

    # Footer with Buy Me a Coffee Link
    dbc.Row(
        dbc.Col(
            html.Footer([
                html.P("Data Sources: WHO, CDC.com, Target.com, Urner Barry Index", className="text-muted"),
                html.P(f"Last Updated: {datetime.now().strftime('%Y-%m-%d')}", className="text-muted"),
                html.P("Disclaimer: Data is provided as-is for informational purposes only.", className="text-muted"),
                html.A(
                    "☕ Buy Me a Coffee",
                    href="https://www.buymeacoffee.com/zburn",
                    target="_blank",
                    style={
                        'color': '#FFD700',
                        'textDecoration': 'none',
                        'fontSize': '16px',
                        'marginTop': '10px',
                        'display': 'inline-block',
                        'padding': '10px 15px',
                        'backgroundColor': '#333',
                        'borderRadius': '5px',
                        'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)',
                        'textAlign': 'center'
                    },
                    className="text-center"
                )
            ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': '#222', 'color': '#FFF'})
        )
    )
])

@app.callback(
    Output('last-7-days-table', 'children'),
    [Input('time-series-chart', 'figure')]
)
def update_last_7_days_table(figure):
    if figure is None or 'data' not in figure:
        return html.P("No data available", className="text-center text-muted")

    last_7_days = time_series.tail(7).assign(
        report_date=lambda x: x['report_date'].dt.strftime('%Y-%m-%d')
    )

    table = dbc.Table.from_dataframe(
        last_7_days,
        striped=True,
        bordered=True,
        hover=True,
        class_name="table-dark text-center",
        style={"fontSize": "0.85em", "marginBottom": "0"}
    )

    return table

@app.callback(
    Output('world-map', 'figure'),
    Input('region-filter', 'value')
)
def update_map(selected_region):
    # Filter map data based on selected region
    filtered_data = map_data if not selected_region else map_data[map_data['region'] == selected_region]

    if filtered_data.empty:
        return px.scatter_mapbox(
            title="No Data Available",
            lat=[0],
            lon=[0],
            zoom=1
        ).update_layout(template='plotly_dark', margin=dict(l=0, r=0, t=40, b=0))

    # Create the scatter mapbox with clustering enabled
    fig = px.scatter_mapbox(
        filtered_data,
        lat='latitude',
        lon='longitude',
        size='Unique Cases',
        color='Unique Cases',
        color_continuous_scale='bluered',
        hover_name='locality',
        hover_data={'region': True, 'Unique Cases': True},
        title="Bird Flu Human Infection Hotspots",
        mapbox_style='carto-positron',
        zoom=2
    )

    # Enable clustering and improve layout
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        template='plotly_dark',
        legend_title_text="Infection Intensity",
        uirevision='constant',  # Prevents zoom reset on updates
        dragmode="zoom",  # Enables zooming and panning
        mapbox=dict(
            zoom=3,  # Default zoom level
            center=dict(lat=20, lon=0),  # Adjust as needed
            style="carto-positron"
        )
    )
    return fig

@app.callback(
    [Output('target-egg-price-chart', 'figure'),
     Output('urner-barry-price-chart', 'figure'),
     Output('egg-price-stats-box', 'children')],
    [Input('time-series-date-picker', 'start_date'),
     Input('time-series-date-picker', 'end_date')]
)
def update_egg_price_charts(start_date, end_date):
    start_date, end_date = pd.to_datetime(start_date), pd.to_datetime(end_date)

    # Filter data by date range
    filtered_target_data = df_egg_prices[(df_egg_prices['date'] >= start_date) &
                                         (df_egg_prices['date'] <= end_date)]
    filtered_urner_barry_data = df_urner_barry[(df_urner_barry['Date'] >= start_date) &
                                               (df_urner_barry['Date'] <= end_date)]

    # ✅ Apply a 7-day rolling average for smoothing
    filtered_target_data.loc[:, 'rolling_avg_price'] = (filtered_target_data.groupby('state')['current_price'].transform(lambda x: x.rolling(window=7, min_periods=1).mean()))

    filtered_urner_barry_data['rolling_avg_price'] = filtered_urner_barry_data['Urner Barry Price'].rolling(window=7, min_periods=1).mean()

    # 📊 Plot Target Egg Prices by State with Rolling Average
    target_fig = px.line(filtered_target_data, x='date', y='rolling_avg_price', color='state',
                         title="Target Egg Prices by State (7-Day Rolling Average)", markers=True)
    # 📊 Plot Urner Barry Egg Prices with Rolling Average
    urner_barry_fig = px.line(filtered_urner_barry_data, x='Date', y='rolling_avg_price',
                              title="Urner Barry Egg Prices (7-Day Rolling Average)", markers=True)

    # 🖤 Dark Theme
    target_fig.update_layout(template='plotly_dark')
    urner_barry_fig.update_layout(template='plotly_dark')

    # ℹ️ Statistics Box
    stats_box = html.Div([
        html.H6("Price Statistics", className="text-info text-center"),
        html.P(f"Target - Max (7-Day Avg): ${filtered_target_data['rolling_avg_price'].max():.2f}", className="text-light"),
        html.P(f"Target - Min (7-Day Avg): ${filtered_target_data['rolling_avg_price'].min():.2f}", className="text-light"),
        html.P(f"Urner Barry - Max (7-Day Avg): ${filtered_urner_barry_data['rolling_avg_price'].max():.2f}", className="text-light"),
        html.P(f"Urner Barry - Min (7-Day Avg): ${filtered_urner_barry_data['rolling_avg_price'].min():.2f}", className="text-light"),
    ], style={'backgroundColor': '#222', 'padding': '10px', 'borderRadius': '5px', 'textAlign': 'center'})

    return target_fig, urner_barry_fig, stats_box


@app.callback(
    Output('bird-species-chart', 'figure'),
    Input('region-filter', 'value')
)
def update_bird_species_chart(selected_region):
    filtered_df = df if not selected_region else df[df['region'] == selected_region]
    top_bird_counts = get_top_bird_counts(filtered_df)

    if top_bird_counts.empty:
        return px.bar(
            title="No Data Available"
        ).update_layout(template='plotly_dark', showlegend=False)

    # Create a horizontal stacked bar chart
    fig = px.bar(
        top_bird_counts,
        y='Species',
        x='Infections',
        color='Species',
        title="Top 10 Bird Species by Infections",
        orientation='h',
        text='Infections'
    )

    # Highlight the top species
    top_species = top_bird_counts.iloc[0]['Species']
    top_infections = top_bird_counts.iloc[0]['Infections']
    fig.add_annotation(
        x=top_infections,
        y=top_species,
        text=f"Top Species: {top_species} ({top_infections})",
        showarrow=True,
        arrowhead=3
    )

    # Disable legend
    fig.update_layout(
        template='plotly_dark',
        xaxis_title="Number of Infections",
        yaxis_title="Bird Species",
        margin=dict(l=0, r=0, t=40, b=0),
        showlegend=False  # 👈 This removes the legend
    )

    return fig

@app.callback(
    [Output('time-series-chart', 'figure'),
     Output('country-stats-box', 'children')],
    [Input('country-filter', 'value'),
     Input('time-range-picker', 'start_date'),
     Input('time-range-picker', 'end_date'),
     Input('toggle-view', 'value'),
     Input('data-type', 'value')]
)
def update_time_series_and_stats(selected_country, start_date, end_date, view_type, data_type):
    if data_type == 'Infections':
        base_data = time_series if selected_country == 'All' else time_series_by_country[
            time_series_by_country['country'] == selected_country
        ]
        column_name = 'Unique Infections'
        y_label = "Infections"
    else:
        base_data = time_series_deaths if selected_country == 'All' else time_series_deaths_by_country[
            time_series_deaths_by_country['country'] == selected_country
        ]
        column_name = 'Unique Deaths'
        y_label = "Deaths"

    base_data = base_data.copy()
    base_data['report_date'] = pd.to_datetime(base_data['report_date'], errors='coerce')

    # Ensure base_data['report_date'] is timezone-aware
    if base_data['report_date'].dt.tz is None:
        base_data['report_date'] = base_data['report_date'].dt.tz_localize('UTC')

    # Convert start_date and end_date to timezone-aware timestamps
    start_date = pd.to_datetime(start_date).tz_localize('UTC') if pd.to_datetime(start_date).tz is None else pd.to_datetime(start_date).tz_convert('UTC')
    end_date = pd.to_datetime(end_date).tz_localize('UTC') if pd.to_datetime(end_date).tz is None else pd.to_datetime(end_date).tz_convert('UTC')

    # Filter data by date range
    filtered_data = base_data[
        (base_data['report_date'] >= start_date) & (base_data['report_date'] <= end_date)
    ]

    if filtered_data.empty:
        return (
            px.line(title="No Data Available").update_layout(template='plotly_dark'),
            html.Div("No data available for the selected filters.", style={'color': '#FFF', 'textAlign': 'center'})
        )

    if view_type == 'Cumulative':
        filtered_data['Value'] = filtered_data[column_name].cumsum()
    else:
        filtered_data['Value'] = filtered_data[column_name]

    filtered_data['Smoothed'] = filtered_data['Value'].rolling(window=7, center=True).mean()

    fig = px.line(
        filtered_data,
        x='report_date',
        y=['Value', 'Smoothed'],
        labels={'Value': y_label, 'report_date': 'Report Date'},
        title=f"Human {y_label} Trends Over Time for {'All Countries' if selected_country == 'All' else selected_country}",
    )
    fig.update_layout(
        template='plotly_dark',
        legend_title_text='Type',
        xaxis_title='Report Date',
        yaxis_title=y_label,
        margin=dict(l=0, r=0, t=40, b=0)
    )

    total_value = filtered_data['Value'].iloc[-1] if not filtered_data.empty else 0
    peak_value = filtered_data['Smoothed'].max() if not filtered_data.empty else 0
    peak_date = (
        filtered_data.loc[filtered_data['Smoothed'].idxmax(), 'report_date']
        if not filtered_data.empty and not filtered_data['Smoothed'].isna().all()
        else "N/A"
    )

    stats_box = html.Div(
        [
            html.H5(f"Latest Data: {filtered_data['report_date'].max().strftime('%Y-%m-%d')}" if not filtered_data.empty else "N/A"),
            html.P(f"Total {y_label}: {total_value:,}", className="text-light"),
            html.P(f"Peak {y_label}: {peak_value:.0f} on {peak_date.strftime('%Y-%m-%d')}" if peak_date != "N/A" else "Peak Data Unavailable", className="text-warning"),
        ],
        style={
            'color': '#FFF',
            'padding': '15px',
            'backgroundColor': '#333',
            'border': '1px solid white',
            'borderRadius': '5px',
            'textAlign': 'center'
        }
    )

    return fig, stats_box

@app.callback(
    Output('flock-infections-chart', 'figure'),
    Input('flock-infections-toggle', 'value')
)
def update_flock_infections_chart(view_type):
    # Ensure column exists
    if 'Outbreak Date' not in df_flock.columns:
        print("Column 'Outbreak Date' not found!")
        return px.line(title="Error: Missing Data Column")

    # Ensure proper datetime format
    df_flock['Outbreak Date'] = pd.to_datetime(df_flock['Outbreak Date'], errors='coerce')

    # Aggregate daily infections
    time_series_flock = (
        df_flock.groupby('Outbreak Date', as_index=False)['Flock Size']
        .sum()
        .rename(columns={'Flock Size': 'Total Infections'})
    )

    # Handle cumulative view
    if view_type == 'Cumulative':
        time_series_flock['Total Infections'] = time_series_flock['Total Infections'].cumsum()

    # Plot
    fig = px.line(
        time_series_flock,
        x='Outbreak Date',
        y='Total Infections',
        title=f"Flock Infections Over Time ({view_type})",
        labels={'Outbreak Date': 'Date', 'Total Infections': 'Infections'},
        markers=True
    )

    fig.update_layout(template='plotly_dark')

    return fig

@app.callback(
    Output('incident-count-chart', 'figure'),
    Input('flock-infections-toggle', 'value')
)
def update_incident_count_chart(view_type):
    # Ensure column exists
    if 'Outbreak Date' not in df_flock.columns:
        print("Column 'Outbreak Date' not found!")
        return px.line(title="Error: Missing Data Column")

    # Ensure proper datetime format
    df_flock['Outbreak Date'] = pd.to_datetime(df_flock['Outbreak Date'], errors='coerce')

    # Aggregate daily incidents
    time_series_incidents = (
        df_flock.groupby('Outbreak Date', as_index=False)
        .size()
        .rename(columns={'size': 'Incident Count'})
    )

    # Handle cumulative view
    if view_type == 'Cumulative':
        time_series_incidents['Incident Count'] = time_series_incidents['Incident Count'].cumsum()

    # Plot
    fig = px.line(
        time_series_incidents,
        x='Outbreak Date',
        y='Incident Count',
        title=f"Incident Count Over Time ({view_type})",
        labels={'Outbreak Date': 'Date', 'Incident Count': 'Incidents'},
        markers=True
    )

    fig.update_layout(template='plotly_dark')

    return fig

@app.callback(
    Output('flock-infection-map', 'figure'),
    Input('flock-infections-toggle', 'value')
)
def update_flock_infection_map(_):
    # Ensure required column exists
    if 'State Abbreviation' not in df_flock.columns:
        print("Column 'State Abbreviation' not found!")
        return px.choropleth(title="Error: Missing Data Column")

    # Aggregate data by state
    map_data = (
        df_flock.groupby('State Abbreviation', as_index=False)
        .agg({'Flock Size': 'sum'})  # Summing flock sizes per state
        .rename(columns={'Flock Size': 'Total Flock Size'})
    )

    # Calculate the number of outbreaks per state
    map_data['Total Outbreaks'] = df_flock.groupby('State Abbreviation').size().values

    # Create choropleth map
    fig = px.choropleth(
        map_data,
        locations='State Abbreviation',
        locationmode='USA-states',
        color='Total Outbreaks',
        hover_name='State Abbreviation',
        hover_data={'Total Outbreaks': True, 'Total Flock Size': True},
        color_continuous_scale='reds',
        title="Density of Flock Infections by State"
    )

    fig.update_layout(template='plotly_dark', geo_scope='usa')

    return fig

@app.callback(
    Output('infections-by-state-bar', 'figure'),
    Input('flock-infections-toggle', 'value')
)
def update_infections_by_state(_):
    if 'State Abbreviation' not in df_flock.columns:
        print("Column 'State Abbreviation' not found!")
        return px.bar(title="Error: Missing Data Column")

    # Aggregate infections by state
    state_counts = (
        df_flock.groupby('State Abbreviation', as_index=False)
        .agg({'Flock Size': 'sum'})
        .rename(columns={'Flock Size': 'Total Infections'})
        .sort_values(by='Total Infections', ascending=False)
    )

    # Create bar chart
    fig = px.bar(
        state_counts,
        x='State Abbreviation',
        y='Total Infections',
        text='Total Infections',
        title="Infections by State",
        labels={'Total Infections': 'Total Infections'},
        color='Total Infections',
        color_continuous_scale='reds'
    )

    fig.update_layout(template='plotly_dark', xaxis_title="State", yaxis_title="Total Infections")

    return fig

@app.callback(
    Output("total-outbreaks-count", "children"),
    Input("flock-infections-toggle", "value")
)
def update_total_outbreak_count(_):
    total_outbreaks = sum(df_flock['Flock Size'])
    return f"{total_outbreaks:,}"

# Run app
if __name__ == "__main__":
    app.run_server(debug=False)