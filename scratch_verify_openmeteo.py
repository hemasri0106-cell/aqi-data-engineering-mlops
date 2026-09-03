import requests

url = "https://api.open-meteo.com/v1/forecast"
# Delhi coordinates roughly: 28.6139, 77.2090
params = {
    "latitude": 28.6139,
    "longitude": 77.2090,
    "hourly": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
    "timezone": "auto"
}
response = requests.get(url, params=params)
print("Open-Meteo Status:", response.status_code)
if response.status_code == 200:
    data = response.json()
    hourly = data.get("hourly", {})
    print("Keys found in hourly:", list(hourly.keys()))
    print("Sample values:")
    for k in hourly.keys():
        print(f"  {k}: {hourly[k][:3]}...")
else:
    print(response.text)
