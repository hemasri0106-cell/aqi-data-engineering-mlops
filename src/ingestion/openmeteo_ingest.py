import os
import sys
import json
import logging
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from src.config import TARGET_CITIES, START_DATE_YMD, END_DATE_YMD

# Setup logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'ingestion.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('openmeteo_ingestion')

load_dotenv()
OPEN_METEO_API_URL = os.getenv('OPEN_METEO_API_URL', 'https://api.open-meteo.com/v1/forecast')
RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'raw', 'weather')

def fetch_weather_data(lat, lon, start_date, end_date):
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "timezone": "auto",
        "start_date": start_date,
        "end_date": end_date
    }
    try:
        response = requests.get(OPEN_METEO_API_URL, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data: {e}")
        return None

def main():
    logger.info(f"Starting Open-Meteo ingestion for {len(TARGET_CITIES)} cities from {START_DATE_YMD} to {END_DATE_YMD}")
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    for city_config in TARGET_CITIES:
        city = city_config['city']
        lat = city_config['latitude']
        lon = city_config['longitude']
        loc_id = city_config['location_id']
        
        logger.info(f"Processing weather for {city} - Station {loc_id} ({lat}, {lon})")
        data = fetch_weather_data(lat, lon, START_DATE_YMD, END_DATE_YMD)
        if not data or 'hourly' not in data:
            logger.error(f"Failed to fetch weather data for station {loc_id}. Skipping.")
            continue
            
        time_array = data['hourly'].get('time', [])
        row_count = len(time_array)
        logger.info(f"Fetched {row_count} hourly weather records for station {loc_id}.")
        
        filepath = os.path.join(RAW_DATA_DIR, f"openmeteo_{city.lower()}_{loc_id}.json")
        
        try:
            with open(filepath, 'w') as f:
                json.dump({
                    "source": "Open-Meteo",
                    "city": city,
                    "latitude": lat,
                    "location_id": loc_id,
                    "note": "Weather is city/location-level enrichment, not direct station sensor measurement.",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "requested_range": {"start": START_DATE_YMD, "end": END_DATE_YMD},
                    "raw_response": data
                }, f, indent=4)
            logger.info(f"Saved {row_count} records to {filepath}")
            logger.info(f"source: Open-Meteo, location: {city} (Station {loc_id}), status: SUCCESS, row_count: {row_count}, extracted_at: {datetime.now(timezone.utc).isoformat()}")
            print(f"Open-Meteo: {city} (Station {loc_id}) ingestion successful! {row_count} records.")
        except Exception as e:
            logger.error(f"Failed to save raw weather data for {city} (Station {loc_id}): {e}")

if __name__ == "__main__":
    main()
