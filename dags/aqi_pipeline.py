import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import subprocess

# Resolve project root explicitly for Windows compatibility
DAGS_FOLDER = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DAGS_FOLDER)

# Path to the primary Python 3.14 virtual environment
PYTHON_BIN = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2026, 9, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'aqi_data_pipeline',
    default_args=default_args,
    description='Orchestrates the AQI data extraction, transformation, and load pipeline.',
    schedule_interval='@daily',
    catchup=False,
    tags=['aqi', 'academic'],
) as dag:
    
    # Helper to create PythonOperators that run scripts via subprocess to avoid Windows preexec_fn errors
    def execute_script(script_path):
        env = os.environ.copy()
        env['PYTHONPATH'] = PROJECT_ROOT
        result = subprocess.run([PYTHON_BIN, script_path], cwd=PROJECT_ROOT, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Script failed with error:\n{result.stderr}")
        print(result.stdout)

    def run_script(task_id, script_path):
        return PythonOperator(
            task_id=task_id,
            python_callable=execute_script,
            op_kwargs={'script_path': script_path},
        )

    # 1. Ingestion Tasks (Parallel)
    ingest_openaq = run_script('ingest_openaq', os.path.join(PROJECT_ROOT, 'src', 'ingestion', 'openaq_ingest.py'))
    ingest_weather = run_script('ingest_weather', os.path.join(PROJECT_ROOT, 'src', 'ingestion', 'openmeteo_ingest.py'))

    # 2. Raw Data Validation
    validate_raw_data = run_script('validate_raw_data', os.path.join(PROJECT_ROOT, 'src', 'ingestion', 'validate_multi_city.py'))

    # 3. Phase 3 Transformation
    run_transformation = run_script('run_transformation', os.path.join(PROJECT_ROOT, 'src', 'pipeline_phase3.py'))

    # 4. Cleaned Data Validation
    def validate_cleaned():
        script = (
            "import pandas as pd, os;"
            "assert len(pd.read_csv(os.path.join('data', 'cleaned', 'cleaned_hourly.csv'))) > 0;"
            "assert len(pd.read_csv(os.path.join('data', 'cleaned', 'cleaned_daily.csv'))) > 0;"
            "print('Cleaned data validated.')"
        )
        result = subprocess.run([PYTHON_BIN, "-c", script], cwd=PROJECT_ROOT, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Validation failed with error:\n{result.stderr}")
        print(result.stdout)

    validate_cleaned_data = PythonOperator(
        task_id='validate_cleaned_data',
        python_callable=validate_cleaned,
    )

    # 5. Database Load
    load_postgresql = run_script('load_postgresql', os.path.join(PROJECT_ROOT, 'src', 'database', 'loader.py'))

    # 6. Database Verification
    verify_database = run_script('verify_database', os.path.join(PROJECT_ROOT, 'src', 'database', 'verify_db.py'))

    # Define Dependencies
    [ingest_openaq, ingest_weather] >> validate_raw_data
    validate_raw_data >> run_transformation >> validate_cleaned_data >> load_postgresql >> verify_database
