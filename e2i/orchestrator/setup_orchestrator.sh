#!/usr/bin/env bash
set -euo pipefail

mkdir -p app tests

cat > requirements.txt <<'TXT'
fastapi>=0.115.0
uvicorn[standard]>=0.30.6
SQLAlchemy>=2.0.35
psycopg2-binary>=2.9.9
pydantic>=2.9.2
python-dotenv>=1.0.1
httpx>=0.27.2
orjson==3.10.7
ulid-py>=1.1.0
TXT

cat > app/db.py <<'PY'
from __future__ import annotations
import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required (PostgreSQL DSN)")

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass

@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
PY

cat > app/models.py <<'PY'
from __future__ import annotations
from enum import Enum as PyEnum
from sqlalchemy import (
    Integer, String, Boolean, Enum as SAEnum, ForeignKey, JSON, DateTime, Index, Text,
    func, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base
from ulid import ULID

class RunStatus(str, PyEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELED = "CANCELED"

class Pipeline(Base):
    __tablename__ = "pipelines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, default=None)
    runs: Mapped[list["PipelineRun"]] = relationship(
        "PipelineRun", back_populates="pipeline", cascade="all, delete-orphan"
    )

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(26), unique=True, index=True,
                                        default=lambda: str(ULID()))
    pipeline_id: Mapped[int] = mapped_column(ForeignKey("pipelines.id"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(SAEnum(RunStatus, name="runstatus"),
                                              default=RunStatus.PENDING, index=True, nullable=False)
    params: Mapped[dict | None] = mapped_column(JSON, default=None)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), index=True)
    external_ref: Mapped[str | None] = mapped_column(String(256))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at: Mapped = mapped_column(DateTime(timezone=True), onupdate=func.now())
    triggered_by: Mapped[str | None] = mapped_column(String(128))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pipeline = relationship("Pipeline", back_populates="runs")
    tasks: Mapped[list["RunTask"]] = relationship("RunTask", back_populates="run",
                                                  cascade="all, delete-orphan")
    __table_args__ = (
        Index("ix_runs_idempotency", "idempotency_key"),
        UniqueConstraint("pipeline_id", "idempotency_key", name="uq_pipeline_idem"),
    )

class RunTask(Base):
    __tablename__ = "run_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("pipeline_runs.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[RunStatus] = mapped_column(SAEnum(RunStatus, name="runstatus_task"),
                                              default=RunStatus.PENDING, nullable=False)
    started_at: Mapped = mapped_column(DateTime(timezone=True))
    finished_at: Mapped = mapped_column(DateTime(timezone=True))
    details: Mapped[dict | None] = mapped_column(JSON, default=None)
    logs_url: Mapped[str | None] = mapped_column(Text)
    run = relationship("PipelineRun", back_populates="tasks")
PY

cat > app/schemas.py <<'PY'
from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional, Literal, List
from datetime import datetime

class RunRequest(BaseModel):
    pipelineId: Optional[int] = None
    pipelineKey: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    idempotencyKey: Optional[str] = Field(None, description="Prevent duplicate enqueues")

class RunResponse(BaseModel):
    runId: str

class RerunResponse(BaseModel):
    runId: str

class TaskDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    status: str
    startedAt: Optional[datetime] = None
    finishedAt: Optional[datetime] = None
    logsUrl: Optional[str] = None
    details: Optional[dict] = None

class RunDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    runId: str
    pipelineKey: str
    status: str
    createdAt: datetime
    updatedAt: Optional[datetime] = None
    params: Optional[dict] = None
    externalRef: Optional[str] = None
    tasks: List[TaskDTO] = []
    retryCount: int = 0
    failureReason: Optional[str] = None

class TaskEvent(BaseModel):
    runId: str
    taskName: str
    status: Literal["PENDING", "RUNNING", "SUCCESS", "FAILED", "CANCELED"]
    startedAt: Optional[datetime] = None
    finishedAt: Optional[datetime] = None
    details: Optional[dict] = None
    logsUrl: Optional[str] = None
PY

cat > app/security.py <<'PY'
from __future__ import annotations
import hmac, hashlib, os, time
from fastapi import Request, HTTPException

SECRET = (os.getenv("ORCH_WEBHOOK_SECRET") or "dev-secret").encode()
SIG_HEADER = "X-Signature"
TS_HEADER = "X-Timestamp"
ALLOWED_SKEW = int(os.getenv("ORCH_WEBHOOK_SKEW_SECS", "300"))

def _hmac(body: bytes, ts: str) -> str:
    mac = hmac.new(SECRET, f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return f"sha256={mac}"

def sign_body(body: bytes, ts: int | None = None) -> tuple[str, str]:
    ts_str = str(int(ts or time.time()))
    return _hmac(body, ts_str), ts_str

def verify_hmac(request: Request, raw_body: bytes):
    sig = request.headers.get(SIG_HEADER)
    ts = request.headers.get(TS_HEADER)
    if not sig or not ts:
        raise HTTPException(status_code=401, detail="Missing signature or timestamp")
    try:
        ts_int = int(ts)
    except ValueError:
        raise HTTPException(status_code=401, detail="Bad timestamp")
    if abs(int(time.time()) - ts_int) > ALLOWED_SKEW:
        raise HTTPException(status_code=401, detail="Stale or future-dated webhook")
    good = _hmac(raw_body, ts)
    if not hmac.compare_digest(sig, good):
        raise HTTPException(status_code=401, detail="Bad signature")
PY

cat > app/airflow_adapter.py <<'PY'
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
PY

cat > app/local_worker.py <<'PY'
from __future__ import annotations
import threading, time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from .models import PipelineRun, RunTask, RunStatus

class LocalWorker:
    def __init__(self, db: Session, run: PipelineRun):
        self.db = db
        self.run = run

    def start(self):
        t = threading.Thread(target=self._work, daemon=True)
        t.start()

    def _work(self):
        tasks = [
            RunTask(run_id=self.run.id, name="extract", status=RunStatus.PENDING),
            RunTask(run_id=self.run.id, name="transform", status=RunStatus.PENDING),
            RunTask(run_id=self.run.id, name="load", status=RunStatus.PENDING),
        ]
        for task in tasks:
            self.db.add(task)
        self.run.status = RunStatus.RUNNING
        self.db.commit()
        self.db.refresh(self.run)

        for t in self.run.tasks:
            t.status = RunStatus.RUNNING
            t.started_at = datetime.now(timezone.utc)
            self.db.commit()
            time.sleep(1.0)
            t.status = RunStatus.SUCCESS
            t.finished_at = datetime.now(timezone.utc)
            self.db.commit()

        self.run.status = RunStatus.SUCCESS
        self.db.commit()
PY

cat > app/seed.py <<'PY'
from __future__ import annotations
from sqlalchemy.orm import Session
from .models import Pipeline

SEEDS = [
    {"key": "tokenize_load", "name": "Tokenize & Load"},
    {"key": "archive", "name": "Archive to cold storage"},
]

def seed_pipelines(db: Session):
    for s in SEEDS:
        exists = db.query(Pipeline).filter_by(key=s["key"]).first()
        if not exists:
            db.add(Pipeline(**s, is_active=True))
    db.commit()
PY

cat > app/routes.py <<'PY'
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

@router.post("/pipelines/run", response_model=RunResponse)
def run_pipeline(payload: RunRequest, request: Request, db: Session = Depends(get_session)):
    if not payload.pipelineId and not payload.pipelineKey:
        raise HTTPException(status_code=400, detail="Provide pipelineId or pipelineKey")

    q = db.query(Pipeline).filter_by(is_active=True)
    pipeline = (q.filter_by(id=payload.pipelineId).first() if payload.pipelineId
                else q.filter_by(key=payload.pipelineKey).first())
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found or inactive")

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

    params = dict(payload.params or {})
    if not params.get("minioKey"):
        if not ALLOW_PLACEHOLDER:
            raise HTTPException(status_code=400, detail="params.minioKey is required")
        params["placeholder"] = True

    triggered_by = (request.headers.get("X-User-Id")
                    or request.headers.get("X-Triggered-By")
                    or ("system:placeholder" if params.get("placeholder") else None))

    run = PipelineRun(
        pipeline_id=pipeline.id, params=params, idempotency_key=idem, triggered_by=triggered_by,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    if params.get("placeholder") and not params.get("minioKey"):
        run.params = {**run.params, "minioKey": f"placeholder/{pipeline.key}/{run.run_id}.csv"}
        db.commit()
        db.refresh(run)

    adapter = AirflowAdapter()
    if adapter.enabled():
        try:
            dag_ref = adapter.trigger(pipeline.key, conf=run.params or {})
            run.external_ref = dag_ref
            run.status = RunStatus.RUNNING
        except Exception as e:
            run.status = RunStatus.FAILED
            run.failure_reason = f"airflow_trigger_error: {e}"
            LocalWorker(db, run).start()
    else:
        LocalWorker(db, run).start()

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
    adapter = AirflowAdapter()
    if adapter.enabled():
        try:
            dag_ref = adapter.trigger(prev.pipeline.key, conf=new_run.params or {})
            new_run.external_ref = dag_ref
            new_run.status = RunStatus.RUNNING
        except Exception as e:
            new_run.status = RunStatus.FAILED
            new_run.failure_reason = f"airflow_trigger_error: {e}"
    else:
        LocalWorker(db, new_run).start()
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
PY

cat > app/retry_worker.py <<'PY'
from __future__ import annotations
import os, time, threading
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import PipelineRun, RunStatus
from .airflow_adapter import AirflowAdapter

MAX_RETRIES = int(os.getenv("ORCH_MAX_RETRIES", 3))
RETRY_INTERVAL_MINUTES = int(os.getenv("ORCH_RETRY_INTERVAL_MINUTES", 5))

def retry_failed_runs():
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url, future=True, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    with SessionLocal() as db:
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
PY

cat > app/main.py <<'PY'
from __future__ import annotations
import os
import uvicorn
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from .db import Base, engine, get_session
from .routes import router
from .seed import seed_pipelines
from .retry_worker import start_retry_worker

app = FastAPI(title="Orchestrator Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    with get_session() as db:
        seed_pipelines(db)
    start_retry_worker()

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or os.urandom(8).hex()
    response = await call_next(request)
    response.headers["X-Request-ID"] = rid
    return response

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    return {"ready": True}

app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8002)), reload=True)
PY

cat > tests/test_smoke.py <<'PY'
def test_placeholder():
    assert True
PY

cat > .env <<'ENV'
# Local dev: app runs on macOS, Postgres runs on localhost (Docker)
DATABASE_URL=postgresql+psycopg2://e2i_user:e2i_pass@localhost:5432/e2i_db

# Airflow (optional); leave blank to use local worker
AIRFLOW_BASE_URL=
AIRFLOW_TOKEN=

# Webhook HMAC
ORCH_WEBHOOK_SECRET=supersecret
ORCH_WEBHOOK_SKEW_SECS=300

# Placeholder toggle (true until Epic B is wired)
ORCH_ALLOW_PLACEHOLDER=true

# Retry policy
ORCH_MAX_RETRIES=3
ORCH_RETRY_INTERVAL_MINUTES=5

# Service
PORT=8002
ENV

cat > Dockerfile <<'DOCKER'
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
EXPOSE 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
DOCKER

echo "✅ Files written. Next: install deps."
