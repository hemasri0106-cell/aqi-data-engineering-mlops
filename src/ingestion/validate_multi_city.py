import os
import json
import pandas as pd
from glob import glob
from datetime import datetime
from src.config import TARGET_CITIES

def validate():
    print("--- MULTI-CITY VALIDATION REPORT ---")
    
    # 1. Config Check
    cities_configured = set(s['city'] for s in TARGET_CITIES)
    print(f"Configured Cities ({len(cities_configured)}): {', '.join(cities_configured)}")
    print(f"Configured Stations: {len(TARGET_CITIES)}")
    
    # 2. Raw Pollution Check
    raw_pollution_dir = os.path.join('data', 'raw', 'pollution')
    pollution_files = glob(os.path.join(raw_pollution_dir, 'openaq_*.json'))
    
    pollution_records = []
    station_stats = {}
    
    for f in pollution_files:
        with open(f, 'r') as fp:
            data = json.load(fp)
            loc_id = data.get('location_id')
            results = data.get('results', [])
            
            # Find station in config
            st = next((s for s in TARGET_CITIES if s['location_id'] == loc_id), None)
            if not st: continue
            
            city = st['city']
            station_name = st['station_name']
            
            pm25_count = sum(1 for r in results if r.get('parameter', {}).get('name') == 'pm25')
            no2_count = sum(1 for r in results if r.get('parameter', {}).get('name') == 'no2')
            
            times = [r.get('period', {}).get('datetimeFrom', {}).get('utc') for r in results]
            times = [pd.to_datetime(t) for t in times if t]
            
            station_stats[loc_id] = {
                'city': city,
                'name': station_name,
                'total_rows': len(results),
                'pm25_count': pm25_count,
                'no2_count': no2_count,
                'min_time': min(times) if times else None,
                'max_time': max(times) if times else None
            }
            
            pollution_records.extend(results)

    print("\n--- Pollution Data Coverage ---")
    for loc_id, stats in station_stats.items():
        print(f"[{stats['city']}] {stats['name']} (ID: {loc_id}):")
        print(f"  Rows: {stats['total_rows']} (PM2.5: {stats['pm25_count']}, NO2: {stats['no2_count']})")
        print(f"  Range: {stats['min_time']} to {stats['max_time']}")
        
        if stats['pm25_count'] == 0:
            print("  ! WARNING: Missing PM2.5 data !")
        if stats['no2_count'] == 0:
            print("  ! WARNING: Missing NO2 data !")
        if stats['total_rows'] == 0:
            print("  ! WARNING: No recent data returned by API !")
            
    # 3. Raw Weather Check
    raw_weather_dir = os.path.join('data', 'raw', 'weather')
    weather_files = glob(os.path.join(raw_weather_dir, 'openmeteo_*.json'))
    
    print("\n--- Weather Data Coverage ---")
    weather_stats = {}
    for f in weather_files:
        with open(f, 'r') as fp:
            data = json.load(fp)
            loc_id = data.get('location_id')
            st = next((s for s in TARGET_CITIES if s['location_id'] == loc_id), None)
            if not st: continue
            
            times = data.get('raw_response', {}).get('hourly', {}).get('time', [])
            print(f"[{st['city']}] Station {loc_id}: {len(times)} hourly records.")

if __name__ == "__main__":
    validate()
