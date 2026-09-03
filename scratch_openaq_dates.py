import requests
import datetime

api_key = "7c11a735bca440e356eaf28cf5a4da05c6c9b9a2b18b2fa388729745e761d271"
headers = {"X-API-Key": api_key}

# Let's test fetching the last 7 days of measurements for Sensor ID 13864 (PM2.5) or 13866 (NO2)
sensor_id = 13864

# Calculate dates
end_date = datetime.datetime.now(datetime.timezone.utc)
start_date = end_date - datetime.timedelta(days=7)

url = f"https://api.openaq.org/v3/sensors/{sensor_id}/measurements"
params = {
    "datetime_from": start_date.isoformat(),
    "datetime_to": end_date.isoformat(),
    "limit": 5
}
print(f"Requesting: {url} with params {params}")
response = requests.get(url, headers=headers, params=params)
if response.status_code == 200:
    data = response.json()
    results = data.get("results", [])
    print(f"Found {len(results)} results")
    for r in results:
        print(r.get("period", {}).get("datetimeFrom", {}).get("utc"), r.get("value"))
else:
    print(f"Error: {response.status_code} - {response.text}")

# Let's check another sensor or endpoint if the above is empty
url_loc = "https://api.openaq.org/v3/locations/13"
loc_resp = requests.get(url_loc, headers=headers).json()
print("Location Sensors:")
for s in loc_resp.get("results", [])[0].get("sensors", []):
    print(f"{s['parameter']['name']} - ID: {s['id']}, Coverage: {s['coverage']['datetimeFrom']} to {s['coverage']['datetimeTo']}")
