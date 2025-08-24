from __future__ import annotations
import os, httpx, json
from typing import Any

class AirflowAdapter:
    def __init__(self):
        self.base = os.getenv("AIRFLOW_BASE_URL", "").rstrip("/")
        self.dag_map = {
            "tokenize_load": os.getenv("AIRFLOW_DAG_TOKENIZE", "tokenize_load"),
            "archive": os.getenv("AIRFLOW_DAG_ARCHIVE", "archive"),
        }
        self.token = os.getenv("AIRFLOW_TOKEN")

    def enabled(self) -> bool:
        return bool(self.base)

    def trigger(self, pipeline_key: str, conf: dict[str, Any]) -> str | None:
        if not self.enabled():
            return None
        dag_id = self.dag_map.get(pipeline_key, pipeline_key)
        url = f"{self.base}/api/v1/dags/{dag_id}/dagRuns"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = {"conf": conf}
        with httpx.Client(timeout=30) as c:
            r = c.post(url, headers=headers, content=json.dumps(payload))
            r.raise_for_status()
            data = r.json()
            return data.get("dag_run_id") or data.get("dagRunId") or data.get("run_id")
