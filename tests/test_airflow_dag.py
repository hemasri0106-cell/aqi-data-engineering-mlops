import os
import pytest
from airflow.models import DagBag

# Ensure the DAG folder is accessible
DAGS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dags')

@pytest.fixture
def dagbag():
    return DagBag(dag_folder=DAGS_FOLDER, include_examples=False)

def test_dag_imports_without_errors(dagbag):
    """Verify that the DAG parses and loads without errors."""
    assert len(dagbag.import_errors) == 0, f"DAG import failures: {dagbag.import_errors}"

def test_aqi_pipeline_dag_exists(dagbag):
    """Verify that the expected DAG ID exists."""
    dag = dagbag.get_dag('aqi_data_pipeline')
    assert dag is not None, "DAG 'aqi_data_pipeline' not found."

def test_aqi_pipeline_tasks(dagbag):
    """Verify all expected tasks are present in the DAG."""
    dag = dagbag.get_dag('aqi_data_pipeline')
    
    expected_tasks = {
        'ingest_openaq',
        'ingest_weather',
        'validate_raw_data',
        'run_transformation',
        'validate_cleaned_data',
        'load_postgresql',
        'verify_database'
    }
    
    actual_tasks = set(task.task_id for task in dag.tasks)
    
    # Assert that all expected tasks are in the DAG
    assert expected_tasks.issubset(actual_tasks), f"Missing tasks: {expected_tasks - actual_tasks}"

def test_aqi_pipeline_dependencies(dagbag):
    """Verify task dependencies are correctly configured."""
    dag = dagbag.get_dag('aqi_data_pipeline')
    
    # validate_raw_data should have 2 upstream tasks (ingest_openaq, ingest_weather)
    validate_raw = dag.get_task('validate_raw_data')
    upstream_ids = set(t.task_id for t in validate_raw.upstream_list)
    assert upstream_ids == {'ingest_openaq', 'ingest_weather'}, f"validate_raw_data has unexpected upstreams: {upstream_ids}"
    
    # run_transformation should be downstream of validate_raw_data
    run_transform = dag.get_task('run_transformation')
    assert run_transform.upstream_task_ids == {'validate_raw_data'}
    
    # load_postgresql should be downstream of validate_cleaned_data
    load_db = dag.get_task('load_postgresql')
    assert load_db.upstream_task_ids == {'validate_cleaned_data'}
