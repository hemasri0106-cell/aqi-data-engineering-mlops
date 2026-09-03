# Air Quality Index Analysis and Prediction
**Phase 1 Project Report**

---

## 1. Abstract / Executive Summary
Air pollution remains a critical public health challenge, particularly in rapidly developing nations. The ability to monitor, analyze, and eventually forecast Air Quality Index (AQI) is paramount for proactive environmental management. This report details the successful implementation of Part 1 of the "Air Quality Index Analysis and Prediction" project. Part 1 establishes a robust, automated Data Engineering pipeline that ingests historical air pollution data alongside meteorological enrichment data across multiple Indian cities. Utilizing Apache Airflow for orchestration, the pipeline extracts data from public APIs (OpenAQ, Open-Meteo), strictly validates it, transforms it into an analytical schema using the Indian National Air Quality Index (NAQI) methodology, and loads it into a PostgreSQL data warehouse. Finally, an interactive Streamlit dashboard is deployed to visualize localized historical trends, pollutant comparisons, and spatial distributions. The architecture natively supports the future inclusion of Machine Learning (MLOps) components planned for Part 2.

## 2. Introduction
### 2.1 The Air Quality Problem
Poor air quality, driven by high concentrations of Fine Particulate Matter (PM2.5) and Nitrogen Dioxide (NO2), contributes to severe respiratory and cardiovascular issues. Accurate monitoring systems generate vast amounts of granular sensor data; however, converting this raw JSON telemetry into actionable insights requires significant data engineering.

### 2.2 Motivation
The motivation behind this project is to bridge the gap between raw environmental sensors and analytical decision-making. By creating an automated, idempotent ETL (Extract, Transform, Load) pipeline, we can guarantee that researchers and analysts have access to clean, validated, and temporally-aligned pollution metrics.

### 2.3 Project Objective
The primary objective of Part 1 is to build the data infrastructure. This includes:
1. Automated data ingestion from external APIs.
2. Robust data validation and cleaning logic.
3. Accurate computation of the Indian NAQI.
4. Relational database storage capable of analytical querying.
5. An interactive presentation layer (Dashboard).

## 3. Problem Understanding and Requirements
The core challenge lies in handling heterogeneous data sources. Air pollution sensors often experience downtime, generating missing periods. Furthermore, API payloads vary in unit measurements, timezone offsets, and payload structures.

The requirements dictated a solution that:
- Never artificially fabricates missing data (imputation is reserved for potential ML models in Part 2).
- Resolves temporal misalignments by standardizing all timestamps to Coordinated Universal Time (UTC).
- Rejects anomalous values (e.g., negative concentrations) while preserving auditability via a rejected-records log.
- Performs spatial aggregation accurately (e.g., City AQI must be calculated from spatially averaged raw pollutants, not by incorrectly averaging pre-calculated station AQI indices).

## 4. Data Sources
The pipeline integrates two independent, public REST APIs:

### 4.1 OpenAQ (Air Pollution)
- **Role:** Primary source of truth for historical pollution concentration measurements.
- **Data Characteristics:** High-frequency, sensor-level readings for PM2.5 and NO2. The API (v3) returns nested JSON objects containing `location_id`, coordinates, values, and local/UTC timestamps.
- **Access Method:** Accessed via Python `requests`. Requires a registered API key securely passed via an environment variable (`OPENAQ_API_KEY`).

### 4.2 Open-Meteo (Weather)
- **Role:** Contextual meteorological enrichment (Temperature, Humidity, Precipitation, Wind Speed).
- **Data Characteristics:** Highly structured hourly archive data generated from meteorological models.
- **Access Method:** Open-source API requiring no authentication. Dynamically queried based on the specific latitude and longitude boundaries of the OpenAQ stations.

## 5. System Architecture
The project architecture strictly follows a classic Batch-ETL paradigm, orchestrated locally.

