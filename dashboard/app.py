import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os
from sqlalchemy import text

# Ensure src is in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.connection import get_engine

st.set_page_config(page_title="AQI Analysis Dashboard", layout="wide")

# ==========================================
# Database Connection
# ==========================================
@st.cache_resource
def init_connection():
    return get_engine()

engine = init_connection()

# ==========================================
# Data Fetching Functions
# ==========================================
@st.cache_data
def get_metadata():
    # Only return stations that actually have data in hourly_air_quality or daily_aqi
    query = text("""
        SELECT s.station_id, s.station_name, s.city, s.latitude, s.longitude
        FROM stations s
        WHERE EXISTS (
            SELECT 1 FROM daily_aqi d WHERE d.station_id = s.station_id
        ) OR EXISTS (
            SELECT 1 FROM hourly_air_quality h WHERE h.station_id = s.station_id
        )
        ORDER BY s.city, s.station_name
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df

@st.cache_data
def get_date_range():
    query = text("""
        SELECT MIN(date) as min_date, MAX(date) as max_date 
        FROM daily_city_aqi
    """)
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    if df.empty or pd.isna(df.iloc[0]['min_date']):
        return None, None
    return df.iloc[0]['min_date'], df.iloc[0]['max_date']

def get_daily_city_aqi(start_date, end_date, city=None):
    query = """
        SELECT date, city, pm25, no2, temperature_c, humidity_pct, aqi
        FROM daily_city_aqi
        WHERE date >= :start_date AND date <= :end_date
    """
    params = {"start_date": start_date, "end_date": end_date}
    if city and city != "All Cities":
        query += " AND city = :city"
        params["city"] = city
    query += " ORDER BY date"
    
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

def get_daily_station_aqi(start_date, end_date, station_id=None, city=None):
    query = """
        SELECT d.date, s.station_name, s.city, d.pm25, d.no2, 
               d.temperature_c, d.humidity_pct, d.wind_speed_kmh,
               d.aqi, d.aqi_category
        FROM daily_aqi d
        JOIN stations s ON d.station_id = s.station_id
        WHERE d.date >= :start_date AND d.date <= :end_date
    """
    params = {"start_date": start_date, "end_date": end_date}
    
    if station_id and station_id != "All Stations":
        query += " AND d.station_id = :station_id"
        params["station_id"] = station_id
    elif city and city != "All Cities":
        query += " AND s.city = :city"
        params["city"] = city
        
    query += " ORDER BY d.date"
    
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)

def get_hourly_pollution(start_date, end_date, station_id=None, city=None):
    query = """
        SELECT h.timestamp_utc, s.station_name, s.city, h.pm25, h.no2
        FROM hourly_air_quality h
        JOIN stations s ON h.station_id = s.station_id
        WHERE h.timestamp_utc >= :start_date AND h.timestamp_utc <= :end_date_time
    """
    # end_date_time to cover the whole day
    params = {"start_date": start_date, "end_date_time": f"{end_date} 23:59:59"}
    
    if station_id and station_id != "All Stations":
        query += " AND h.station_id = :station_id"
        params["station_id"] = station_id
    elif city and city != "All Cities":
        query += " AND s.city = :city"
        params["city"] = city
        
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn, params=params)
    
    if not df.empty:
        # Extract hour of day
        df['hour'] = pd.to_datetime(df['timestamp_utc']).dt.hour
    return df

def get_station_coverage():
    query = text("""
        SELECT s.station_name, s.city, COUNT(h.id) as obs_count
        FROM stations s
        JOIN hourly_air_quality h ON s.station_id = h.station_id
        GROUP BY s.station_name, s.city
        HAVING COUNT(h.id) > 0
        ORDER BY obs_count DESC
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

def get_weather_aggregate(start_date, end_date, station_id=None, city=None):
    # Get daily averaged weather to avoid duplicating AQI when plotting
    query = """
        SELECT d.date, s.station_name, s.city, d.temperature_c, d.humidity_pct, d.wind_speed_kmh, d.aqi
        FROM daily_aqi d
        JOIN stations s ON d.station_id = s.station_id
        WHERE d.date >= :start_date AND d.date <= :end_date
    """
    params = {"start_date": start_date, "end_date": end_date}
    if station_id and station_id != "All Stations":
        query += " AND d.station_id = :station_id"
        params["station_id"] = station_id
    elif city and city != "All Cities":
        query += " AND s.city = :city"
        params["city"] = city
        
    with engine.connect() as conn:
        return pd.read_sql(text(query), conn, params=params)


# ==========================================
# Sidebar UI
# ==========================================
metadata_df = get_metadata()
min_date_db, max_date_db = get_date_range()

st.title("Air Quality Index Analysis Dashboard")
st.markdown("Analyzes pollution, AQI, stations, and weather data collected through the ETL pipeline.")

if metadata_df.empty or min_date_db is None:
    st.error("No data available in the database. Please run the ETL pipeline first.")
    st.stop()

st.sidebar.header("Filters")

# City Filter
cities = ["All Cities"] + sorted(metadata_df['city'].unique().tolist())
selected_city = st.sidebar.selectbox("Select City", cities)

# Station Filter
if selected_city == "All Cities":
    station_options = ["All Stations"]
else:
    city_stations = metadata_df[metadata_df['city'] == selected_city]
    station_options = ["All Stations"] + city_stations['station_name'].tolist()
selected_station_name = st.sidebar.selectbox("Select Station", station_options)

selected_station_id = None
if selected_station_name != "All Stations":
    selected_station_id = int(metadata_df[metadata_df['station_name'] == selected_station_name]['station_id'].iloc[0])

# Date Range Filter
start_date, end_date = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date_db, max_date_db),
    min_value=min_date_db,
    max_value=max_date_db
)

