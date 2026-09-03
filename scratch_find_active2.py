import requests

api_key = "c89f6784f83552cd284dc695ee570c1f270d4a49ab13e9da5cd5f363429c9e32"
headers = {"X-API-Key": api_key}

url = "https://api.openaq.org/v3/locations"
params = {"iso": "IN", "limit": 100}
response = requests.get(url, headers=headers, params=params)
if response.status_code == 200:
    data = response.json()
    for loc in data.get("results", []):
        if "Delhi" in loc.get("name", ""):
            last = loc.get("datetimeLast", {}).get("utc")
            if last and last.startswith("2026"):
                print(f"Name: {loc['name']}, ID: {loc['id']}, Last: {last}")
                for s in loc.get("sensors", []):
                     if s['parameter']['name'] in ['pm25', 'no2']:
                         print(f"  {s['parameter']['name']} - sensor_id: {s['id']}")
else:
    print("Error:", response.text)
