import os
import pandas as pd
import logging
import numpy as np

logger = logging.getLogger('transformation.aggregator')

def calculate_naqi_subindex(pollutant: str, avg_val: float) -> float:
    """Calculates the Indian NAQI sub-index for a given pollutant and concentration."""
    if pd.isna(avg_val) or avg_val < 0:
        return np.nan
        
    avg_val = round(avg_val)
        
    # Breakpoints for Indian NAQI
    # Format: [(conc_low, conc_high, aqi_low, aqi_high), ...]
    breakpoints = {
        'pm25': [
            (0, 30, 0, 50), (31, 60, 51, 100), (61, 90, 101, 200),
            (91, 120, 201, 300), (121, 250, 301, 400), (251, 1000, 401, 500)
        ],
        'pm10': [
            (0, 50, 0, 50), (51, 100, 51, 100), (101, 250, 101, 200),
            (251, 350, 201, 300), (351, 430, 301, 400), (431, 1000, 401, 500)
        ],
        'no2': [
            (0, 40, 0, 50), (41, 80, 51, 100), (81, 180, 101, 200),
            (181, 280, 201, 300), (281, 400, 301, 400), (401, 1000, 401, 500)
        ]
    }
    
    if pollutant not in breakpoints:
        return np.nan
        
    for (c_low, c_high, i_low, i_high) in breakpoints[pollutant]:
        if c_low <= avg_val <= c_high:
            # Linear interpolation formula
            return ((i_high - i_low) / (c_high - c_low)) * (avg_val - c_low) + i_low
            
    return np.nan

def get_aqi_category(aqi: float) -> str:
    """Returns the NAQI category string."""
    if pd.isna(aqi): return "Unknown"
    if aqi <= 50: return "Good"
    if aqi <= 100: return "Satisfactory"
    if aqi <= 200: return "Moderate"
    if aqi <= 300: return "Poor"
    if aqi <= 400: return "Very Poor"
    return "Severe"

def aggregate_and_join(pollution_df: pd.DataFrame, weather_df: pd.DataFrame, cleaned_dir: str):
    """Joins weather and pollution, aggregates hourly/daily, calculates AQI."""
    logger.info("Aggregating and joining data...")
    os.makedirs(cleaned_dir, exist_ok=True)
    
    if pollution_df.empty:
        logger.warning("Pollution DataFrame is empty. Cannot join.")
        return
        
    # Pivot pollution so pollutants become columns
    poll_pivoted = pollution_df.pivot_table(
        index=['city', 'station', 'timestamp_utc_hr'],
        columns='pollutant',
        values='value',
        aggfunc='mean'
    ).reset_index()
    
    # 1. Hourly Join
    if not weather_df.empty:
        # Weather is now fetched per station coordinates, but remains enrichment data.
        # We join on city, station, and time.
        # We use a LEFT join so that weather-only rows are discarded.
        # We only keep weather for timestamps where pollution data exists.
        weather_sub = weather_df[['city', 'station', 'timestamp_utc_hr', 'temperature_c', 'humidity_pct', 'precipitation_mm', 'wind_speed_kmh']]
        hourly_joined = pd.merge(poll_pivoted, weather_sub, on=['city', 'station', 'timestamp_utc_hr'], how='left')
    else:
        hourly_joined = poll_pivoted
        
    # Save hourly data
    hourly_file = os.path.join(cleaned_dir, 'cleaned_hourly.csv')
    hourly_joined.to_csv(hourly_file, index=False)
    logger.info(f"Saved {len(hourly_joined)} hourly records to {hourly_file}")
    
    # 2. Daily Aggregation & AQI Calculation
    # NAQI requires 24-hr averages for PM2.5, PM10, NO2. 
    # For a simple daily rollup, we will average by day.
    hourly_joined['date'] = hourly_joined['timestamp_utc_hr'].dt.date
    
    # Identify which numeric columns exist
    numeric_cols = hourly_joined.select_dtypes(include=[np.number]).columns.tolist()
    
    daily_agg = hourly_joined.groupby(['city', 'station', 'date'])[numeric_cols].mean().reset_index()
    
    # Calculate AQI
    daily_agg['aqi_pm25'] = daily_agg['pm25'].apply(lambda x: calculate_naqi_subindex('pm25', x)) if 'pm25' in daily_agg else np.nan
    daily_agg['aqi_no2'] = daily_agg['no2'].apply(lambda x: calculate_naqi_subindex('no2', x)) if 'no2' in daily_agg else np.nan
    
    # Overall AQI is the max of the sub-indices (if available)
    aqi_cols = [c for c in ['aqi_pm25', 'aqi_no2'] if c in daily_agg.columns]
    
    if aqi_cols:
        daily_agg['aqi'] = daily_agg[aqi_cols].max(axis=1, skipna=False) # skipna=False requires all to be present to be robust, but assignment sample is small
        daily_agg['aqi_category'] = daily_agg['aqi'].apply(get_aqi_category)
        logger.info("Calculated NAQI based on available pollutants.")
    else:
        daily_agg['aqi'] = np.nan
        daily_agg['aqi_category'] = "Unknown"
        logger.warning("Insufficient pollutants available in current sample to calculate NAQI.")

    # Save daily data
    daily_file = os.path.join(cleaned_dir, 'cleaned_daily.csv')
    daily_agg.to_csv(daily_file, index=False)
    logger.info(f"Saved {len(daily_agg)} daily records to {daily_file}")
    
    return hourly_joined, daily_agg
