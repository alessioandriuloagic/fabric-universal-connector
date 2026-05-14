---
applyTo: "backend/**"
---

# Backend Instructions — Python FastAPI

## Stack
- Python 3.11+, FastAPI, Uvicorn, Pydantic v2, httpx, MSAL, APScheduler, pyarrow (for Parquet writing)

## Async Rules
Always use `async`/`await`. Never use `time.sleep()` — use `asyncio.sleep()`.
Never use `requests` library — use `httpx.AsyncClient` with context manager.

## Pydantic v2 Syntax
Use `model_dump()` not `dict()`. Use `model_validate()` not `parse_obj()`.
Use `model_dump_json()` for serialization to Key Vault. Field aliases with `Field(alias=...)`.

## FastAPI Patterns
Use `Depends()` for auth injection. Raise `HTTPException` — never return error dicts.
Use `APIRouter` with prefix per module — never put all routes in `main.py`.

## Token Validation
Every protected route gets `token: EntraToken = Depends(validate_token)`.
After validation always call `await assert_item_belongs_to_tenant(item_id, token.tid)`.
The `validate_token` dependency is in `auth/token_validator.py` — do not reimplement it inline.

## Logging
```python
import logging
logger = logging.getLogger(__name__)
logger.info("Event received", extra={"tenant_id": tid, "item_id": iid, "entity": entity})
```
Always pass `tenant_id` and `item_id` in `extra`. Never use `print()`.

## Open Mirroring Writer
Only call `writer.write_events(events: list[ChangeEvent])`.
Never construct Parquet files manually outside `open_mirroring/writer.py`.
`__rowMarker__` must always be the last column. Use `pyarrow` not `pandas` for Parquet construction.

## Error Handling in Connectors
Wrap external API calls in try/except. On transient errors (429, 5xx) raise `RetryableError`.
On auth errors (401, 403) raise `ConnectorAuthError` — these surface to the UI as actionable messages.
```python
try:
    response = await client.get(url)
    response.raise_for_status()
except httpx.HTTPStatusError as e:
    if e.response.status_code in (401, 403):
        raise ConnectorAuthError("BC credentials invalid or expired")
    raise RetryableError(f"BC API error: {e.response.status_code}")
```
