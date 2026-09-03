import requests

api_key = "c89f6784f83552cd284dc695ee570c1f270d4a49ab13e9da5cd5f363429c9e32"
headers = {"X-API-Key": api_key}

url = "https://api.openaq.org/v3/locations"
params = {"iso": "IN", "limit": 20}
response = requests.get(url, headers=headers, params=params)
if response.status_code == 200:
    data = response.json()
    for loc in data.get("results", []):
        if "Delhi" in loc.get("name", "") or "Delhi" in str(loc.get("locality")):
            print(f"Name: {loc['name']}, ID: {loc['id']}, Last updated: {loc['datetimeLast']}")
else:
    print("Error:", response.text)
