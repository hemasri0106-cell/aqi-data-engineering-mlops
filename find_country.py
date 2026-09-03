import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get('OPENAQ_API_KEY')
headers = {'X-API-Key': api_key}

url = "https://api.openaq.org/v3/countries"
response = requests.get(url, headers=headers, params={'limit': 200})
if response.status_code == 200:
    for c in response.json().get('results', []):
        if c.get('name') == 'India' or c.get('iso') == 'IN':
            print(f"India Country ID: {c.get('id')}, Name: {c.get('name')}")
