import os
import json
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from src.database.connection import get_engine
from src.database.models import Base, Station, HourlyAirQuality, DailyAQI, DailyCityAQI
from src.transformation.aggregator import calculate_naqi_subindex, get_aqi_category

def get_stations_config():
    config_path = os.path.join('config', 'stations.json')
    with open(config_path, 'r') as f:
        return json.load(f).get('stations', [])

def load_data():
    engine = get_engine()
    Base.metadata.create_all(engine)
    
    hourly_df = pd.read_csv(os.path.join('data', 'cleaned', 'cleaned_hourly.csv'))
    daily_df = pd.read_csv(os.path.join('data', 'cleaned', 'cleaned_daily.csv'))
    
    if hourly_df.empty and daily_df.empty:
        print("No data to load.")
        return

    # Replace NaNs with None for DB insertion
    hourly_df = hourly_df.replace({np.nan: None})
    daily_df = daily_df.replace({np.nan: None})
    
    # Extract unique valid locations that actually have data
    valid_locations = set(hourly_df['station'].unique()) | set(daily_df['station'].unique())
    stations_config = get_stations_config()
    
    with Session(engine) as session:
        # 1. Load Stations
        print("Loading stations...")
        station_id_map = {}
        for st in stations_config:
            if st['station_name'] in valid_locations:
                stmt = insert(Station).values(
                    station_name=st['station_name'],
                    city=st['city'],
                    source=st.get('source'),
                    location_id=st['location_id'],
                    latitude=st.get('latitude'),
                    longitude=st.get('longitude')
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=['location_id'],
                    set_={
                        'station_name': stmt.excluded.station_name,
                        'city': stmt.excluded.city,
                        'source': stmt.excluded.source,
                        'latitude': stmt.excluded.latitude,
                        'longitude': stmt.excluded.longitude
                    }
                )
                session.execute(stmt)
        session.commit()
        
        # Build station_name to station_id map
        db_stations = session.query(Station).all()
        for db_st in db_stations:
            station_id_map[db_st.station_name] = db_st.station_id
            
        # 2. Load Hourly Air Quality
        print(f"Loading {len(hourly_df)} hourly records...")
        hourly_records = []
        for _, row in hourly_df.iterrows():
            if row['station'] not in station_id_map: continue
            
            hourly_records.append({
                'station_id': station_id_map[row['station']],
                'timestamp_utc': row['timestamp_utc_hr'],
                'no2': row['no2'],
                'pm25': row['pm25'],
                'temperature_c': row.get('temperature_c'),
                'humidity_pct': row.get('humidity_pct'),
                'precipitation_mm': row.get('precipitation_mm'),
                'wind_speed_kmh': row.get('wind_speed_kmh')
            })
            
        if hourly_records:
            stmt = insert(HourlyAirQuality).values(hourly_records)
            stmt = stmt.on_conflict_do_update(
                index_elements=['station_id', 'timestamp_utc'],
                set_={
                    'no2': stmt.excluded.no2,
                    'pm25': stmt.excluded.pm25,
                    'temperature_c': stmt.excluded.temperature_c,
                    'humidity_pct': stmt.excluded.humidity_pct,
                    'precipitation_mm': stmt.excluded.precipitation_mm,
                    'wind_speed_kmh': stmt.excluded.wind_speed_kmh
                }
            )
            session.execute(stmt)
        session.commit()

        # 3. Load Daily AQI
        print(f"Loading {len(daily_df)} daily records...")
        daily_records = []
        for _, row in daily_df.iterrows():
            if row['station'] not in station_id_map: continue
            daily_records.append({
                'station_id': station_id_map[row['station']],
                'date': row['date'],
                'no2': row['no2'],
                'pm25': row['pm25'],
                'temperature_c': row.get('temperature_c'),
                'humidity_pct': row.get('humidity_pct'),
                'precipitation_mm': row.get('precipitation_mm'),
                'wind_speed_kmh': row.get('wind_speed_kmh'),
                'aqi_pm25': row.get('aqi_pm25'),
                'aqi_no2': row.get('aqi_no2'),
                'aqi': row.get('aqi'),
                'aqi_category': row.get('aqi_category')
            })
            
        if daily_records:
            stmt = insert(DailyAQI).values(daily_records)
            stmt = stmt.on_conflict_do_update(
                index_elements=['station_id', 'date'],
                set_={
                    'no2': stmt.excluded.no2,
                    'pm25': stmt.excluded.pm25,
                    'temperature_c': stmt.excluded.temperature_c,
                    'humidity_pct': stmt.excluded.humidity_pct,
                    'precipitation_mm': stmt.excluded.precipitation_mm,
                    'wind_speed_kmh': stmt.excluded.wind_speed_kmh,
                    'aqi_pm25': stmt.excluded.aqi_pm25,
                    'aqi_no2': stmt.excluded.aqi_no2,
                    'aqi': stmt.excluded.aqi,
                    'aqi_category': stmt.excluded.aqi_category
                }
            )
            session.execute(stmt)
        session.commit()
        
        # 4. Calculate and Load Daily City AQI
        print("Calculating and loading city daily AQI...")
        # We need to average pollutants across stations for each city/date
        daily_df_numeric = pd.read_csv(os.path.join('data', 'cleaned', 'cleaned_daily.csv'))
        city_groups = daily_df_numeric.groupby(['city', 'date'])
        
        city_records = []
        for (city, date), group in city_groups:
            # Aggregate values
            avg_pm25 = group['pm25'].mean() if 'pm25' in group and not group['pm25'].isna().all() else np.nan
            avg_no2 = group['no2'].mean() if 'no2' in group and not group['no2'].isna().all() else np.nan
            avg_temp = group['temperature_c'].mean() if 'temperature_c' in group and not group['temperature_c'].isna().all() else np.nan
            avg_hum = group['humidity_pct'].mean() if 'humidity_pct' in group and not group['humidity_pct'].isna().all() else np.nan
            avg_prec = group['precipitation_mm'].mean() if 'precipitation_mm' in group and not group['precipitation_mm'].isna().all() else np.nan
            avg_wind = group['wind_speed_kmh'].mean() if 'wind_speed_kmh' in group and not group['wind_speed_kmh'].isna().all() else np.nan
            
            # Calculate NAQI dynamically
            aqi_pm25 = calculate_naqi_subindex('pm25', avg_pm25)
            aqi_no2 = calculate_naqi_subindex('no2', avg_no2)
            
            sub_indices = [x for x in [aqi_pm25, aqi_no2] if pd.notna(x)]
            final_aqi = max(sub_indices) if sub_indices else np.nan
            aqi_category = get_aqi_category(final_aqi)
            
            city_records.append({
                'city': city,
                'date': date,
                'pm25': None if pd.isna(avg_pm25) else float(avg_pm25),
                'no2': None if pd.isna(avg_no2) else float(avg_no2),
                'temperature_c': None if pd.isna(avg_temp) else float(avg_temp),
                'humidity_pct': None if pd.isna(avg_hum) else float(avg_hum),
                'precipitation_mm': None if pd.isna(avg_prec) else float(avg_prec),
                'wind_speed_kmh': None if pd.isna(avg_wind) else float(avg_wind),
                'aqi_pm25': None if pd.isna(aqi_pm25) else float(aqi_pm25),
                'aqi_no2': None if pd.isna(aqi_no2) else float(aqi_no2),
                'aqi': None if pd.isna(final_aqi) else float(final_aqi),
                'aqi_category': aqi_category
            })
            
        if city_records:
            stmt = insert(DailyCityAQI).values(city_records)
            stmt = stmt.on_conflict_do_update(
                index_elements=['city', 'date'],
                set_={
                    'no2': stmt.excluded.no2,
                    'pm25': stmt.excluded.pm25,
                    'temperature_c': stmt.excluded.temperature_c,
                    'humidity_pct': stmt.excluded.humidity_pct,
                    'precipitation_mm': stmt.excluded.precipitation_mm,
                    'wind_speed_kmh': stmt.excluded.wind_speed_kmh,
                    'aqi_pm25': stmt.excluded.aqi_pm25,
                    'aqi_no2': stmt.excluded.aqi_no2,
                    'aqi': stmt.excluded.aqi,
                    'aqi_category': stmt.excluded.aqi_category
                }
            )
            session.execute(stmt)
        session.commit()
        
    print("Database loading complete.")

if __name__ == "__main__":
    load_data()
