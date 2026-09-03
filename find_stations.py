import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv()
api_key = os.environ.get('OPENAQ_API_KEY')
headers = {'X-API-Key': api_key}

target_cities = ["Delhi", "Mumbai", "Bengaluru", "Chennai", "Kolkata"]
city_stations = {city: [] for city in target_cities}
thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

page = 1
while True:
    url = "https://api.openaq.org/v3/locations"
    params = {
        "countries_id": 9,
        "limit": 100,
        "page": page
    }
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        break
    data = resp.json().get('results', [])
    if not data:
        break
        
    for loc in data:
        name = loc.get('name', '')
        locality = loc.get('locality', '')
        if not name: continue
        
        target_city = None
        for city in target_cities:
            if city.lower() in name.lower() or (locality and city.lower() in locality.lower()):
                target_city = city
                break
        if not target_city:
            if 'bangalore' in name.lower() or (locality and 'bangalore' in locality.lower()):
                target_city = 'Bengaluru'
        
        if not target_city:
            continue
            
        loc_id = loc['id']
        sens_url = f"https://api.openaq.org/v3/locations/{loc_id}"
        sens_resp = requests.get(sens_url, headers=headers)
        if sens_resp.status_code == 200:
            sens_data = sens_resp.json().get('results', [])
            if sens_data:
                sensors = sens_data[0].get('sensors', [])
                has_pm25 = False
                has_no2 = False
                is_recent = False
                
                for s in sensors:
                    param = s.get('parameter', {}).get('name')
                    latest = s.get('latest')
                    if latest:
                        latest_dt = latest.get('datetime', {}).get('utc')
                        if latest_dt:
                            latest_date = datetime.fromisoformat(latest_dt.replace('Z', '+00:00'))
                            if latest_date > thirty_days_ago:
                                is_recent = True
                                if param == 'pm25': has_pm25 = True
                                if param == 'no2': has_no2 = True
                                
                if has_pm25 and has_no2 and is_recent:
                    city_stations[target_city].append({
                        'name': name,
                        'id': loc_id,
                        'coords': loc.get('coordinates')
                    })
                    print(f"Found: {name} in {target_city}")
    
    # We just need 2 per city, so check if we have enough
    all_done = all(len(s) >= 2 for s in city_stations.values())
    if all_done:
        break
    page += 1

print("\nFinal Results:")
for city, stations in city_stations.items():
    print(f"\nCity: {city} (Found {len(stations)})")
    for s in stations[:2]:
        print(f"  - {s['name']} (ID: {s['id']}), Coords: {s['coords']}")
