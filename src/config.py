import os
from datetime import datetime, timezone, timedelta

import json

STATIONS_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'stations.json')
try:
    with open(STATIONS_CONFIG_PATH, 'r') as f:
        config_data = json.load(f)
        TARGET_CITIES = config_data.get('stations', [])
except Exception as e:
    print(f"Warning: Failed to load {STATIONS_CONFIG_PATH}: {e}")
    TARGET_CITIES = []

# Explicit date range for historical ML data extraction
# From Jan 1, 2025 to today
END_DATE = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
START_DATE = datetime(2025, 1, 1, tzinfo=timezone.utc)

# Format dates for APIs
START_DATE_STR = START_DATE.isoformat()
END_DATE_STR = END_DATE.isoformat()

# Open-Meteo uses YYYY-MM-DD format
START_DATE_YMD = START_DATE.strftime('%Y-%m-%d')
END_DATE_YMD = END_DATE.strftime('%Y-%m-%d')
