from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional, Literal, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Any, Optional

class RunRequest(BaseModel):
    pipelineId: Optional[str] = None   # change to str, not int
    pipelineKey: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    idempotencyKey: Optional[str] = Field(None, description="Prevent duplicate enqueues")

    @model_validator(mode="before")
    def normalize_pipeline_key(cls, values):
        # if caller sends pipelineId, treat it like pipelineKey
        key = values.get("pipelineKey") or values.get("pipelineId")
        if not key:
            raise ValueError("One of pipelineKey or pipelineId is required")
        values["pipelineKey"] = key
        return values

    @property
    def key(self) -> str:
        return self.pipelineKey

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
