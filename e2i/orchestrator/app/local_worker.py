from __future__ import annotations
import threading, time
from datetime import datetime, timezone

from .models import PipelineRun, RunTask, RunStatus
from .db import SessionLocal
from .pipelines import get_pipeline_tasks   # 👈 comes from app/pipelines/__init__.py


class LocalWorker:
    """
    LocalWorker is a simple, threaded executor that:
    - Loads the PipelineRun from DB
    - Resolves tasks from pipelines/
    - Runs tasks sequentially (extract → transform → load …)
    - Updates DB with task/run status + timestamps
    """

    def __init__(self, run: PipelineRun):
        self.run = run

    def start(self):
        # Run worker in a background thread (non-blocking)
        t = threading.Thread(target=self._work, daemon=True)
        t.start()

    def _work(self):
        db = SessionLocal()
        run: PipelineRun | None = None

        try:
            # Reload run from DB to ensure fresh session
            run = db.query(PipelineRun).get(self.run.id)

            # Safely resolve pipeline key
            pipeline_key = run.pipeline.key if run.pipeline else str(run.pipeline_id)
            task_names = get_pipeline_tasks(pipeline_key)

            if not task_names:
                raise ValueError(f"No tasks defined for pipeline {pipeline_key}")

            # Create RunTask rows if not already created
            if not run.tasks:
                tasks = [
                    RunTask(run_id=run.id, name=name, status=RunStatus.PENDING)
                    for name in task_names
                ]
                db.add_all(tasks)
                db.commit()
                db.refresh(run)

            # Mark pipeline run as running
            run.status = RunStatus.RUNNING
            db.commit()

            # Run tasks sequentially
            for task in run.tasks:
                task.status = RunStatus.RUNNING
                task.started_at = datetime.now(timezone.utc)
                db.commit()

                print(f"Running {task.name} with params: {run.params}")

                # --- placeholder for real ETL function ---
                time.sleep(1.0)  # simulate work

                # Check if user requested forced failure (for testing)
                if run.params and run.params.get("forceFail"):
                    task.status = RunStatus.FAILED
                    task.finished_at = datetime.now(timezone.utc)
                    run.status = RunStatus.FAILED
                    run.failure_reason = f"Task {task.name} failed due to forceFail flag"
                    db.commit()
                    return

                # Otherwise mark success
                task.status = RunStatus.SUCCESS
                task.finished_at = datetime.now(timezone.utc)
                db.commit()

            # If all succeed → mark run SUCCESS
            run.status = RunStatus.SUCCESS
            db.commit()

        except Exception as e:
            db.rollback()
            if run:
                run.status = RunStatus.FAILED
                run.failure_reason = str(e)
                db.commit()
            raise
        finally:
            db.close()
