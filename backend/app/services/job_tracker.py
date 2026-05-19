"""
Job state tracker.

Phase 1: in-memory dict (sufficient for single-instance deployments and dev).
Phase 2: swap backend to Azure Table Storage by flipping USE_TABLE_STORAGE=true.

The interface is the same in both cases so callers don't change.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Optional

from app.models.job_models import JobRecord, JobStatus

log = logging.getLogger(__name__)

_USE_TABLE_STORAGE = os.getenv("USE_TABLE_STORAGE", "false").lower() == "true"
_AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
_TABLE_NAME = os.getenv("JOB_TABLE_NAME", "ConnectorJobs")

# In-memory store (primary for Phase 1)
_store: Dict[str, JobRecord] = {}
_lock = asyncio.Lock()


# ── Public API ─────────────────────────────────────────────────────────────────

async def create(job_instance_id: str, record: JobRecord) -> None:
    if _USE_TABLE_STORAGE:
        await _table_upsert(job_instance_id, record)
    else:
        async with _lock:
            _store[job_instance_id] = record


async def get_or_create(
    job_instance_id: str, record: JobRecord
) -> tuple[JobRecord, bool]:
    """
    Atomically returns (existing_record, False) if the job already exists,
    or (new_record, True) if it was just created.
    Prevents TOCTOU races on concurrent POST requests for the same jobInstanceId.
    """
    if _USE_TABLE_STORAGE:
        existing = await _table_get(job_instance_id)
        if existing is not None:
            return existing, False
        await _table_upsert(job_instance_id, record)
        return record, True
    else:
        async with _lock:
            existing = _store.get(job_instance_id)
            if existing is not None:
                return existing, False
            _store[job_instance_id] = record
            return record, True


async def get(job_instance_id: str) -> Optional[JobRecord]:
    if _USE_TABLE_STORAGE:
        return await _table_get(job_instance_id)
    async with _lock:
        return _store.get(job_instance_id)


async def update_status(
    job_instance_id: str,
    status: JobStatus,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    records_ingested: int = 0,
    entities_processed: int = 0,
    entities_failed: int = 0,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    record = await get(job_instance_id)
    if record is None:
        log.warning("update_status: job %s not found", job_instance_id)
        return

    updated = record.model_copy(update={
        "status": status,
        "error_code": error_code,
        "error_message": error_message,
        "records_ingested": records_ingested,
        "entities_processed": entities_processed,
        "entities_failed": entities_failed,
        "finished_at": now if status in (
            JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED
        ) else record.finished_at,
    })

    if _USE_TABLE_STORAGE:
        await _table_upsert(job_instance_id, updated)
    else:
        async with _lock:
            _store[job_instance_id] = updated


async def mark_started(job_instance_id: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    record = await get(job_instance_id)
    if record is None:
        return
    updated = record.model_copy(update={
        "status": JobStatus.IN_PROGRESS,
        "started_at": now,
    })
    if _USE_TABLE_STORAGE:
        await _table_upsert(job_instance_id, updated)
    else:
        async with _lock:
            _store[job_instance_id] = updated


async def cancel(job_instance_id: str) -> bool:
    """Returns True if the job was in a cancellable state."""
    record = await get(job_instance_id)
    if record is None:
        return False
    if record.status not in (JobStatus.NOT_STARTED, JobStatus.IN_PROGRESS):
        return False
    await update_status(job_instance_id, JobStatus.CANCELLED)
    return True


# ── Azure Table Storage backend (Phase 2) ─────────────────────────────────────

async def _table_upsert(job_instance_id: str, record: JobRecord) -> None:
    try:
        from azure.data.tables.aio import TableServiceClient  # type: ignore

        async with TableServiceClient.from_connection_string(
            _AZURE_STORAGE_CONNECTION_STRING
        ) as svc:
            table = svc.get_table_client(_TABLE_NAME)
            entity = {
                "PartitionKey": "jobs",
                "RowKey": job_instance_id,
                **record.model_dump(),
            }
            await table.upsert_entity(entity)
    except Exception as exc:
        log.error("Table Storage upsert failed for %s: %s", job_instance_id, exc)


async def _table_get(job_instance_id: str) -> Optional[JobRecord]:
    try:
        from azure.data.tables.aio import TableServiceClient  # type: ignore

        async with TableServiceClient.from_connection_string(
            _AZURE_STORAGE_CONNECTION_STRING
        ) as svc:
            table = svc.get_table_client(_TABLE_NAME)
            entity = await table.get_entity("jobs", job_instance_id)
            data = dict(entity)
            data.pop("PartitionKey", None)
            data.pop("RowKey", None)
            data.pop("odata.etag", None)
            data.pop("Timestamp", None)
            return JobRecord(**data)
    except Exception:
        return None
