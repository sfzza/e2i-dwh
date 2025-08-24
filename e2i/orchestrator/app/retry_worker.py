from __future__ import annotations
import os, time, threading
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import PipelineRun, RunStatus
from .airflow_adapter import AirflowAdapter

MAX_RETRIES = int(os.getenv("ORCH_MAX_RETRIES", 3))
RETRY_INTERVAL_MINUTES = int(os.getenv("ORCH_RETRY_INTERVAL_MINUTES", 5))

# Create engine + SessionLocal once for the retry worker
db_url = os.getenv("DATABASE_URL")
engine = create_engine(db_url, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, future=True)

def retry_failed_runs():
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=RETRY_INTERVAL_MINUTES)
        runs = (
            db.query(PipelineRun)
              .filter(
                  PipelineRun.status == RunStatus.FAILED,
                  PipelineRun.retry_count < MAX_RETRIES,
                  (PipelineRun.updated_at == None) | (PipelineRun.updated_at < cutoff),
              )
              .all()
        )
        if not runs:
            return

        adapter = AirflowAdapter()
        if not adapter.enabled():
            return

        for run in runs:
            run.retry_count += 1
            run.status = RunStatus.PENDING
            db.commit()

            try:
                dag_ref = adapter.trigger(run.pipeline.key, conf=run.params or {})
                run.external_ref = dag_ref
                run.status = RunStatus.RUNNING
            except Exception as e:
                run.status = RunStatus.FAILED
                run.failure_reason = f"retry_airflow_error: {e}"
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def start_retry_worker():
    def loop():
        while True:
            try:
                retry_failed_runs()
            except Exception as e:
                print(f"retry worker error: {e}")
            time.sleep(RETRY_INTERVAL_MINUTES * 60)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