### 5.1 Pipeline Flow
1. **Source Layer:** OpenAQ (Pollution) and Open-Meteo (Weather).
2. **Ingestion Layer:** Python request scripts orchestrated by Apache Airflow.
3. **Raw Landing Layer:** JSON payloads are saved to a local `data/raw/` directory, acting as a data lake for raw telemetry.
4. **Staging / Transformation Layer:** Pandas is utilized to parse JSON, normalize UTC times, merge pollution with weather, and compute the NAQI.
5. **Storage Layer:** A PostgreSQL 18.6 relational database holding the finalized star-schema (or snowflake) analytical tables.
6. **Presentation Layer:** A Streamlit web application that directly queries the PostgreSQL warehouse.

*(Please refer to `docs/architecture_diagram.mermaid` for the visual representation).*

## 6. Data Ingestion
Data ingestion scripts (`src/ingestion/openaq_ingest.py` and `openmeteo_ingest.py`) are designed to be idempotent and stateless.

- **Collectors:** Python scripts dynamically read a configured `config/stations.json` file to identify active monitoring targets.
- **Raw Landing:** To ensure no data is lost during transit, the raw JSON response is immediately serialized and dumped to `data/raw/` partitioned by source and timestamp.
- **Error Handling:** Network timeouts and HTTP 4xx/5xx errors are caught via standard try-except blocks and logged securely to `logs/ingestion.log`.

## 7. ETL and Data Transformation
The core logic resides in `src/pipeline_phase3.py` and `src/transformation/aggregator.py`.

### 7.1 Staging and Cleaning
Raw JSON is flattened into Pandas DataFrames. Time series indices are coerced using `pd.to_datetime(..., utc=True)` to eliminate local time zone variations. All records are floored to the nearest hour.

### 7.2 Duplicate Removal
Intra-hour duplicates from the same station (a common occurrence in sensor data) are resolved by grouping by `['station', 'timestamp_utc_hr', 'pollutant']` and aggregating via the `mean()` function.

### 7.3 Weather Join and Aggregation
Weather data acts strictly as an enrichment layer. The pipeline performs a Left Join (Pollution `LEFT JOIN` Weather) using the City, Station, and UTC Hour keys. Weather rows without corresponding pollution data are discarded to prevent "phantom" AQI records. The hourly granular data is then rolled up into a daily average (Daily Aggregation) to prepare for NAQI computation.

## 8. Data Quality and Validation
Data quality is strictly enforced before database insertion.

### 8.1 Validation Rules
- **Range Checks:** Any observation where PM2.5 or NO2 is less than `0.0` is flagged as a sensor error.
- **Rejected Records:** Anomalous records are dropped from the analytical pipeline and appended to `data/rejected/rejected_records.csv` alongside a `rejection_reason` string.

### 8.2 Missing Periods
The pipeline calculates a continuous hourly index between the minimum and maximum observation times for a station. Missing timestamps are counted and logged, ensuring transparency regarding sensor uptime without resorting to artificial backfilling.

### 8.3 Database Constraints
PostgreSQL enforces uniqueness at the physical layer. Unique constraints on `(station_id, timestamp_utc)` and `(city, date)` guarantee that redundant pipeline executions do not duplicate historical facts.

## 9. AQI Calculation Methodology
The project strictly implements the **Indian National Air Quality Index (NAQI)**.

### 9.1 Pollutant Sub-Indices
Daily average concentrations for PM2.5 and NO2 are rounded to the nearest integer. Sub-indices are calculated using piecewise linear interpolation against the NAQI standard breakpoints.

### 9.2 Final Station AQI
The overall Station AQI evaluates to the maximum of the available sub-indices. If a station lacks valid pollutant data on a given day, the AQI safely evaluates to `NaN` and the category to "Unknown".

### 9.3 City AQI Methodology
Crucially, City AQI is derived by spatially averaging raw pollutant concentrations across all active stations in a city *before* applying the NAQI formula. Averaging individual station AQI values is mathematically invalid due to the non-linear health impact scale of the index.

## 10. PostgreSQL Analytical Warehouse
The finalized data is loaded into `aqi_db` using SQLAlchemy. The schema supports robust analytical querying:

- **`stations`**: Dimension table for location metadata (linked via OpenAQ `location_id`).
- **`hourly_air_quality`**: Granular fact table for hourly PM2.5, NO2, and meteorological context.
- **`daily_aqi`**: Fact table storing daily averages, sub-indices, and final Station AQI.
- **`daily_city_aqi`**: Analytical presentation table storing spatially aggregated City AQI.

