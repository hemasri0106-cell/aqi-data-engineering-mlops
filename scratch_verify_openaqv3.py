import requests

api_key = "7c11a735bca440e356eaf28cf5a4da05c6c9b9a2b18b2fa388729745e761d271"
headers = {"X-API-Key": api_key}

# Let's check countries first to get India's ID
url_countries = "https://api.openaq.org/v3/countries"
res_countries = requests.get(url_countries, headers=headers)
if res_countries.status_code == 200:
    for c in res_countries.json().get("results", []):
        if c.get("iso") == "IN" or c.get("name") == "India":
            print("Country India:", c)
            break
else:
    print("Countries API Error:", res_countries.text)

# Let's try v3 locations with iso=IN or just try a location directly
url_loc = "https://api.openaq.org/v3/locations"
params = {"iso": "IN", "limit": 2}
res_loc = requests.get(url_loc, headers=headers, params=params)
print("Locations Status:", res_loc.status_code)
if res_loc.status_code == 200:
    data = res_loc.json()
    print("Locations:", [loc.get('name') for loc in data.get('results', [])])
    if data.get('results'):
        print("Sample location object keys:", data['results'][0].keys())
        print("Sensors in first location:")
        for s in data['results'][0].get("sensors", []):
            print(f"  {s.get('parameter', {}).get('name')}: {s.get('id')}")
else:
    print(res_loc.text)
