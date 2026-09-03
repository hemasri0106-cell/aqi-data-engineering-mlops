import os
import json
import pandas as pd
from datetime import datetime, timezone
from src.config import TARGET_CITIES, START_DATE, END_DATE

print(f"Requested Extraction Window (UTC): {START_DATE} to {END_DATE}")

print("\n--- Final Coverage Table ---")
print(f"{'City':<10} | {'Station':<45} | {'Location ID':<11} | {'PM2.5':<5} | {'NO2':<5} | {'Pollution rows':<15} | {'Earliest UTC':<25} | {'Latest UTC':<25} | {'Weather rows'}")
print("-" * 170)

for st in TARGET_CITIES:
    loc_id = st['location_id']
    city = st['city']
    name = st['station_name']
    
    # Pollution
    poll_file = os.path.join('data', 'raw', 'pollution', f"openaq_{city.lower()}_{loc_id}.json")
    poll_rows = 0
    earliest_utc = None
    latest_utc = None
    pm25_count = 0
    no2_count = 0
    if os.path.exists(poll_file):
        with open(poll_file, 'r') as f:
            data = json.load(f)
            results = data.get('results', [])
            poll_rows = len(results)
            times = [pd.to_datetime(r.get('period', {}).get('datetimeFrom', {}).get('utc')) for r in results if r.get('period', {}).get('datetimeFrom', {}).get('utc')]
            if times:
                earliest_utc = min(times).strftime("%Y-%m-%d %H:%M:%S")
                latest_utc = max(times).strftime("%Y-%m-%d %H:%M:%S")
            pm25_count = sum(1 for r in results if r.get('parameter', {}).get('name') == 'pm25')
            no2_count = sum(1 for r in results if r.get('parameter', {}).get('name') == 'no2')
            
    # Weather
    weather_file = os.path.join('data', 'raw', 'weather', f"openmeteo_{city.lower()}_{loc_id}.json")
    weather_rows = 0
    if os.path.exists(weather_file):
        with open(weather_file, 'r') as f:
            data = json.load(f)
            weather_rows = len(data.get('raw_response', {}).get('hourly', {}).get('time', []))
            
    print(f"{city:<10} | {name:<45} | {loc_id:<11} | {pm25_count:<5} | {no2_count:<5} | {poll_rows:<15} | {str(earliest_utc):<25} | {str(latest_utc):<25} | {weather_rows}")

# Load phase 3 outputs
cleaned_hourly = pd.read_csv(os.path.join('data', 'cleaned', 'cleaned_hourly.csv'))
cleaned_daily = pd.read_csv(os.path.join('data', 'cleaned', 'cleaned_daily.csv'))

print("\n--- Phase 3 Validation Metrics ---")
print(f"Number of cities with data: {cleaned_hourly['city'].nunique()}")
print(f"Number of stations with data: {cleaned_hourly['station'].nunique()}")
print(f"Final hourly rows: {len(cleaned_hourly)}")
print(f"Final daily rows: {len(cleaned_daily)}")
print(f"Missing Weather (Hourly rows with NaNs in weather cols): {cleaned_hourly['temperature_c'].isna().sum()}")

print("\nAQI Category Distribution:")
print(cleaned_daily['aqi_category'].value_counts().to_string())

# Verify UTC normalization
print("\nVerifying UTC normalization...")
staged = pd.read_csv(os.path.join('data', 'staging', 'pollution', 'staged_pollution.csv'))
tz_info = staged['timestamp_utc'].str.extract(r'([+-]\d{2}:\d{2})$')[0].unique()
print(f"Timezone offsets in staged pollution data: {tz_info}")
