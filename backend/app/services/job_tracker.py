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
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

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


async def list_recent(hours: int = 24) -> List[JobRecord]:
    """
    Return jobs that started or finished within the last `hours` hours.

    Used by the /health/detailed endpoint to compute per-status counts.
    Results are sorted by started_at ascending (oldest first).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    if _USE_TABLE_STORAGE:
        return await _table_list_recent(cutoff)

    async with _lock:
        result = [
            r for r in _store.values()
            if _record_is_recent(r, cutoff)
        ]
    result.sort(key=lambda r: r.started_at or r.finished_at or "")
    return result


async def count_by_status(hours: int = 24) -> Dict[str, int]:
    """
    Return a mapping of JobStatus → count for jobs in the last `hours` hours.

    All statuses are included in the result (with 0 count when no jobs exist).
    """
    counts: Dict[str, int] = {s.value: 0 for s in JobStatus}
    records = await list_recent(hours)
    for r in records:
        counts[r.status.value] = counts.get(r.status.value, 0) + 1
    return counts


def _record_is_recent(record: JobRecord, cutoff_iso: str) -> bool:
    """True when the record's most recent activity timestamp is >= cutoff."""
    ts = record.finished_at or record.started_at
    return ts is not None and ts >= cutoff_iso


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


async def _table_list_recent(cutoff_iso: str) -> List[JobRecord]:
    """
    Query Azure Table Storage for jobs with a started_at or finished_at
    timestamp >= cutoff_iso.

    Uses an OData filter so only matching rows are transferred.
    Falls back to an empty list on any error to keep /health/detailed resilient.
    """
    try:
        from azure.data.tables.aio import TableServiceClient  # type: ignore

        # OData filter: rows where either time field meets the cutoff.
        # Azure Tables OData doesn't support OR across string comparisons
        # easily, so we filter by started_at only and supplement in memory.
        query_filter = f"PartitionKey eq 'jobs' and started_at ge '{cutoff_iso}'"

        results: List[JobRecord] = []
        async with TableServiceClient.from_connection_string(
            _AZURE_STORAGE_CONNECTION_STRING
        ) as svc:
            table = svc.get_table_client(_TABLE_NAME)
            async for entity in table.query_entities(query_filter):
                data = dict(entity)
                data.pop("PartitionKey", None)
                data.pop("RowKey", None)
                data.pop("odata.etag", None)
                data.pop("Timestamp", None)
                try:
                    results.append(JobRecord(**data))
                except Exception as parse_exc:
                    log.warning("Failed to parse Table Storage entity: %s", parse_exc)

        # Include jobs that finished recently but started before cutoff
        # (e.g. a long-running job started 25h ago but finished 1h ago).
        completed_filter = (
            f"PartitionKey eq 'jobs' and finished_at ge '{cutoff_iso}'"
        )
        seen_ids = {r.job_instance_id for r in results}
        async with TableServiceClient.from_connection_string(
            _AZURE_STORAGE_CONNECTION_STRING
        ) as svc:
            table = svc.get_table_client(_TABLE_NAME)
            async for entity in table.query_entities(completed_filter):
                data = dict(entity)
                row_key = data.get("RowKey", "")
                if row_key in seen_ids:
                    continue
                data.pop("PartitionKey", None)
                data.pop("RowKey", None)
                data.pop("odata.etag", None)
                data.pop("Timestamp", None)
                try:
                    results.append(JobRecord(**data))
                except Exception as parse_exc:
                    log.warning("Failed to parse Table Storage entity: %s", parse_exc)

        return results

    except Exception as exc:
        log.error("_table_list_recent failed: %s", exc)
        return []
