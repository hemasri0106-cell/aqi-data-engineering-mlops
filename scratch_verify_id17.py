import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAQ_API_KEY")

headers = {"X-API-Key": api_key}
url_loc = "https://api.openaq.org/v3/locations/17"

try:
    loc_resp = requests.get(url_loc, headers=headers).json()
    sensors = loc_resp.get("results", [])[0].get("sensors", [])
    
    print("Sensors for R K Puram:")
    for s in sensors:
        param = s.get("parameter", {}).get("name")
        if param in ["pm25", "no2"]:
            print(f"{param} - ID: {s['id']}, Coverage: {s['coverage']['datetimeFrom']} to {s['coverage']['datetimeTo']}")
            
            # test fetch
            url_meas = f"https://api.openaq.org/v3/sensors/{s['id']}/measurements"
            res = requests.get(url_meas, headers=headers, params={"limit": 1})
            data = res.json().get("results", [])
            if data:
                print(f"  Latest measurement: {data[0]['period']['datetimeFrom']['utc']} -> {data[0]['value']}")
            else:
                print("  No recent measurements.")
except Exception as e:
    print("Error:", e)

