from __future__ import annotations
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import os

from .db import get_session
from .models import Pipeline, PipelineRun, RunTask, RunStatus
from .schemas import RunRequest, RunResponse, RunDTO, TaskDTO, RerunResponse, TaskEvent
from .airflow_adapter import AirflowAdapter
from .local_worker import LocalWorker
from .security import verify_hmac
from .config import USE_LOCAL_WORKER

router = APIRouter(prefix="/v1")
ALLOW_PLACEHOLDER = (os.getenv("ORCH_ALLOW_PLACEHOLDER", "true").lower() == "true")

def _task_dto(t: RunTask) -> TaskDTO:
    return TaskDTO(
        id=t.id, name=t.name, status=t.status.value,
        startedAt=t.started_at, finishedAt=t.finished_at,
        logsUrl=t.logs_url, details=t.details or {},
    )

def _run_dto(r: PipelineRun) -> RunDTO:
    return RunDTO(
        runId=r.run_id, pipelineKey=r.pipeline.key, status=r.status.value,
        createdAt=r.created_at, updatedAt=r.updated_at, params=r.params or {},
        externalRef=r.external_ref, tasks=[_task_dto(t) for t in r.tasks],
        retryCount=r.retry_count, failureReason=r.failure_reason,
    )

# app/routes.py

@router.post("/pipelines/run", response_model=RunResponse)
def run_pipeline(payload: RunRequest, request: Request, db: Session = Depends(get_session)):
    # Original check for missing keys - no change here
    if not payload.pipelineId and not payload.pipelineKey:
        raise HTTPException(status_code=400, detail="Provide pipelineId or pipelineKey")

    # ----- START of the updated logic -----
    # Get the key from the payload
    # Note: If you want to use 'req.key' as in your instructions,
    # you'll also need to update your RunRequest schema.
    # For now, we will use the existing `pipelineKey` from your schema.
    pipeline_key = payload.pipelineKey
    
    # Try exact match first
    pipeline = db.query(Pipeline).filter_by(key=pipeline_key, is_active=True).first()
    
    # Fallback: if not found and key starts with 'e2i_', try stripping the prefix
    if not pipeline and pipeline_key and pipeline_key.startswith("e2i_"):
        alt_key = pipeline_key[len("e2i_"):]
        pipeline = db.query(Pipeline).filter_by(key=alt_key, is_active=True).first()

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found or inactive")
    # ----- END of the updated logic -----

    idem = payload.idempotencyKey or request.headers.get("Idempotency-Key")
    if idem:
        existing = (
            db.query(PipelineRun)
              .filter_by(idempotency_key=idem, pipeline_id=pipeline.id)
              .order_by(PipelineRun.id.desc())
              .first()
        )
        if existing:
            return RunResponse(runId=existing.run_id)

    params = payload.params or {}
    if "minioKey" not in params:
        if not ALLOW_PLACEHOLDER:
            raise HTTPException(status_code=400, detail="params.minioKey is required")
        params["placeholder_key"] = True

    triggered_by = (request.headers.get("X-User-Id")
                    or request.headers.get("X-Triggered-By")
                    or ("system:placeholder" if params.get("placeholder_key") else None))

    run = PipelineRun(
        pipeline_id=pipeline.id, params=params, idempotency_key=idem, triggered_by=triggered_by,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    if params.get("placeholder_key"):
        run.params["minioKey"] = f"placeholder/{pipeline.key}/{run.run_id}.csv"
        del run.params["placeholder_key"]
        db.commit()
        db.refresh(run)

    if USE_LOCAL_WORKER:
        # Correctly pass the new `run` object to the LocalWorker
        LocalWorker(run).start()
    else:
        adapter = AirflowAdapter()
        try:
            dag_ref = adapter.trigger(pipeline.key, conf=run.params or {})
            run.external_ref = dag_ref
            run.status = RunStatus.RUNNING
            db.commit()
        except Exception as e:
            run.status = RunStatus.FAILED
            run.failure_reason = f"airflow_trigger_error: {e}"
            db.commit()

    db.refresh(run)
    return RunResponse(runId=run.run_id)

@router.get("/pipelines/runs")
def list_runs(
    status: Optional[str] = None,
    pipelineKey: Optional[str] = None,
    createdFrom: Optional[datetime] = None,
    createdTo: Optional[datetime] = None,
    limit: int = 50, offset: int = 0,
    db: Session = Depends(get_session),
):
    q = db.query(PipelineRun).join(Pipeline)
    if status:
        try:
            q = q.filter(PipelineRun.status == RunStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    if pipelineKey:
        q = q.filter(Pipeline.key == pipelineKey)
    if createdFrom:
        q = q.filter(PipelineRun.created_at >= createdFrom)
    if createdTo:
        q = q.filter(PipelineRun.created_at <= createdTo)
    total = q.count()
    runs = q.order_by(PipelineRun.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [_run_dto(r) for r in runs]}

@router.get("/pipelines/runs/{runId}")
def get_run(runId: str, db: Session = Depends(get_session)):
    run = db.query(PipelineRun).filter_by(run_id=runId).join(Pipeline).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_dto(run)

@router.post("/pipelines/rerun/{runId}", response_model=RerunResponse)
def rerun(runId: str, db: Session = Depends(get_session)):
    prev = db.query(PipelineRun).filter_by(run_id=runId).join(Pipeline).first()
    if not prev:
        raise HTTPException(status_code=404, detail="Run not found")
    new_run = PipelineRun(pipeline_id=prev.pipeline_id, params=prev.params or {}, retry_count=0)
    db.add(new_run)
    db.commit()
    db.refresh(new_run)
    
    if USE_LOCAL_WORKER:
        # Correctly pass the new `run` object to the LocalWorker
        LocalWorker(new_run).start()
    else:
        adapter = AirflowAdapter()
        try:
            dag_ref = adapter.trigger(prev.pipeline.key, conf=new_run.params or {})
            new_run.external_ref = dag_ref
            new_run.status = RunStatus.RUNNING
            db.commit()
        except Exception as e:
            new_run.status = RunStatus.FAILED
            new_run.failure_reason = f"airflow_trigger_error: {e}"
            db.commit()

    return RerunResponse(runId=new_run.run_id)

@router.post("/webhooks/task-events")
async def task_events(request: Request, db: Session = Depends(get_session)):
    raw = await request.body()
    verify_hmac(request, raw)
    payload = TaskEvent.model_validate_json(raw)
    run = db.query(PipelineRun).filter_by(run_id=payload.runId).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    task = db.query(RunTask).filter_by(run_id=run.id, name=payload.taskName).first()
    if not task:
        task = RunTask(run_id=run.id, name=payload.taskName)
        db.add(task)
    task.status = RunStatus(payload.status)
    task.started_at = payload.startedAt or task.started_at
    task.finished_at = payload.finishedAt or task.finished_at
    task.details = payload.details or task.details
    task.logs_url = payload.logsUrl or task.logs_url
    db.commit()
    tasks = db.query(RunTask).filter_by(run_id=run.id).all()
    if any(t.status == RunStatus.FAILED for t in tasks):
        run.status = RunStatus.FAILED
    elif all(t.status == RunStatus.SUCCESS for t in tasks) and tasks:
        run.status = RunStatus.SUCCESS
    elif any(t.status == RunStatus.RUNNING for t in tasks):
        run.status = RunStatus.RUNNING
    db.commit()
    return {"ok": True}