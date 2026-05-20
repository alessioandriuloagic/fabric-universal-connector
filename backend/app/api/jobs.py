"""
Fabric Workload Development Kit — IJobsController implementation.

Endpoints required by the WDK spec:
  POST   /workload/jobs/instances/{jobInstanceId}         ← Fabric starts a job
  GET    /workload/jobs/instances/{jobInstanceId}          ← Fabric polls status
  DELETE /workload/jobs/instances/{jobInstanceId}          ← Fabric cancels (hard)
  POST   /workload/jobs/instances/{jobInstanceId}/cancel   ← Fabric requests cancel

The job is executed asynchronously (background task).
Fabric polls GET until status is terminal.

Ref: https://learn.microsoft.com/en-us/fabric/workload-development-kit/extensibility-back-end
"""
import asyncio
import json
import logging
import os
from functools import lru_cache
from typing import Annotated

import jwt as _jwt
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from app.rate_limiter import limiter
from app.api.workloads import WorkloadId, get_workload_id

from app.models.job_models import (
    JobRecord,
    JobRunContext,
    JobStatus,
    JobStatusResponse,
    StartJobResponse,
    ErrorDetails,
)
from app.services import job_tracker
from app.exceptions import ConnectorFatalError, ConfigLoadError, ConfigValidationError

log = logging.getLogger(__name__)
router = APIRouter(prefix="/workload/jobs/instances", tags=["jobs"])

# ── JWT validation ─────────────────────────────────────────────────────────────

_FABRIC_TENANT_ID = os.getenv("FABRIC_TENANT_ID", "")
_BACKEND_APP_ID = os.getenv("BACKEND_APP_ID", "")
_SKIP_VALIDATION = not _FABRIC_TENANT_ID or not _BACKEND_APP_ID

if _SKIP_VALIDATION:
    log.warning(
        "⚠️  JWT validation DISABLED — set FABRIC_TENANT_ID and BACKEND_APP_ID to enable"
    )


@lru_cache(maxsize=1)
def _jwks_client() -> "_jwt.PyJWKClient":
    url = (
        f"https://login.microsoftonline.com/{_FABRIC_TENANT_ID}"
        "/discovery/v2.0/keys"
    )
    return _jwt.PyJWKClient(url, cache_keys=True)


# ── Token extraction + validation ─────────────────────────────────────────────

def _extract_bearer(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization[len("Bearer "):]

    if _SKIP_VALIDATION:
        return token

    try:
        client = _jwks_client()
        signing_key = client.get_signing_key_from_jwt(token)
        _jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=_BACKEND_APP_ID,
            issuer=f"https://sts.windows.net/{_FABRIC_TENANT_ID}/",
        )
    except _jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except _jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        )

    return token


BearerToken = Annotated[str, Depends(_extract_bearer)]


# ── WDK endpoints ──────────────────────────────────────────────────────────────

@router.post("/{job_instance_id}", response_model=StartJobResponse)
@limiter.limit("60/minute")
async def start_job(
    request: Request,
    job_instance_id: str,
    context: JobRunContext,
    background_tasks: BackgroundTasks,
    token: BearerToken,
    workload_id: WorkloadId = Depends(get_workload_id),
) -> StartJobResponse:
    """
    Fabric calls this endpoint to start a job instance.
    We acknowledge immediately (IN_PROGRESS) and run the job in the background.
    """
    new_record = JobRecord(
        job_instance_id=job_instance_id,
        item_object_id=context.item_object_id,
        workspace_object_id=context.workspace_object_id,
        job_type=context.job_type,
        status=JobStatus.IN_PROGRESS,
    )
    existing_or_new, created = await job_tracker.get_or_create(job_instance_id, new_record)

    if not created:
        if existing_or_new.status in (JobStatus.IN_PROGRESS, JobStatus.NOT_STARTED):
            return StartJobResponse(status=JobStatus.IN_PROGRESS)
        return StartJobResponse(status=existing_or_new.status)

    background_tasks.add_task(_execute_job, job_instance_id, context, token, workload_id)
    log.info("Job %s accepted (item=%s, workload=%s)", job_instance_id, context.item_object_id, workload_id.value)
    return StartJobResponse(status=JobStatus.IN_PROGRESS)


@router.get("/{job_instance_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_instance_id: str,
    token: BearerToken,
) -> JobStatusResponse:
    """Fabric polls this endpoint to determine if the job has completed."""
    record = await job_tracker.get(job_instance_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job instance {job_instance_id} not found",
        )
    return record.to_status_response()


@router.delete("/{job_instance_id}", status_code=status.HTTP_200_OK)
async def delete_job(
    job_instance_id: str,
    token: BearerToken,
) -> dict:
    """Hard cancel — Fabric calls this when the user force-stops a job."""
    cancelled = await job_tracker.cancel(job_instance_id)
    log.info("Job %s delete requested, cancelled=%s", job_instance_id, cancelled)
    return {"jobInstanceId": job_instance_id, "cancelled": cancelled}


