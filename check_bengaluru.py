import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()
api_key = os.environ.get('OPENAQ_API_KEY')
headers = {'X-API-Key': api_key}

seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

url = "https://api.openaq.org/v3/locations"
params = {
    "countries_id": 9,
    "limit": 1000
}

resp = requests.get(url, headers=headers, params=params)
locations = resp.json().get('results', [])
bengaluru_locs = []
for loc in locations:
    name = (loc.get('name') or '').lower()
    locality = (loc.get('locality') or '').lower()
    if 'bengaluru' in name or 'bangalore' in name or 'bengaluru' in locality or 'bangalore' in locality:
        bengaluru_locs.append(loc)

for loc in bengaluru_locs:
    loc_id = loc['id']
    sens_url = f"https://api.openaq.org/v3/locations/{loc_id}"
    sens_resp = requests.get(sens_url, headers=headers)
    if sens_resp.status_code != 200:
        continue
    
    data = sens_resp.json().get('results', [])
    if not data: continue
    
    sensors = data[0].get('sensors', [])
    
    pm25_latest = None
    no2_latest = None
    
    for s in sensors:
        param = s.get('parameter', {}).get('name')
        latest = s.get('latest')
        if latest:
            latest_dt = latest.get('datetime', {}).get('utc')
            if latest_dt:
                dt = datetime.fromisoformat(latest_dt.replace('Z', '+00:00'))
                if param == 'pm25': pm25_latest = dt
                if param == 'no2': no2_latest = dt
                
    print(f"ID: {loc_id} | {loc.get('name')}")
    print(f"  PM2.5 latest: {pm25_latest}")
    print(f"  NO2 latest:   {no2_latest}")
    if pm25_latest and no2_latest:
        if pm25_latest > seven_days_ago and no2_latest > seven_days_ago:
            print("  >>> GOOD RECENT CANDIDATE <<<")
            