# ==========================================
# Fetch Filtered Data
# ==========================================
city_aqi_df = get_daily_city_aqi(start_date, end_date, selected_city)
station_aqi_df = get_daily_station_aqi(start_date, end_date, selected_station_id, selected_city)
hourly_df = get_hourly_pollution(start_date, end_date, selected_station_id, selected_city)

# ==========================================
# Main Dashboard UI
# ==========================================

# Decide the primary dataframe for KPIs based on selection level
if selected_station_name != "All Stations":
    kpi_df = station_aqi_df
    view_level = "Station"
else:
    kpi_df = city_aqi_df
    view_level = "City"

if kpi_df.empty:
    st.warning("No data available for the selected filters.")
else:
    # Top KPI Cards
    avg_aqi = kpi_df['aqi'].mean()
    max_aqi = kpi_df['aqi'].max()
    min_aqi = kpi_df['aqi'].min()
    avg_pm25 = kpi_df['pm25'].mean()
    avg_no2 = kpi_df['no2'].mean()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Average AQI", f"{avg_aqi:.1f}")
    col2.metric("Max AQI", f"{max_aqi:.1f}")
    col3.metric("Min AQI", f"{min_aqi:.1f}")
    col4.metric("Average PM2.5", f"{avg_pm25:.1f} µg/m³")
    col5.metric("Average NO2", f"{avg_no2:.1f} µg/m³")
    
    st.divider()

    # Section 1: AQI Trend
    st.header("1. AQI Trend")
    if view_level == "Station":
        fig_trend = px.line(station_aqi_df, x='date', y='aqi', color='station_name', title="Daily AQI Trend by Station")
    else:
        if selected_city == "All Cities":
            fig_trend = px.line(city_aqi_df, x='date', y='aqi', color='city', title="Daily AQI Trend by City")
        else:
            fig_trend = px.line(city_aqi_df, x='date', y='aqi', title=f"Daily AQI Trend for {selected_city}")
    st.plotly_chart(fig_trend, use_container_width=True)

    # Section 2: Comparisons
    st.header("2. Comparisons")
    col_comp1, col_comp2 = st.columns(2)
    
    with col_comp1:
        # City Comparison - ALWAYS SHOW (as per user instruction)
        # We need all cities data for the selected date range for this specific chart
        all_cities_df = get_daily_city_aqi(start_date, end_date, "All Cities")
        if not all_cities_df.empty:
            city_avg = all_cities_df.groupby('city')['aqi'].mean().reset_index()
            fig_city = px.bar(city_avg, x='city', y='aqi', title="Average AQI by City", color='city')
            st.plotly_chart(fig_city, use_container_width=True)
        else:
            st.info("No city data available for comparison.")
            
    with col_comp2:
        # Station Comparison
        if not station_aqi_df.empty:
            station_avg = station_aqi_df.groupby('station_name')['aqi'].mean().reset_index()
            fig_station = px.bar(station_avg, x='station_name', y='aqi', title="Average AQI by Station", color='station_name')
            st.plotly_chart(fig_station, use_container_width=True)
        else:
            st.info("No station data available for comparison.")

    # Section 3: Pollutant Analysis
    st.header("3. Pollutants & Categories")
    col_pol1, col_pol2 = st.columns(2)
    
    with col_pol1:
        if not station_aqi_df.empty and 'pm25' in station_aqi_df.columns and 'no2' in station_aqi_df.columns:
            fig_scatter = px.scatter(station_aqi_df, x='pm25', y='no2', color='station_name', hover_data=['date'], title="PM2.5 vs NO2")
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info("Insufficient data for PM2.5 vs NO2 scatter plot.")
            
    with col_pol2:
        if not station_aqi_df.empty and 'aqi_category' in station_aqi_df.columns:
            cat_counts = station_aqi_df['aqi_category'].value_counts().reset_index()
            cat_counts.columns = ['aqi_category', 'count']
            fig_cat = px.bar(cat_counts, x='aqi_category', y='count', title="AQI Category Distribution", color='aqi_category')
            st.plotly_chart(fig_cat, use_container_width=True)
        else:
            st.info("No AQI category data available.")

    # Section 4: Weather & Hourly Patterns
    st.header("4. Weather Relationships & Hourly Patterns")
    col_wea1, col_wea2 = st.columns(2)
    
    with col_wea1:
        # Weather vs AQI
        weather_df = get_weather_aggregate(start_date, end_date, selected_station_id, selected_city)
        if not weather_df.empty and 'temperature_c' in weather_df.columns and weather_df['temperature_c'].notna().any():
            # Filter out NaNs for scatter plot
            weather_df_clean = weather_df.dropna(subset=['temperature_c', 'aqi'])
            if not weather_df_clean.empty:
                fig_weather = px.scatter(weather_df_clean, x='temperature_c', y='aqi', color='station_name', 
                                         title="Daily Average Temperature vs Daily AQI",
                                         labels={'temperature_c': 'Temperature (°C)', 'aqi': 'AQI'})
                st.plotly_chart(fig_weather, use_container_width=True)
            else:
                st.info("Not enough matching weather/AQI records for comparison.")
        else:
            st.info("No weather data available.")
            
    with col_wea2:
        # Hourly Pollution Pattern
        if not hourly_df.empty and 'hour' in hourly_df.columns:
            hourly_avg = hourly_df.groupby('hour')[['pm25', 'no2']].mean().reset_index()
            fig_hourly = px.line(hourly_avg, x='hour', y='pm25', title="Average PM2.5 by Hour of Day",
                                 labels={'hour': 'Hour (UTC)', 'pm25': 'Avg PM2.5'})
            st.plotly_chart(fig_hourly, use_container_width=True)
        else:
            st.info("No hourly data available for pattern analysis.")

    # Section 5: Data Coverage
    st.header("5. Station Data Coverage")
    coverage_df = get_station_coverage()
    
    if not coverage_df.empty:
        # Show coverage for selected city if filtering is needed, else show all
        if selected_city != "All Cities":
            coverage_df = coverage_df[coverage_df['city'] == selected_city]
            
        if not coverage_df.empty:
            fig_cov = px.bar(coverage_df, x='station_name', y='obs_count', color='city',
                             title="Total Hourly Observations by Station",
                             labels={'obs_count': 'Number of Hourly Records', 'station_name': 'Station'})
            st.plotly_chart(fig_cov, use_container_width=True)
        else:
            st.info(f"No coverage data for {selected_city}.")
    else:
        st.info("No coverage data.")

# ==========================================
# Methodology & Data Sources
# ==========================================
st.divider()
st.header("Methodology")
st.markdown("""
- **Data Collection**: Pollution data comes from the OpenAQ API v3. Weather enrichment comes from the Open-Meteo API v1.
- **Data Processing**: Data is processed through an automated ETL pipeline orchestrated by Apache Airflow.
- **Analytical Storage**: Validated and transformed records are stored in PostgreSQL.
- **AQI Calculation**: AQI is computed using the Indian National Air Quality Index (NAQI) breakpoints. 
  - Sub-indices are calculated for PM2.5 and NO2 based on 24-hour averages.
  - The final AQI is the maximum applicable sub-index for that day.
  - City AQI is calculated by aggregating raw pollutant concentrations across available stations *first*, before applying the NAQI formula (averaging station AQIs is mathematically invalid).
- **Missing Data**: Missing pollution periods are retained as missing rather than artificially imputed. Weather data acts as enrichment and is not treated as a primary pollutant.
""")

st.header("Data Sources")
st.markdown("""
- **Air Pollution**: [OpenAQ](https://openaq.org/)
- **Weather**: [Open-Meteo](https://open-meteo.com/)
- **Database**: Local PostgreSQL (`aqi_db`)
""")
