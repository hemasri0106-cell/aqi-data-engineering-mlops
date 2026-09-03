# Data Dictionary

This document outlines the schema of the analytical data warehouse hosted in PostgreSQL (`aqi_db`). 
The schema consists of four main tables: `stations`, `hourly_air_quality`, `daily_aqi`, and `daily_city_aqi`.

---

## Table: `stations`
Stores metadata and location details for all active air quality monitoring stations in the system.

| Column Name | Data Type | Description | Primary / Foreign Key | Nullable | Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `station_id` | Integer | Internal surrogate key for the station. | **Primary Key** | No | `1` |
| `station_name` | String | Human-readable name of the monitoring station. | None | No | `"DTU, Delhi - CPCB"` |
| `city` | String | The city where the station is located. | None | No | `"Delhi"` |
| `source` | String | The source network providing the station data. | None | Yes | `"cpcb"` |
| `location_id` | Integer | The external ID assigned by OpenAQ (v3). | None (Unique) | No | `13` |
| `latitude` | Float | Latitude coordinates of the station. | None | Yes | `28.75` |
| `longitude` | Float | Longitude coordinates of the station. | None | Yes | `77.111` |

---

## Table: `hourly_air_quality`
Stores hourly raw pollutant and weather enrichment measurements. Serves as the primary granular fact table.

| Column Name | Data Type | Description | Primary / Foreign Key | Nullable | Unit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | Integer | Internal surrogate key. | **Primary Key** | No | - |
| `station_id` | Integer | Reference to the station taking the reading. | **Foreign Key** (`stations.station_id`) | No | - |
| `timestamp_utc` | DateTime (TZ) | Floor-rounded hour in UTC of the reading. | None | No | - |
| `no2` | Float | Nitrogen Dioxide concentration. | None | Yes | µg/m³ |
| `pm25` | Float | Fine Particulate Matter concentration. | None | Yes | µg/m³ |
| `temperature_c` | Float | Ambient temperature. | None | Yes | °C |
| `humidity_pct` | Float | Relative humidity. | None | Yes | % |
| `precipitation_mm` | Float | Hourly precipitation sum. | None | Yes | mm |
| `wind_speed_kmh` | Float | Wind speed (10m). | None | Yes | km/h |

**Constraints:** `UNIQUE (station_id, timestamp_utc)`

---

## Table: `daily_aqi`
Stores daily aggregated pollutant averages, daily weather metrics, and the calculated Indian National Air Quality Index (NAQI) for individual stations.

| Column Name | Data Type | Description | Primary / Foreign Key | Nullable | Unit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | Integer | Internal surrogate key. | **Primary Key** | No | - |
| `station_id` | Integer | Reference to the station. | **Foreign Key** (`stations.station_id`) | No | - |
| `date` | Date | The observation date. | None | No | - |
| `no2` | Float | Daily average Nitrogen Dioxide. | None | Yes | µg/m³ |
| `pm25` | Float | Daily average Fine Particulate Matter. | None | Yes | µg/m³ |
| `temperature_c` | Float | Daily average temperature. | None | Yes | °C |
| `humidity_pct` | Float | Daily average humidity. | None | Yes | % |
| `precipitation_mm` | Float | Daily average precipitation sum. | None | Yes | mm |
| `wind_speed_kmh` | Float | Daily average wind speed. | None | Yes | km/h |
| `aqi_pm25` | Float | Calculated NAQI sub-index for PM2.5. | None | Yes | - |
| `aqi_no2` | Float | Calculated NAQI sub-index for NO2. | None | Yes | - |
| `aqi` | Float | Overall station AQI (MAX of available sub-indices). | None | Yes | - |
| `aqi_category` | String | Descriptive AQI category (e.g., "Good", "Severe"). | None | Yes | - |

**Constraints:** `UNIQUE (station_id, date)`

---

## Table: `daily_city_aqi`
Stores the analytical city-level metrics. It aggregates pollutant concentrations across all stations within a city for a given day *before* dynamically applying the NAQI formula to compute the City AQI.

| Column Name | Data Type | Description | Primary / Foreign Key | Nullable | Unit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `id` | Integer | Internal surrogate key. | **Primary Key** | No | - |
| `city` | String | Name of the city. | None | No | - |
| `date` | Date | The observation date. | None | No | - |
| `no2` | Float | Spatially averaged NO2 across city stations. | None | Yes | µg/m³ |
| `pm25` | Float | Spatially averaged PM2.5 across city stations. | None | Yes | µg/m³ |
| `temperature_c` | Float | Spatially averaged temperature. | None | Yes | °C |
| `humidity_pct` | Float | Spatially averaged humidity. | None | Yes | % |
| `precipitation_mm` | Float | Spatially averaged precipitation. | None | Yes | mm |
| `wind_speed_kmh` | Float | Spatially averaged wind speed. | None | Yes | km/h |
| `aqi_pm25` | Float | Calculated City NAQI sub-index for PM2.5. | None | Yes | - |
| `aqi_no2` | Float | Calculated City NAQI sub-index for NO2. | None | Yes | - |
| `aqi` | Float | Overall City AQI (MAX of available sub-indices). | None | Yes | - |
| `aqi_category` | String | Descriptive AQI category. | None | Yes | - |

**Constraints:** `UNIQUE (city, date)`
