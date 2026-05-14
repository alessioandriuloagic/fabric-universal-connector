---
applyTo: "backend/src/connectors/**"
---

# Connector Adapter Instructions

## The Rule: Implement ConnectorBase, Nothing Else
Every file in this folder is a connector adapter. It MUST subclass `ConnectorBase` from `base.py`.
It MUST implement all abstract methods. It MUST NOT import from other connector adapters.
It MUST NOT contain any Open Mirroring or Parquet writing logic.
It MUST NOT contain any Fabric API calls.
Its only job: talk to the external system and return `list[ChangeEvent]`.

## Method Contracts

### `discover_entities() -> list[EntityMetadata]`
Call the source system's metadata/discovery endpoint to enumerate available entities.
Never hardcode entity lists. The UI calls this to populate the table selection step.
Return only entities that are both readable AND change-trackable (webhook or CDC capable).

### `subscribe_changes(entities: list[str]) -> None`
Register change notifications for the given entity list on the source system.
Store subscription IDs persistently so `renew_subscriptions()` can find them.
If the source does not support push (e.g. SAP B1), register a poll job instead —
set `self.uses_polling = True` so the scheduler knows.

### `handle_incoming_event(raw_payload: dict) -> list[ChangeEvent]`
Called by the webhook HTTP handler when a notification arrives.
Parse the source-specific payload and return normalized `ChangeEvent` objects.
If the source does not include full record data (e.g. BC), set `payload=None`
and the framework will call `fetch_record()` automatically.

### `fetch_record(entity: str, record_id: str) -> dict`
Fetch a single record by ID from the source system.
Called automatically when `ChangeEvent.payload is None`.
Return the full row as a flat dict matching the entity schema.

### `initial_load(entity: str) -> AsyncIterator[list[dict]]`
Yield batches of records for the initial full sync.
Use pagination — never load the entire entity into memory.
Recommended batch size: 500–1000 records per yield.

### `renew_subscriptions() -> None`
Renew all active webhook subscriptions for this customer.
Called every 2 days by the scheduler. Must be idempotent.
Log each renewal with `tenant_id`, `item_id`, `entity`, `new_expiry`.

## Adding a New Connector — Checklist
- [ ] Create `{system_name}.py` in this folder
- [ ] Subclass `ConnectorBase`
- [ ] Implement all 7 abstract methods
- [ ] Add `"system_name"` to the `ConnectorRegistry` in `base.py`
- [ ] Add auth parameter schema to `ConnectorConfig` in `models/connector_config.py`
- [ ] Add wizard Step 1 UI card to `frontend/src/components/SourceConfig/`
- [ ] Write tests in `backend/tests/connectors/test_{system_name}.py`
- [ ] Document subscription expiry behavior in a docstring on `renew_subscriptions()`
- [ ] Document whether the adapter is push-based or poll-based in the class docstring
