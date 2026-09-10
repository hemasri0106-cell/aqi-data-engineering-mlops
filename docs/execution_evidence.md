# End-to-End Execution Evidence

This document serves as proof of a successful end-to-end execution of the Air Quality Data Pipeline (Phase 5) and the Analytical Dashboard (Phase 6).

## 1. Pipeline Execution (Apache Airflow)
The pipeline was orchestrated using Apache Airflow 3 on Ubuntu WSL2. The DAG (`aqi_data_pipeline`) executes the workflow synchronously, relying on `subprocess.run` with WSL interop and dynamic path translation to trigger the actual project code in the native Windows Python 3.14 environment against the Windows PostgreSQL database.

**Execution Command (from Windows):**
```powershell
wsl -e bash -c "source ~/airflow-venv/bin/activate && export AIRFLOW_HOME=~/airflow && airflow standalone"
```
Wait for Airflow to start, then trigger `aqi_data_pipeline` via http://localhost:8080.

**Task Flow Successfully Completed:**
1. `ingest_openaq` / `ingest_weather` (Parallel ingestion of JSON to `data/raw/`)
2. `validate_raw_data`
3. `run_transformation` (Creates `data/cleaned/cleaned_hourly.csv` and `cleaned_daily.csv`)
4. `validate_cleaned_data`
5. `load_postgresql` (Upserts into `aqi_db`)
6. `verify_database` (Confirms idempotency and data integrity)

## 2. Database Verification Results
The pipeline successfully loaded and validated the transformed records into the PostgreSQL `aqi_db` database without duplication errors.

**Actual verified database output:**
```
--- DATABASE VERIFICATION REPORT ---
Stations count: 5
Hourly count: 823 (Distinct: 823)
Daily count: 43 (Distinct: 43)
City Daily count: 37
Hourly unique constraints passed.
Daily unique constraints passed.

--- DATA QUALITY CHECK ---
City days with missing PM2.5: 0
City days with missing AQI: 0
```
*Note: Due to OpenAQ's current availability window for the specific configured stations, 5 active stations generated 823 verified hourly observations.*

## 3. Dashboard Execution
The Streamlit dashboard successfully queried the PostgreSQL database, generated analytical KPIs, and visualized the multi-city data natively.

**Execution Command:**
```powershell
.\.venv\Scripts\streamlit.exe run dashboard/app.py
```

**Dashboard Launch Success:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.1.15:8501
```

The application correctly evaluated empty states, successfully computed spatial city aggregations without averaging station AQIs, and rendered all interactive Plotly charts as specified.
