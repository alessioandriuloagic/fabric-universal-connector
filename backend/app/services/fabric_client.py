"""
Fabric Items API client.
Reads the ConnectorItem definition (payload.json) using the job's Bearer token.

Fabric Items API ref:
  GET /v1/workspaces/{workspaceId}/items/{itemId}/definitions/files/payload.json
  Authorization: Bearer {fabric_subject_and_app_token}
"""
from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict

import httpx

from app.exceptions import ConfigLoadError

log = logging.getLogger(__name__)

FABRIC_API_BASE = "https://api.fabric.microsoft.com"


async def load_item_definition(
    workspace_id: str,
    item_id: str,
    bearer_token: str,
) -> Dict[str, Any]:
    """
    Fetches the item definition payload.json from Fabric Items API.

    Returns the decoded JSON dict (the ConnectorItemDefinition object).
    Raises ConfigLoadError on any failure.
    """
    url = (
        f"{FABRIC_API_BASE}/v1/workspaces/{workspace_id}"
        f"/items/{item_id}/definitions/files/payload.json"
    )
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=headers)

        if resp.status_code == 404:
            raise ConfigLoadError(
                f"Item {item_id} not found in workspace {workspace_id}"
            )
        if resp.status_code == 403:
            raise ConfigLoadError(
                f"Access denied reading item {item_id} — check token scopes"
            )
        if resp.status_code != 200:
            raise ConfigLoadError(
                f"Fabric API returned {resp.status_code} for item {item_id}: {resp.text[:200]}"
            )

        payload = resp.json()
        encoded_content: str = payload.get("value", "")
        if not encoded_content:
            raise ConfigLoadError(f"Empty payload.json for item {item_id}")

        raw_json = base64.b64decode(encoded_content).decode("utf-8")
        definition = json.loads(raw_json)

        log.info(
            "Loaded item definition",
            extra={
                "workspace_id": workspace_id,
                "item_id": item_id,
                "schema_version": definition.get("schemaVersion"),
                "state": definition.get("state"),
                "module_type": definition.get("moduleType"),
            },
        )
        return definition

    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise ConfigLoadError(
            f"Network error reading item definition for {item_id}: {exc}"
        ) from exc
    except (json.JSONDecodeError, base64.binascii.Error) as exc:
        raise ConfigLoadError(
            f"Malformed payload.json for item {item_id}: {exc}"
        ) from exc
