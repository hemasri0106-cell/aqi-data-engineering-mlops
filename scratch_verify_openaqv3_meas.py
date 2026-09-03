import requests

api_key = "7c11a735bca440e356eaf28cf5a4da05c6c9b9a2b18b2fa388729745e761d271"
headers = {"X-API-Key": api_key}

# Let's get the ID of Delhi Technological University, Delhi - CPCB
url_loc = "https://api.openaq.org/v3/locations"
params = {"iso": "IN", "limit": 2}
res_loc = requests.get(url_loc, headers=headers, params=params)
if res_loc.status_code == 200:
    data = res_loc.json()
    dtu_loc = next((l for l in data.get('results', []) if "Delhi" in l.get("name")), None)
    if dtu_loc:
        loc_id = dtu_loc['id']
        print(f"Found location ID: {loc_id} for {dtu_loc['name']}")
        
        # Test fetching measurements for this location? Wait, OpenAQ v3 uses /sensors/{sensor_id}/measurements or /locations/{locations_id}/measurements?
        # Let's try /locations/{loc_id}/measurements
        res_meas = requests.get(f"https://api.openaq.org/v3/locations/{loc_id}/measurements", headers=headers, params={"limit": 5})
        print("/locations/.../measurements Status:", res_meas.status_code)
        if res_meas.status_code == 200:
            print("Measurements:", res_meas.json().get('results', []))
        else:
            print("Failed to get location measurements:", res_meas.text)
            
        # Maybe /v3/sensors/{id}/measurements
        sensor_id = dtu_loc['sensors'][0]['id']
        res_sens = requests.get(f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements", headers=headers, params={"limit": 5})
        print("/sensors/.../measurements Status:", res_sens.status_code)
        if res_sens.status_code == 200:
            print("Sensor measurements:", res_sens.json().get('results', []))
        else:
            print("Failed to get sensor measurements:", res_sens.text)
            
