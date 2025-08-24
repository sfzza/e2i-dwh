from __future__ import annotations
import threading, time
from datetime import datetime, timezone
from .models import PipelineRun, RunTask, RunStatus
from .db import SessionLocal
from .pipelines import get_pipeline_tasks  # import dynamic pipeline definitions


class LocalWorker:
    def __init__(self, run: PipelineRun):
        # only keep reference to run, not db
        self.run = run

    def start(self):
        t = threading.Thread(target=self._work, daemon=True)
        t.start()

    def _work(self):
        db = SessionLocal()
        try:
            run = db.query(PipelineRun).get(self.run.id)

            # get dynamic task list for this pipelineKey
            task_names = get_pipeline_tasks(run.pipeline.key)

            if not task_names:
                raise ValueError(f"No tasks defined for pipeline {run.pipeline_key}")

            # create RunTask rows dynamically
            tasks = [
                RunTask(run_id=run.id, name=name, status=RunStatus.PENDING)
                for name in task_names
            ]
            for task in tasks:
                db.add(task)

            run.status = RunStatus.RUNNING
            db.commit()
            db.refresh(run)

            # simulate task execution
            for t in run.tasks:
                t.status = RunStatus.RUNNING
                t.started_at = datetime.now(timezone.utc)
                db.commit()

                # here you could call real business logic, passing run.params
                print(f"Running {t.name} with params: {run.params}")
                time.sleep(1.0)

                t.status = RunStatus.SUCCESS
                t.finished_at = datetime.now(timezone.utc)
                db.commit()

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