The loading script uses `INSERT ... ON CONFLICT DO UPDATE` to gracefully handle upserts, enabling idempotent execution.

## 11. Airflow Orchestration
Apache Airflow orchestrates the pipeline (`dags/aqi_pipeline.py`).

### 11.1 DAG Structure
The Directed Acyclic Graph defines a logical dependency chain:
1. `ingest_openaq` and `ingest_weather` (Run in parallel)
2. `validate_raw_data`
3. `run_transformation`
4. `validate_cleaned_data`
5. `load_postgresql`
6. `verify_database`

*(Note: Due to a known Windows `preexec_fn` compatibility constraint with the `BashOperator`, the DAG utilizes the `PythonOperator` to securely invoke the primary project environment via `subprocess.run`).*

## 12. Streamlit Dashboard
The presentation layer is built using Streamlit and Plotly (`dashboard/app.py`).

### 12.1 Features
- **Dynamic Filters:** Users can filter by Date Range, City, and Station. The station dropdown dynamically limits choices to only those stations that possess actual database observations.
- **KPI Metrics:** At-a-glance averages for AQI, PM2.5, and NO2.
- **Visualizations:** The dashboard features AQI Trend line charts, City/Station comparison bar charts, and PM2.5 vs NO2 scatter plots.
- **Meteorological Insights:** A scatter plot maps Daily Average Temperature against Daily AQI to explore weather correlations.

## 13. Results and Observations
Based on the actual local execution of the pipeline, the system ingested historical telemetry for 5 actively reporting stations across 4 Indian cities (Delhi, Mumbai, Chennai, Kolkata). 

**Current Database Metrics:**
- **Verified Hourly Records:** 613 distinct observations.
- **Verified Daily Records:** 34 distinct station days.
- **Verified City Records:** 29 distinct city days.
- **Data Quality:** 0 records suffered from anomalous negative values; database constraints successfully prevented all duplication attempts during idempotency testing.

**Observations:** The dashboard immediately reveals significant temporal variance in PM2.5, aligning with anticipated urban emission patterns. Weather correlation plots correctly integrate the Open-Meteo context without artificially duplicating the daily AQI indices.

## 14. Limitations
Honesty regarding data limitations is crucial for subsequent analytical phases:
- **Station Coverage:** While configurations for 10 stations across 5 cities were attempted, the OpenAQ v3 API currently only provided recent historical telemetry for 5 specific stations. Cities like Bengaluru did not return viable recent observations within the exact parameters, resulting in an honest 0-row footprint for that city in the analytical layer.
- **Missing Periods:** Sensor downtime resulted in inherent gaps in the hourly continuity. This was logged but not imputed, leaving sparse periods in the time-series charts.

## 15. Conclusion
Part 1 of the Air Quality Index Analysis and Prediction project has successfully met all data engineering requirements. The pipeline reliably fetches, cleans, transforms, and loads complex environmental data into a relational warehouse, making it immediately available for interactive visualization. The rigid adherence to correct mathematical methodologies (specifically regarding spatial City AQI aggregation) ensures the data is analytically sound.

## 16. Future Work / Part 2
The completion of Part 1 paves the way for advanced analytical modeling. **The following features are slated for Part 2 and are currently strictly separated from the existing architecture**:

1. **Machine Learning:** Utilizing the historical PostgreSQL data to train predictive models (e.g., Random Forests, LSTMs) to forecast next-day AQI.
2. **MLOps Tracking:** Integrating MLflow to track model experiments, hyperparameters, and registry versions.
3. **Model Deployment:** Serving the trained models via a FastAPI REST endpoint.
4. **Containerization:** Packaging the entire pipeline (Airflow, PostgreSQL, FastAPI, Streamlit) using Docker for scalable, environment-agnostic deployment.

## 17. References / Data Sources
1. **OpenAQ API:** [https://openaq.org/](https://openaq.org/) - Provision of PM2.5 and NO2 pollutant telemetry.
2. **Open-Meteo API:** [https://open-meteo.com/](https://open-meteo.com/) - Provision of meteorological archive data.
3. **Indian National Air Quality Index (NAQI):** Central Pollution Control Board (CPCB) methodology and breakpoint definitions.
