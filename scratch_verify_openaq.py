import requests

api_key = "7c11a735bca440e356eaf28cf5a4da05c6c9b9a2b18b2fa388729745e761d271"
headers = {"X-API-Key": api_key}

# Let's test the v2 locations endpoint for India
url = "https://api.openaq.org/v2/locations"
params = {
    "country": "IN",
    "limit": 5
}
response = requests.get(url, headers=headers, params=params)
print("Status Code:", response.status_code)
if response.status_code == 200:
    data = response.json()
    print("Found", data.get("meta", {}).get("found"), "locations.")
    for loc in data.get("results", []):
        print(f"City: {loc.get('city')}, Location: {loc.get('name')}, Parameters: {[p.get('parameter') for p in loc.get('parameters', [])]}")
else:
    print(response.text)
