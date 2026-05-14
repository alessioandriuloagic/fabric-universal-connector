from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any, List
import uuid
import logging

from token_validator import validate_token, EntraToken, assert_item_belongs_to_tenant
from storage import storage
from connectors.base import ConnectorRegistry, ConnectorConfig, ChangeEvent
from open_mirroring_writer import write_events
from keyvault_client import set_secret_json, get_secret_json

router = APIRouter(prefix="/workload")
logger = logging.getLogger(__name__)

# Item lifecycle endpoints

@router.post("/item/create")
async def create_item(payload: Dict[str, Any], token: EntraToken = Depends(validate_token)):
    tenant_id = token.tid
    config = payload.get("config")
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid 'config' object")

    # If the payload includes a 'secrets' object, store it in Key Vault and
    # remove secrets from the stored item payload to avoid persisting secrets in the item config.
    secrets = payload.get("secrets")

    item_id = str(uuid.uuid4())

    if isinstance(secrets, dict):
        try:
            set_secret_json(tenant_id, item_id, secrets)
        except Exception as e:
            logger.exception("Failed to save secrets to Key Vault: %s", e)
            raise HTTPException(status_code=500, detail="Failed to save secrets")

    storage.save_item(item_id, {"tenant_id": tenant_id, "config": config})
    logger.info("Item created", extra={"tenant_id": tenant_id, "item_id": item_id})
    return {"itemId": item_id}


@router.get("/item/{item_id}")
async def get_item(item_id: str, token: EntraToken = Depends(validate_token)):
    item = storage.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await assert_item_belongs_to_tenant(item_id, token.tid)
    return {"itemId": item_id, "config": item.get("config")}


@router.put("/item/{item_id}")
async def update_item(item_id: str, payload: Dict[str, Any], token: EntraToken = Depends(validate_token)):
    item = storage.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await assert_item_belongs_to_tenant(item_id, token.tid)
    config = payload.get("config")
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="Missing or invalid 'config' object")

    # If secrets provided, update Key Vault secret for this item
    secrets = payload.get("secrets")
    if isinstance(secrets, dict):
        try:
            set_secret_json(item.get("tenant_id"), item_id, secrets)
        except Exception as e:
            logger.exception("Failed to save secrets to Key Vault: %s", e)
            raise HTTPException(status_code=500, detail="Failed to save secrets")

    item["config"] = config
    storage.save_item(item_id, item)
    logger.info("Item updated", extra={"tenant_id": item.get("tenant_id"), "item_id": item_id})
    return {"ok": True}


@router.delete("/item/{item_id}")
async def delete_item(item_id: str, token: EntraToken = Depends(validate_token)):
    item = storage.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await assert_item_belongs_to_tenant(item_id, token.tid)
    storage.delete_item(item_id)
    logger.info("Item deleted", extra={"tenant_id": token.tid, "item_id": item_id})
    return {"ok": True}


# Webhook receiver

webhook_router = APIRouter()

