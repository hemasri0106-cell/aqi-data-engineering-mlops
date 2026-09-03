import pandas as pd
import json
import glob

# 3. VERIFY HOURLY AGGREGATION
hourly_df = pd.read_csv('data/cleaned/cleaned_hourly.csv')
print(f"Number of hourly pollution records: {len(hourly_df)}")
print(f"Number of unique pollution timestamps: {hourly_df['timestamp_utc_hr'].nunique()}")
hourly_with_weather = hourly_df.dropna(subset=['temperature_c'])
print(f"Number of hourly records with weather: {len(hourly_with_weather)}")
print(f"Number of hourly records without weather: {len(hourly_df) - len(hourly_with_weather)}")

# 4. VERIFY AQI OUTPUT
daily_df = pd.read_csv('data/cleaned/cleaned_daily.csv')
print(f"Number of daily records: {len(daily_df)}")
aqi_records = daily_df.dropna(subset=['aqi'])
print(f"Number of daily AQI values: {len(aqi_records)}")
if len(aqi_records) > 0:
    print(f"Minimum AQI: {aqi_records['aqi'].min()}")
    print(f"Maximum AQI: {aqi_records['aqi'].max()}")
    print(f"Average AQI: {aqi_records['aqi'].mean():.2f}")
    print(f"AQI categories present: {aqi_records['aqi_category'].unique()}")

# 5. VERIFY TIME RANGE
print(f"\nPollution:")
poll_df = pd.read_csv('data/staging/pollution/staged_pollution.csv')
print(f"earliest timestamp: {poll_df['timestamp_utc'].min()}")
print(f"latest timestamp: {poll_df['timestamp_utc'].max()}")

print(f"\nWeather:")
weat_df = pd.read_csv('data/staging/weather/staged_weather.csv')
print(f"earliest timestamp: {weat_df['timestamp_local'].min()}")
print(f"latest timestamp: {weat_df['timestamp_local'].max()}")

print(f"\nCleaned hourly:")
print(f"earliest timestamp: {hourly_df['timestamp_utc_hr'].min()}")
print(f"latest timestamp: {hourly_df['timestamp_utc_hr'].max()}")

print(f"\nCleaned daily:")
print(f"earliest date: {daily_df['date'].min()}")
print(f"latest date: {daily_df['date'].max()}")
