from __future__ import annotations
import pendulum
from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

def process_upload(**context):
    conf = context["dag_run"].conf or {}
    upload_id = conf.get("upload_id", "dummy-no-id")

    if upload_id.startswith("dummy-"):
        print(f"[Dummy Mode] No real upload found. Using generated upload_id={upload_id}")
        # simulate creating a dummy file
        with open(f"/tmp/{upload_id}.csv", "w") as f:
            f.write("col1,col2\n1,2\n3,4\n")
    else:
        print(f"[Real Mode] Processing real upload with upload_id={upload_id}")

with DAG(
    dag_id="poc_pipeline",
    start_date=pendulum.datetime(2025, 8, 22, tz="UTC"),
    catchup=False,
    tags=["epic-c", "poc"],
) as dag:

    start_task = BashOperator(
        task_id="start_task",
        bash_command="echo 'Starting the Epic C PoC pipeline...'",
    )

    process_task = PythonOperator(
        task_id="process_upload",
        python_callable=process_upload,
        provide_context=True,
    )

    end_task = BashOperator(
        task_id="end_task",
        bash_command="echo 'The PoC pipeline has finished successfully!'",
    )

    start_task >> process_task >> end_task
