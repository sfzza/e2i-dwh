# e2i/orchestrator/app/models.py - FIXED VERSION

from __future__ import annotations
from enum import Enum as PyEnum
from datetime import datetime
import uuid
from sqlalchemy import (
    Integer, String, Boolean, Enum as SAEnum, ForeignKey, JSON, DateTime, Index, Text,
    func, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

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
    dag_id: Mapped[str] = mapped_column(String(255), nullable=False)  # ADDED
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # ADDED
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, default=None)
    
    # Relationships
    runs: Mapped[list["PipelineRun"]] = relationship(
        "PipelineRun", back_populates="pipeline", cascade="all, delete-orphan"
    )

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36), unique=True, index=True,
                                        default=lambda: str(uuid.uuid4()))
    pipeline_id: Mapped[int] = mapped_column(ForeignKey("pipelines.id"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(SAEnum(RunStatus, name="runstatus"),
                                              default=RunStatus.PENDING, index=True, nullable=False)
    params: Mapped[dict | None] = mapped_column(JSON, default=None)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), index=True)
    external_ref: Mapped[str | None] = mapped_column(String(256))
    failure_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 server_default=func.now(), index=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True),
                                                       onupdate=func.now())
    triggered_by: Mapped[str | None] = mapped_column(String(128))
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
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
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, default=None)
    logs_url: Mapped[str | None] = mapped_column(Text)
    
    # Relationships
    run = relationship("PipelineRun", back_populates="tasks")