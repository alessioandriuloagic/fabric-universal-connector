"""
Fabric Workload Development Kit — IJobsController request/response models.

Spec: https://learn.microsoft.com/en-us/fabric/workload-development-kit/extensibility-back-end
"""
from __future__ import annotations
from enum import Enum
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field
import uuid


class JobStatus(str, Enum):
    NOT_STARTED = "NotStarted"
    IN_PROGRESS = "InProgress"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    DEDUPED = "Deduped"


class JobType(str, Enum):
    CONNECTOR_INGESTION_JOB = "ConnectorIngestionJob"


# ── Inbound from Fabric Job Scheduler ─────────────────────────────────────────

class ItemReference(BaseModel):
    workspace_id: str = Field(alias="workspaceId")
    item_id: str = Field(alias="itemId")
    item_type: str = Field(alias="itemType")

    model_config = {"populate_by_name": True}


class ExecutionData(BaseModel):
    """Opaque bag forwarded by Fabric — may be empty for scheduled runs."""
    parameters: Optional[Dict[str, Any]] = None


class JobRunContext(BaseModel):
    """
    Payload received in POST /workload/jobs/instances/{jobInstanceId}.
    Fabric sends this when starting a job run.
    """
    job_type: str = Field(alias="jobType")
    invocation_context: Optional[Dict[str, Any]] = Field(
        default=None, alias="invocationContext"
    )
    item_object_id: str = Field(alias="itemObjectId")
    workspace_object_id: str = Field(alias="workspaceObjectId")
    capacity_object_id: Optional[str] = Field(default=None, alias="capacityObjectId")
    execution_data: Optional[ExecutionData] = Field(
        default=None, alias="executionData"
    )

    model_config = {"populate_by_name": True}


# ── Outbound to Fabric ─────────────────────────────────────────────────────────

class ErrorDetails(BaseModel):
    error_code: str = Field(alias="errorCode")
    message: str
    message_parameters: Optional[Dict[str, str]] = Field(
        default=None, alias="messageParameters"
    )

    model_config = {"populate_by_name": True}


class JobStatusResponse(BaseModel):
    """
    Returned by GET /workload/jobs/instances/{jobInstanceId}
    and by POST /workload/jobs/instances/{jobInstanceId} on completion.
    """
    status: JobStatus
    failure_reason: Optional[ErrorDetails] = Field(
        default=None, alias="failureReason"
    )

    model_config = {"populate_by_name": True}


class StartJobResponse(BaseModel):
    """
    Returned immediately by POST /workload/jobs/instances/{jobInstanceId}.
    Fabric expects either an immediate terminal status (sync job)
    or InProgress (async job that will be polled).
    """
    status: JobStatus = JobStatus.IN_PROGRESS
    failure_reason: Optional[ErrorDetails] = Field(
        default=None, alias="failureReason"
    )

    model_config = {"populate_by_name": True}


# ── Internal job tracking record ───────────────────────────────────────────────

class JobRecord(BaseModel):
    """Internal state persisted by job_tracker — not exposed to Fabric directly."""
    job_instance_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    item_object_id: str
    workspace_object_id: str
    job_type: str
    status: JobStatus = JobStatus.NOT_STARTED
    started_at: Optional[str] = None      # ISO 8601
    finished_at: Optional[str] = None     # ISO 8601
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    records_ingested: int = 0
    entities_processed: int = 0
    entities_failed: int = 0

    def to_status_response(self) -> JobStatusResponse:
        failure = None
        if self.status == JobStatus.FAILED and self.error_code:
            failure = ErrorDetails(
                errorCode=self.error_code,
                message=self.error_message or "Job failed",
            )
        return JobStatusResponse(status=self.status, failureReason=failure)
