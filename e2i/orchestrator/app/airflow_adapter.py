import os, httpx, json
from typing import Any
import logging

class AirflowAdapter:
    def __init__(self):
        self.base = os.getenv("AIRFLOW_BASE_URL", "").rstrip("/")
        self.dag_map = {
            "tokenize_load": os.getenv("AIRFLOW_DAG_TOKENIZE", "tokenize_load"),
            "archive": os.getenv("AIRFLOW_DAG_ARCHIVE", "archive"),
        }
        self.username = os.getenv("AIRFLOW_USERNAME")
        self.password = os.getenv("AIRFLOW_PASSWORD")
        self.token = os.getenv("AIRFLOW_TOKEN")

    def enabled(self) -> bool:
        return bool(self.base)

    def trigger(self, pipeline_key: str, conf: dict[str, Any]) -> str | None:
        if not self.enabled():
            return None
        dag_id = self.dag_map.get(pipeline_key, pipeline_key)
        url = f"{self.base}/dags/{dag_id}/dagRuns"
        headers = {"Content-Type": "application/json"}

        auth = None
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.username and self.password:
            auth = (self.username, self.password)

        payload = {"conf": conf}

        logging.info(f"[AirflowAdapter] Triggering DAG={dag_id} with conf={conf}")
        with httpx.Client(timeout=30) as c:
            r = c.post(url, headers=headers, auth=auth, content=json.dumps(payload))
            logging.info(f"[AirflowAdapter] Airflow response: {r.status_code} {r.text}")
            r.raise_for_status()
            data = r.json()
            return (
                data.get("dag_run_id")
                or data.get("dagRunId")
                or data.get("run_id")
            )
