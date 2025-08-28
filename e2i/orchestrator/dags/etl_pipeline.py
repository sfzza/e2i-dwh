from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import time

def fake_extract(**kwargs):
    print("Extracting (fake)...")
    time.sleep(2)

def fake_transform(**kwargs):
    print("Transforming (fake)...")
    time.sleep(2)

def fake_load(**kwargs):
    print("Loading (fake)...")
    time.sleep(2)

def fake_archive(**kwargs):
    print("Archiving (fake)...")
    time.sleep(2)

with DAG(
    dag_id="etl_pipeline",
    start_date=days_ago(1),
    schedule_interval=None,
    catchup=False,
    tags=["etl", "fake"],
) as dag:
    extract = PythonOperator(task_id="extract", python_callable=fake_extract)
    transform = PythonOperator(task_id="transform", python_callable=fake_transform)
    load = PythonOperator(task_id="load", python_callable=fake_load)
    archive = PythonOperator(task_id="archive", python_callable=fake_archive)

    extract >> transform >> load >> archive
