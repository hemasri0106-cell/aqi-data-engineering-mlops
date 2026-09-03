import os
import json
import logging
import pandas as pd
from glob import glob

from src.config import TARGET_CITIES

logger = logging.getLogger('transformation.staging')

def get_station_info(loc_id):
    for st in TARGET_CITIES:
        if st.get('location_id') == loc_id:
            return st
    return None

def stage_pollution_data(raw_dir: str, staging_dir: str) -> pd.DataFrame:
    """Parses raw OpenAQ JSON files and converts them into a staging DataFrame."""
    logger.info("Staging pollution data...")
    raw_files = glob(os.path.join(raw_dir, 'openaq_*.json'))
    
    all_records = []
    
    for file in raw_files:
        with open(file, 'r') as f:
            data = json.load(f)
            
            loc_id = data.get('location_id')
            st_info = get_station_info(loc_id)
            if not st_info:
                logger.warning(f"Unknown location_id {loc_id} in {file}. Skipping.")
                continue
                
            source = st_info.get('source', data.get('source', 'OpenAQ'))
            city = st_info.get('city')
            location_name = st_info.get('station_name')
            
            for result in data.get('results', []):
                val = result.get('value')
                param_name = result.get('parameter', {}).get('name')
                param_units = result.get('parameter', {}).get('units')
                
                # Using the datetimeFrom of the period as the timestamp
                period = result.get('period', {})
                dt_from = period.get('datetimeFrom', {})
                ts_utc = dt_from.get('utc')
                ts_local = dt_from.get('local')
                
                all_records.append({
                    'city': city,
                    'station': location_name,
                    'timestamp_utc': ts_utc,
                    'timestamp_local': ts_local,
                    'pollutant': param_name,
                    'value': val,
                    'unit': param_units,
                    'source': source
                })
                
    df = pd.DataFrame(all_records)
    
    if not df.empty:
        os.makedirs(staging_dir, exist_ok=True)
        staging_file = os.path.join(staging_dir, 'staged_pollution.csv')
        df.to_csv(staging_file, index=False)
        logger.info(f"Staged {len(df)} pollution records to {staging_file}")
    else:
        logger.warning("No pollution records found to stage.")
        
    return df

def stage_weather_data(raw_dir: str, staging_dir: str) -> pd.DataFrame:
    """Parses raw Open-Meteo JSON files and converts them into a staging DataFrame."""
    logger.info("Staging weather data...")
    raw_files = glob(os.path.join(raw_dir, 'openmeteo_*.json'))
    
    all_records = []
    
    for file in raw_files:
        with open(file, 'r') as f:
            data = json.load(f)
            
            loc_id = data.get('location_id')
            st_info = get_station_info(loc_id)
            if not st_info:
                logger.warning(f"Unknown location_id {loc_id} in weather file {file}. Skipping.")
                continue
                
            source = data.get('source', 'Open-Meteo')
            city = st_info.get('city')
            station = st_info.get('station_name')
            
            raw_response = data.get('raw_response', {})
            hourly = raw_response.get('hourly', {})
            
            times = hourly.get('time', [])
            temps = hourly.get('temperature_2m', [])
            humids = hourly.get('relative_humidity_2m', [])
            precips = hourly.get('precipitation', [])
            winds = hourly.get('wind_speed_10m', [])
            
            utc_offset_seconds = raw_response.get('utc_offset_seconds', 0)
            
            for i in range(len(times)):
                all_records.append({
                    'city': city,
                    'station': station, # Adding station to weather to join properly
                    'timestamp_local': times[i], 
                    'utc_offset_seconds': utc_offset_seconds,
                    'temperature_c': temps[i] if i < len(temps) else None,
                    'humidity_pct': humids[i] if i < len(humids) else None,
                    'precipitation_mm': precips[i] if i < len(precips) else None,
                    'wind_speed_kmh': winds[i] if i < len(winds) else None,
                    'source': source
                })

    df = pd.DataFrame(all_records)
    
    if not df.empty:
        os.makedirs(staging_dir, exist_ok=True)
        staging_file = os.path.join(staging_dir, 'staged_weather.csv')
        df.to_csv(staging_file, index=False)
        logger.info(f"Staged {len(df)} weather records to {staging_file}")
    else:
        logger.warning("No weather records found to stage.")
        
    return df
