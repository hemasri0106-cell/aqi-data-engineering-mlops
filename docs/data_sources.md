# Data Sources & Access

This project relies on two public APIs to construct the analytical data warehouse. Both APIs are queried securely via the data ingestion layer in Phase 2.

## 1. OpenAQ (Air Pollution)

- **Purpose**: Acts as the primary source of truth for all historical and real-time air pollution concentration measurements.
- **Role in Pipeline**: Provides raw sensor data (PM2.5, NO2) for specific `location_id`s mapped to our internal `stations` table.
- **Variables Used**: `pm2.5` and `no2` concentrations (in µg/m³).
- **Access Instructions**:
  - The project utilizes the **OpenAQ API v3**.
  - **API Key**: Access requires a registered API key from [openaq.org](https://openaq.org/).
  - **Configuration**: The API key must be stored securely in the local `.env` file as `OPENAQ_API_KEY=your_key_here`. It is automatically loaded by the pipeline using the `python-dotenv` library.
  - **Endpoint**: `https://api.openaq.org/v3/locations/{id}/measurements`

## 2. Open-Meteo (Weather)

- **Purpose**: Provides meteorological context to enrich the pollution dataset, allowing for downstream analysis of the relationship between weather patterns and air quality.
- **Role in Pipeline**: Fetches hourly weather archives matching the precise latitude/longitude coordinates of the OpenAQ stations.
- **Variables Used**: 
  - Temperature at 2m (°C)
  - Relative Humidity at 2m (%)
  - Precipitation (mm)
  - Wind Speed at 10m (km/h)
- **Access Instructions**:
  - The project utilizes the **Open-Meteo API v1**.
  - **API Key**: Open-Meteo is an open-source API that does **not** require an API key for standard non-commercial usage.
  - **Configuration**: The base URL is stored in the `.env` file as `OPEN_METEO_API_URL=https://archive-api.open-meteo.com/v1/archive`.
  - **Endpoint**: Coordinates are dynamically passed to the endpoint based on the station metadata.

---
**Security Note**: Never commit the `.env` file to version control. All Python scripts use `os.environ.get()` to pull these credentials dynamically at runtime, ensuring secrets are never exposed in the source code or Airflow logs.
