# Adding a New Connector

Step-by-step guide for adding a new source system to the Fabric Universal Connector.

---

## Before You Start

Check that the source system has at least one of:
- An HTTP webhook / push notification mechanism (preferred)
- An API with incremental change tracking (timestamp, sequence number, or CDC)

If it has neither, contact the team — pull-only systems with no change tracking
require a different strategy (full reload on schedule) and need a product decision.

---

## Step 1 — Create the adapter file

```bash
touch backend/src/connectors/{system_name}.py
```

Use `snake_case` for the filename. Examples: `hubspot.py`, `oracle_erp.py`, `pipedrive.py`.

---

## Step 2 — Implement ConnectorBase

```python
from connectors.base import ConnectorBase, ConnectorRegistry, ChangeEvent, ...

@ConnectorRegistry.register
class HubSpotAdapter(ConnectorBase):
    SOURCE_SYSTEM_ID = "hubspot"      # lowercase, no spaces, permanent — never change
    USES_POLLING = False              # True if source has no push capability

    async def authenticate(self) -> bool: ...
    async def discover_entities(self) -> list[EntityMetadata]: ...
    async def subscribe_changes(self, entities: list[str]) -> None: ...
    async def handle_incoming_event(self, raw_payload: dict) -> list[ChangeEvent]: ...
    async def fetch_record(self, entity_type: str, record_id: str) -> dict: ...
    async def initial_load(self, entity_type: str) -> AsyncIterator[list[dict]]: ...
    async def renew_subscriptions(self) -> None: ...
    async def revoke_subscriptions(self) -> None: ...
```

All 8 methods are mandatory. See `base.py` docstrings for the contract of each.

---

## Step 3 — Register the adapter

In `backend/src/connectors/base.py`, add your import to `_register_all_adapters()`:

```python
def _register_all_adapters() -> None:
    from connectors.business_central import BCAdapter    # noqa: F401
    from connectors.dynamics365 import D365Adapter       # noqa: F401
    from connectors.salesforce import SalesforceAdapter  # noqa: F401
    from connectors.sap import SAPAdapter                # noqa: F401
    from connectors.hubspot import HubSpotAdapter        # noqa: F401  ← ADD THIS
```

---

## Step 4 — Add credential fields to ConnectorConfig

In `backend/src/models/connector_config.py`, document what credentials your adapter expects.
These fields are NOT stored in ConnectorConfig directly — they are read from Key Vault at runtime.
But document them so the UI wizard knows what fields to show.

```python
# In connector_config.py, add to the CREDENTIAL_SCHEMAS dict:
CREDENTIAL_SCHEMAS = {
    "bc": {
        "client_id": {"type": "string", "label": "Client ID", "secret": False},
        "client_secret": {"type": "string", "label": "Client Secret", "secret": True},
        "tenant_id": {"type": "string", "label": "BC Tenant ID", "secret": False},
    },
    # ... existing systems ...
    "hubspot": {
        "api_key": {"type": "string", "label": "HubSpot Private App Token", "secret": True},
    },
}
```

The wizard UI reads `CREDENTIAL_SCHEMAS` to render the correct input fields for Step 1.
You do not need to touch any React code for standard string/password fields.

---

## Step 5 — Add a webhook endpoint (if push-based)

If your adapter is push-based, add a route in `backend/src/api/webhook.py`:

```python
@router.post("/webhook/hubspot/{item_id}")
async def hubspot_webhook(item_id: str, request: Request):
    raw_payload = await request.json()
    # Resolve customer config
    config = await load_config(item_id)
    adapter = ConnectorRegistry.create(config)
    events = await adapter.handle_incoming_event(raw_payload)
    await event_router.process(events)
    return {"status": "ok"}
```

---

## Step 6 — Write tests

```bash
touch backend/tests/connectors/test_hubspot.py
```

Minimum required tests:

```python
import pytest
from unittest.mock import AsyncMock, patch
from connectors.hubspot import HubSpotAdapter

@pytest.mark.asyncio
async def test_authenticate_success():
    adapter = HubSpotAdapter(make_test_config("hubspot"))
    with patch("httpx.AsyncClient.get", return_value=mock_response(200)):
        assert await adapter.authenticate() is True

@pytest.mark.asyncio
async def test_authenticate_invalid_credentials():
    adapter = HubSpotAdapter(make_test_config("hubspot"))
    with patch("httpx.AsyncClient.get", return_value=mock_response(401)):
        with pytest.raises(ConnectorAuthError):
            await adapter.authenticate()

@pytest.mark.asyncio
async def test_handle_incoming_event_returns_change_events():
    ...

@pytest.mark.asyncio
async def test_initial_load_paginates():
    ...

@pytest.mark.asyncio
async def test_renew_subscriptions_is_idempotent():
    ...
```

PR will not be merged without tests covering these scenarios.

---

## Step 7 — Document subscription behavior

Add a docstring to your class that answers:
- Does the source use push or pull?
- How long do subscriptions last before expiry?
- What happens if a webhook delivery fails (does the source retry)?
- Are deletes trackable? If not, how is this communicated to the user?

---

## Checklist

- [ ] `{system}.py` created in `backend/src/connectors/`
- [ ] `ConnectorBase` subclassed with `@ConnectorRegistry.register`
- [ ] `SOURCE_SYSTEM_ID` set (lowercase, unique, permanent)
- [ ] All 8 abstract methods implemented (no bare `raise NotImplementedError` in production)
- [ ] Adapter imported in `_register_all_adapters()` in `base.py`
- [ ] Credential schema added to `CREDENTIAL_SCHEMAS` in `connector_config.py`
- [ ] Webhook route added to `api/webhook.py` (if push-based)
- [ ] Tests written covering auth success, auth failure, event parsing, pagination
- [ ] Class docstring documents subscription expiry and delete behavior
- [ ] PR description links to source system API documentation
