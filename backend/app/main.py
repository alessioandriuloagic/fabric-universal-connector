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

from fastapi import FastAPI, Request, status
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
    if os.getenv("USE_TABLE_STORAGE", "false").lower() != "true":
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://api.fabric.microsoft.com"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(jobs_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Health probe endpoint for load balancers and container orchestrators."""
    return {"status": "ok", "version": app.version}


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=LOG_LEVEL.lower(),
    )