@router.post("/{job_instance_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_job(
    job_instance_id: str,
    token: BearerToken,
) -> dict:
    """Graceful cancel request from Fabric."""
    cancelled = await job_tracker.cancel(job_instance_id)
    log.info("Job %s cancel requested, cancelled=%s", job_instance_id, cancelled)
    return {"jobInstanceId": job_instance_id, "cancelled": cancelled}


# ── Background job execution ───────────────────────────────────────────────────

async def _execute_job(
    job_instance_id: str,
    context: JobRunContext,
    fabric_token: str,
    workload_id: WorkloadId = WorkloadId.UNIVERSAL,
) -> None:
    """
    Runs the actual ingestion pipeline for a job instance.
    Errors are caught and reflected in job status — never propagated upward.
    """
    await job_tracker.mark_started(job_instance_id)
    log.info("Background job starting: %s", job_instance_id)

    try:
        from app.services.fabric_client import load_item_definition
        from app.models.connector_item_definition import (
            CrmConnectorItemDefinition,
            BusinessCentralConnectorItemDefinition,
            SqlConnectorItemDefinition,
            ConnectorState,
        )
        from app.services.auth_service import resolve_credentials

        raw_def = await load_item_definition(
            workspace_id=context.workspace_object_id,
            item_id=context.item_object_id,
            bearer_token=fabric_token,
        )

        module_type = raw_def.get("moduleType")
        state = raw_def.get("state")

        if state != ConnectorState.CONFIGURED.value:
            raise ConfigValidationError(
                f"Connector state is '{state}', expected 'configured'"
            )

        if module_type == "crm":
            config = CrmConnectorItemDefinition.model_validate(raw_def)
            creds = await resolve_credentials(config.authentication, fabric_token)

            from app.connectors.crm.crm_connector import CRMConnector
            connector = CRMConnector(
                config=config,
                workspace_id=context.workspace_object_id,
                lakehouse_id=_resolve_lakehouse_id(config),
                connector_id=context.item_object_id,
                bearer_token=fabric_token,
                credentials=creds,
            )

        elif module_type == "businesscentral":
            config = BusinessCentralConnectorItemDefinition.model_validate(raw_def)
            creds = await resolve_credentials(config.authentication, fabric_token)

            from app.connectors.businesscentral.bc_connector import BusinessCentralConnector
            connector = BusinessCentralConnector(
                config=config,
                workspace_id=context.workspace_object_id,
                lakehouse_id=_resolve_lakehouse_id(config),
                connector_id=context.item_object_id,
                bearer_token=fabric_token,
                credentials=creds,
            )

        elif module_type == "sql":
            config = SqlConnectorItemDefinition.model_validate(raw_def)
            creds = await resolve_credentials(config.authentication, fabric_token)

            from app.connectors.sql.sql_connector import SQLConnector
            connector = SQLConnector(
                config=config,
                workspace_id=context.workspace_object_id,
                lakehouse_id=_resolve_lakehouse_id(config),
                connector_id=context.item_object_id,
                bearer_token=fabric_token,
                credentials=creds,
            )

        else:
            raise ConfigValidationError(f"Unknown moduleType: {module_type}")

        result = await connector.run()

        if result.status == "success":
            final_status = JobStatus.COMPLETED
        elif result.status == "failed":
            final_status = JobStatus.FAILED
        else:
            # partial_success: some entities failed — report COMPLETED to Fabric
            # (WDK has no PARTIAL status) but log the failures for observability.
            final_status = JobStatus.COMPLETED
            log.warning(
                "Job %s partial success: %d/%d entities failed",
                job_instance_id,
                result.total_entities_failed,
                len(result.entity_results),
            )

        await job_tracker.update_status(
            job_instance_id,
            status=final_status,
            records_ingested=result.total_records_ingested,
            entities_processed=len(result.entity_results),
            entities_failed=result.total_entities_failed,
        )
        log.info(
            "Job %s completed: status=%s records=%d entities_failed=%d",
            job_instance_id, result.status, result.total_records_ingested,
            result.total_entities_failed,
        )

    except (ConfigLoadError, ConfigValidationError, ConnectorFatalError) as exc:
        error_code = getattr(exc, "error_code", "FATAL_ERROR")
        log.error("Job %s fatal error (%s): %s", job_instance_id, error_code, exc)
        await job_tracker.update_status(
            job_instance_id,
            status=JobStatus.FAILED,
            error_code=error_code,
            error_message=str(exc),
        )

    except Exception as exc:
        log.exception("Job %s unexpected error: %s", job_instance_id, exc)
        await job_tracker.update_status(
            job_instance_id,
            status=JobStatus.FAILED,
            error_code="UNEXPECTED_ERROR",
            error_message=str(exc),
        )


def _resolve_lakehouse_id(config) -> str:
    """Extracts the Bronze Lakehouse ID from the item definition runtime config."""
    runtime = getattr(config, "runtime", None)
    if runtime:
        lh_id = getattr(runtime, "bronze_lake_house_id", None)
        if lh_id:
            return lh_id
    storage = getattr(config, "storage", None)
    if storage:
        lh_id = getattr(storage, "bronze_lake_house_id", None)
        if lh_id:
            return lh_id
    raise ConfigValidationError(
        "bronzeLakeHouseId not set in item definition. "
        "Complete the wizard activation first."
    )