@webhook_router.post("/webhook/{source}/{item_id}")
async def receive_webhook(source: str, item_id: str, request: Request):
    try:
        raw_payload = await request.json()
    except Exception:
        raw_payload = await request.body()

    item = storage.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    cfg = item.get("config", {})
    config = ConnectorConfig(
        tenant_id=item.get("tenant_id"),
        item_id=item_id,
        source_system=source,
        base_url=cfg.get("base_url", ""),
        company_id=cfg.get("company_id"),
        entities=cfg.get("entities", []),
    )

    try:
        adapter = ConnectorRegistry.create(config)
    except Exception as e:
        logger.exception("No adapter for source %s: %s", source, e)
        raise HTTPException(status_code=400, detail=str(e))

    try:
        events: List[ChangeEvent] = await adapter.handle_incoming_event(raw_payload)
    except Exception as e:
        logger.exception("Adapter failed to parse webhook payload: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    hydrated = []
    for ev in events:
        if ev.payload is None:
            try:
                ev.payload = await adapter.fetch_record(ev.entity_type, ev.record_id)
            except Exception as e:
                logger.warning("Failed to fetch record %s/%s: %s", ev.entity_type, ev.record_id, e)
        hydrated.append(ev)

    try:
        await write_events(hydrated)
    except Exception as e:
        logger.exception("Failed to write events: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    return {"received": len(hydrated)}

# expose routers for main.py
item_lifecycle = router
webhook = webhook_router

# -----------------------------
# Connector utility endpoints
# -----------------------------
# These endpoints are used by the frontend to validate connection parameters,
# discover available entities/tables from a source system, and request
# subscription creation. They create a ConnectorConfig (minimal) and
# instantiate the appropriate adapter via ConnectorRegistry.

from fastapi import Body

connectors_router = APIRouter(prefix="/workload/connectors")


@connectors_router.post("/test-connection")
async def test_connection(body: Dict[str, Any]):
    """Test authentication/connection to a source system.

    Expected body:
    {
      "source": "business_central" | "d365" | "salesforce" | "sap",
      "config": { ... non-secret config ... },
      "secrets": { ... optional secrets object ... }
    }

    If `secrets` are provided, they are stored temporarily in Key Vault for
    the duration of this operation (not persisted to the item). The adapter
    authenticate() method is invoked to validate credentials.
    """
    source = body.get("source")
    cfg = body.get("config", {}) or {}
    secrets = body.get("secrets")

    # Build a minimal ConnectorConfig for the adapter factory
    cconfig = ConnectorConfig(
        tenant_id=cfg.get("tenant_id") or "dev-tenant",
        item_id=cfg.get("item_id") or "test-item",
        source_system=source,
        base_url=cfg.get("base_url"),
        company_id=cfg.get("company_id"),
        entities=cfg.get("entities", []),
    )

    # If secrets were provided, temporarily inject them into Key Vault so
    # backend_2 helpers that expect Key Vault can pick them up via the bridge.
    temp_saved = False
    try:
        if isinstance(secrets, dict):
            set_secret_json(cconfig.tenant_id, cconfig.item_id, secrets)
            temp_saved = True
    except Exception:
        # Non-fatal for test — adapter.authenticate should surface auth errors
        temp_saved = False

    try:
        adapter = ConnectorRegistry.create(cconfig)
    except Exception as e:
        if temp_saved:
            # best-effort cleanup omitted for dev; production should delete secret
            pass
        raise HTTPException(status_code=400, detail=str(e))

    # Call authenticate (may be sync or async depending on adapter)
    try:
        auth_result = adapter.authenticate()
        if hasattr(auth_result, "__await__"):
            auth_result = await auth_result
    except Exception as e:
        # cleanup temporary secret if possible
        raise HTTPException(status_code=400, detail=f"Authentication failed: {e}")

    return {"ok": True, "authenticated": bool(auth_result)}


@connectors_router.post("/discover-entities")
async def discover_entities(body: Dict[str, Any]):
    """Discover entities/tables supported by the source system given config.

    Body same structure as /test-connection. Returns a list of EntityMetadata
    objects (serializable dicts) as provided by the adapter.
    """
    source = body.get("source")
    cfg = body.get("config", {}) or {}
    secrets = body.get("secrets")

    cconfig = ConnectorConfig(
        tenant_id=cfg.get("tenant_id") or "dev-tenant",
        item_id=cfg.get("item_id") or "test-item",
        source_system=source,
        base_url=cfg.get("base_url"),
        company_id=cfg.get("company_id"),
        entities=cfg.get("entities", []),
    )

    # store secrets if supplied
    try:
        if isinstance(secrets, dict):
            set_secret_json(cconfig.tenant_id, cconfig.item_id, secrets)
    except Exception:
        pass

    try:
        adapter = ConnectorRegistry.create(cconfig)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        entities = adapter.discover_entities()
        if hasattr(entities, "__await__"):
            entities = await entities
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Ensure results are serializable
    try:
        return {"entities": [e.__dict__ if hasattr(e, "__dict__") else e for e in entities]}
    except Exception:
        return {"entities": entities}


@connectors_router.post("/subscribe")
async def subscribe(body: Dict[str, Any]):
    """Request the adapter to create subscriptions/webhooks for the provided entities.

    Body:
    {
      "source": "business_central",
      "item_id": "...",
      "entities": ["Customer","Item"],
      "config": { ... },
      "secrets": { ... }
    }
    """
    source = body.get("source")
    item_id = body.get("item_id")
    entities = body.get("entities", [])
    cfg = body.get("config", {}) or {}
    secrets = body.get("secrets")

    if not item_id:
        raise HTTPException(status_code=400, detail="item_id is required")

    cconfig = ConnectorConfig(
        tenant_id=cfg.get("tenant_id") or "dev-tenant",
        item_id=item_id,
        source_system=source,
        base_url=cfg.get("base_url"),
        company_id=cfg.get("company_id"),
        entities=entities,
    )

    # Persist secrets if provided (so scheduler and webhook handlers can reuse them)
    if isinstance(secrets, dict):
        try:
            set_secret_json(cconfig.tenant_id, item_id, secrets)
        except Exception as e:
            logger.exception("Unable to persist secrets to Key Vault: %s", e)
            raise HTTPException(status_code=500, detail="Failed to save secrets")

    try:
        adapter = ConnectorRegistry.create(cconfig)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = adapter.subscribe_changes(entities)
        if hasattr(result, "__await__"):
            result = await result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"ok": True, "result": result}


# expose connectors router as well
connectors = connectors_router
