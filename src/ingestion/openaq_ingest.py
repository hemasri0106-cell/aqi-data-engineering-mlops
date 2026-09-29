import os
import sys
import json
import logging
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from src.config import TARGET_CITIES, START_DATE_STR, END_DATE_STR

# Setup logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, 'ingestion.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('openaq_ingestion')

load_dotenv()
OPENAQ_API_KEY = os.getenv('OPENAQ_API_KEY')
if not OPENAQ_API_KEY:
    logger.error("OPENAQ_API_KEY not found in environment variables.")
    sys.exit(1)

RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'raw', 'pollution')

def fetch_location_sensors(location_id):
    url = f"https://api.openaq.org/v3/locations/{location_id}"
    headers = {"X-API-Key": OPENAQ_API_KEY}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get('results'):
            return data['results'][0].get('sensors', []), data['results'][0].get('name')
        return [], None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching sensors for location {location_id}: {e}")
        return [], None

from datetime import datetime, timezone, timedelta

def fetch_sensor_measurements(sensor_id, start_date_str, end_date_str):
    url = f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements"
    headers = {"X-API-Key": OPENAQ_API_KEY}
    
    start_dt = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
    end_dt = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
    
    all_results = []
    
    current_start = start_dt
    while current_start < end_dt:
        current_end = min(current_start + timedelta(days=30), end_dt)
        
        page = 1
        while True:
            params = {
                "datetime_from": current_start.isoformat(),
                "datetime_to": current_end.isoformat(),
                "limit": 1000,
                "page": page
            }
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                results = data.get('results', [])
                if not results:
                    break
                all_results.extend(results)
                if len(results) < 1000:
                    break
                page += 1
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching measurements for sensor {sensor_id} on page {page} for dates {current_start} to {current_end}: {e}")
                break
                
        current_start = current_end
            
    return all_results

def main():
    logger.info(f"Starting OpenAQ ingestion for {len(TARGET_CITIES)} cities from {START_DATE_STR} to {END_DATE_STR}")
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    
    for city_config in TARGET_CITIES:
        city = city_config['city']
        loc_id = city_config['location_id']
        target_params = city_config['pollutants']
        
        logger.info(f"Processing {city} (Location ID: {loc_id})")
        sensors, loc_name = fetch_location_sensors(loc_id)
        if not sensors:
            logger.error(f"No sensors found for location {loc_id}. Skipping.")
            continue
            
        all_measurements = []
        for sensor in sensors:
            param_name = sensor.get('parameter', {}).get('name')
            if param_name in target_params:
                sensor_id = sensor.get('id')
                logger.info(f"Fetching {param_name} (Sensor {sensor_id}) for period {START_DATE_STR} to {END_DATE_STR}")
                measurements = fetch_sensor_measurements(sensor_id, START_DATE_STR, END_DATE_STR)
                if measurements:
                    all_measurements.extend(measurements)
                    logger.info(f"Fetched {len(measurements)} records for {param_name}.")
                else:
                    logger.warning(f"No measurements returned for {param_name} in requested range.")
                    
        if not all_measurements:
            logger.error(f"No measurements fetched for {city} in the requested range.")
            continue
            
        filepath = os.path.join(RAW_DATA_DIR, f"openaq_{city.lower()}_{loc_id}.json")
        
        try:
            with open(filepath, 'w') as f:
                json.dump({
                    "source": "OpenAQ v3",
                    "location_id": loc_id,
                    "location_name": loc_name,
                    "city": city,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "requested_range": {"start": START_DATE_STR, "end": END_DATE_STR},
                    "results": all_measurements
                }, f, indent=4)
            logger.info(f"Saved {len(all_measurements)} records to {filepath}")
            logger.info(f"source: OpenAQ, location: {city}, status: SUCCESS, row_count: {len(all_measurements)}, extracted_at: {datetime.now(timezone.utc).isoformat()}")
            print(f"OpenAQ: {city} ingestion successful! {len(all_measurements)} records.")
        except Exception as e:
            logger.error(f"Failed to save raw data for {city}: {e}")

if __name__ == "__main__":
    main()
