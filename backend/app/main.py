"""
FastAPI application entry point.

Hosting-agnostic: this module can be wrapped by:
  - uvicorn directly (Azure Container Apps / App Service / local dev)
  - Azure Functions custom handler (thin wrapper in function_app.py)
  - Any ASGI server

Environment variables:
  FABRIC_TENANT_ID     — ISV tenant ID for token validation
  BACKEND_APP_ID       — Entra ID app registration ID for this backend
  LOG_LEVEL            — DEBUG / INFO / WARNING (default: INFO)
  USE_TABLE_STORAGE    — true = persist job state in Azure Table Storage
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pythonjsonlogger import jsonlogger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.jobs import router as jobs_router
from app.rate_limiter import limiter

# ── Structured JSON logging ────────────────────────────────────────────────────

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

_handler = logging.StreamHandler()
_handler.setFormatter(
    jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        rename_fields={
            "asctime": "time",
            "levelname": "level",
            "name": "logger",
            "message": "msg",
        },
    )
)
logging.root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
logging.root.addHandler(_handler)

log = logging.getLogger(__name__)


# ── Startup checks ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    app_env = os.getenv("APP_ENV", "").lower()
    use_table_storage = os.getenv("USE_TABLE_STORAGE", "false").lower() == "true"

    if app_env == "production" and not use_table_storage:
        raise RuntimeError(
            "In-memory job storage is not allowed in production. "
            "Set USE_TABLE_STORAGE=true (and configure AZURE_STORAGE_ACCOUNT_NAME)."
        )

    if not use_table_storage:
        log.warning(
            "Job state is in-memory — will be lost on container restart. "
            "Set USE_TABLE_STORAGE=true for production deployments.",
            extra={"hint": "set USE_TABLE_STORAGE=true"},
        )

    fabric_tenant_id = os.getenv("FABRIC_TENANT_ID", "")
    backend_app_id = os.getenv("BACKEND_APP_ID", "")
    if not fabric_tenant_id or not backend_app_id:
        log.warning(
            "JWT validation is DISABLED — FABRIC_TENANT_ID and BACKEND_APP_ID are not set. "
            "All requests are accepted without token verification. "
            "This is acceptable for local development only.",
            extra={"security": "jwt_validation_disabled"},
        )

    yield


# ── Application ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Fabric Universal Connector — Backend",
    version="0.1.0",
    description=(
        "ISV backend for the Fabric Universal Connector workload. "
        "Implements the Fabric WDK IJobsController contract."
    ),
    docs_url="/docs" if os.getenv("ENABLE_SWAGGER", "false").lower() == "true" else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS origin list ──────────────────────────────────────────────────────────

_DEFAULT_CORS_ORIGINS = [
    # Fabric platform
    "https://api.fabric.microsoft.com",
    "https://app.fabric.microsoft.com",
    # ISV frontend deployments — one subdomain per scoped workload
    "https://connector.agic.technology",
    "https://cij.connector.agic.technology",
    "https://sales.connector.agic.technology",
    "https://bc.connector.agic.technology",
    "https://sql.connector.agic.technology",
]


def _build_cors_origins() -> list[str]:
    """Build the CORS allow-list from environment variables.

    If CORS_ORIGINS is set (comma-separated), it replaces the default list.
    CORS_EXTRA_ORIGINS (comma-separated) is always appended.
    Document both in backend/.env.example.
    """
    primary_env = os.getenv("CORS_ORIGINS", "")
    origins: list[str] = (
        [o.strip() for o in primary_env.split(",") if o.strip()]
        if primary_env
        else list(_DEFAULT_CORS_ORIGINS)
    )
    origins += [o.strip() for o in os.getenv("CORS_EXTRA_ORIGINS", "").split(",") if o.strip()]
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-Workload-Id"],
)

app.include_router(jobs_router)


# ── X-Workload-Id middleware ───────────────────────────────────────────────────

# Paths exempt from X-Workload-Id validation:
#   /health*   — monitoring probes (no workload context)
#   /workload* — Fabric Scheduler calls these directly (no custom header allowed)
#   /docs / /openapi.json — Swagger UI (only enabled in dev via ENABLE_SWAGGER)
_WORKLOAD_HEADER_EXEMPT_PREFIXES = (
    "/health",
    "/workload",
    "/docs",
    "/openapi.json",
    "/redoc",
)


@app.middleware("http")
async def validate_workload_id_header(request: Request, call_next):
    """
    Enforce presence of the X-Workload-Id header on all non-exempt endpoints.

    WDK endpoints (/workload/*) are exempt because the Fabric Scheduler calls
    them directly and cannot inject custom headers.  All other endpoints
    (e.g. /v1/workloads/config) require the header so the backend knows which
    workload is making the request.

    Missing header behaviour:
      - Exempt paths: pass through silently.
      - Non-exempt paths: return HTTP 400 + log WARNING.
    """
    path = request.url.path
    if any(path == prefix or path.startswith(prefix + "/") or path.startswith(prefix + "?")
           for prefix in _WORKLOAD_HEADER_EXEMPT_PREFIXES):
        return await call_next(request)

    workload_id = request.headers.get("X-Workload-Id")
    if not workload_id:
        log.warning(
            "Missing X-Workload-Id header",
            extra={"path": path, "method": request.method},
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": "Missing required header: X-Workload-Id"},
        )

    return await call_next(request)


# ── Health endpoints ───────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Lightweight health probe for load balancers and container orchestrators."""
    return {"status": "ok", "version": app.version}


@app.get("/health/detailed", tags=["system"])
async def health_detailed(request: Request) -> dict:
    """
    Detailed health report including job statistics and configuration status.

    Protected by X-Health-Token header. If HEALTH_TOKEN env var is not set,
    the endpoint always returns 403 (fail-safe: no accidental exposure).

    Returns:
      - status: "ok" or "degraded"
      - version: backend app version
      - job_tracker_backend: "in_memory" | "azure_table_storage"
      - jobs_last_24h: per-status job counts for the last 24 hours
      - onelake_configured: whether the OneLake account URL env var is set
      - registered_workloads: list of known workload IDs
    """
    health_token = os.getenv("HEALTH_TOKEN", "")
    if not health_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    provided_token = request.headers.get("X-Health-Token", "")
    if not provided_token or provided_token != health_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    from app.services import job_tracker as _tracker
    from app.api.workloads import WorkloadId

    # Job counts (never raises — falls back to zeros on error)
    try:
        job_counts = await _tracker.count_by_status(hours=24)
    except Exception as exc:
        log.error("health/detailed: count_by_status failed: %s", exc)
        from app.models.job_models import JobStatus
        job_counts = {s.value: 0 for s in JobStatus}

    # OneLake connectivity — check environment configuration only (no network call)
    onelake_account_url = os.getenv("ONELAKE_ACCOUNT_URL", "")
    onelake_configured = bool(onelake_account_url)

    # Workload config versions
    registered_workloads = [
        w.value for w in WorkloadId if w != WorkloadId.UNIVERSAL
    ]

    # Job tracker backend
    use_table_storage = os.getenv("USE_TABLE_STORAGE", "false").lower() == "true"

    return {
        "status": "ok",
        "version": app.version,
        "job_tracker_backend": (
            "azure_table_storage" if use_table_storage else "in_memory"
        ),
        "jobs_last_24h": job_counts,
        "onelake_configured": onelake_configured,
        "registered_workloads": registered_workloads,
    }


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# Request logging middleware runs outermost (last @app.middleware in file = first to execute).
# It logs every request after the workload_id check so the workload_id header is available.
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with correlation ID, method, path, status, and duration."""
    import time as _time
    import uuid as _uuid

    request_id = request.headers.get("X-Request-Id") or str(_uuid.uuid4())
    workload_id = request.headers.get("X-Workload-Id", "")
    start = _time.monotonic()

    response = await call_next(request)

    duration_ms = round((_time.monotonic() - start) * 1000, 1)
    log.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "workload_id": workload_id,
        },
    )

    response.headers["X-Request-Id"] = request_id
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=LOG_LEVEL.lower(),
    )
