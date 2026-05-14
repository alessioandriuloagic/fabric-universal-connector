from fastapi import FastAPI
import logging
import os

# Register connectors and include routers
try:
    from connectors.base import _register_all_adapters
except Exception:
    _register_all_adapters = None

app = FastAPI(title="Fabric Universal Connector Backend")
logger = logging.getLogger(__name__)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Fabric Universal Connector backend")
    if _register_all_adapters:
        try:
            _register_all_adapters()
            logger.info("Connector adapters registered")
        except Exception:
            logger.exception("Failed registering connector adapters")
    # Start scheduler (renew subscriptions job)
    try:
        from scheduler import start_scheduler
        start_scheduler()
    except Exception:
        logger.exception('Failed to start scheduler')

# Include routers (import lazily to avoid import order issues)
try:
    from api import item_lifecycle  # noqa: E402
    from api import webhook        # noqa: E402
    from api import connectors     # noqa: E402
    app.include_router(item_lifecycle.router)
    app.include_router(webhook.router)
    app.include_router(connectors)
except Exception:
    logger.warning("API routers not available at startup")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
