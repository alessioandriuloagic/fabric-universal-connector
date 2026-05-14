"""
backend/src/connectors/dynamics365.py

Dynamics 365 / Dataverse Connector Adapter.

Change detection: Dataverse Webhooks (push), full payload included.
D365 includes PostEntityImages in webhook payload — fetch_record() is NOT called.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, AsyncIterator

import asyncio

import token_validator

from connectors.base import (
    ChangeEvent, ChangeType, ConnectorAuthError, ConnectorBase,
    ConnectorConfig, EntityMetadata, ConnectorRegistry, RetryableError,
)


async def acquire_app_token_for_scopes(scopes: list[str]) -> str:
    """Acquire an application token for the given scopes using MSAL helpers.

    Runs the blocking MSAL call in a thread to avoid blocking the event loop.
    Returns the raw access token string.
    """
    result = await asyncio.to_thread(token_validator.acquire_app_token, scopes)
    return result.get('access_token')


async def acquire_obo_token_for_scopes(user_assertion: str, scopes: list[str]) -> str:
    """Acquire a delegated token (OBO) for the given scopes using MSAL OBO helper.

    Runs the blocking MSAL call in a thread to avoid blocking the event loop.
    Returns the raw access token string.
    """
    result = await token_validator.acquire_token_on_behalf_of_async(user_assertion, scopes)
    return result.get('access_token')


@ConnectorRegistry.register
class D365Adapter(ConnectorBase):
    """
    Microsoft Dynamics 365 / Dataverse connector.

    Source system ID: "d365"
    Auth: OAuth2 (Entra ID client credentials) — Dataverse scope
    Change detection: Dataverse webhooks with full PostEntityImages payload
    Subscription expiry: managed via Dataverse Plugin Registration

    Credentials expected in config.credentials:
        client_id: str
        client_secret: str
        tenant_id: str
    """

    SOURCE_SYSTEM_ID = "d365"
    USES_POLLING = False

    async def authenticate(self) -> bool:
        # TODO: implement — call GET {base_url}/api/data/v9.2/
        raise NotImplementedError

    async def discover_entities(self) -> list[EntityMetadata]:
        # TODO: enumerate Dataverse entities with change tracking enabled
        # GET {base_url}/api/data/v9.2/EntityDefinitions?$select=LogicalName,DisplayName
        # Filter: IsChangeTrackingEnabled eq true
        raise NotImplementedError

    async def subscribe_changes(self, entities: list[str]) -> None:
        # TODO: register Dataverse webhooks via Plugin Registration API
        # Dataverse webhook endpoint receives full Create/Update/Delete payloads
        raise NotImplementedError

    async def handle_incoming_event(self, raw_payload: dict) -> list[ChangeEvent]:
        # Dataverse sends full PostEntityImages — no fetch_record() needed
        # raw_payload contains: PrimaryEntityName, PrimaryEntityId,
        #                       MessageName (Create/Update/Delete), PostEntityImages
        raise NotImplementedError

    async def fetch_record(self, entity_type: str, record_id: str) -> dict[str, Any]:
        # Only called for reconciliation — D365 normally provides full payload
        raise NotImplementedError

    async def initial_load(self, entity_type: str) -> AsyncIterator[list[dict[str, Any]]]:
        # TODO: page through Dataverse entity using $top/$skiptoken
        raise NotImplementedError
        yield []  # make Python recognize this as a generator

    async def renew_subscriptions(self) -> None:
        # TODO: Dataverse webhook registrations don't expire like BC
        # But verify they're still active and re-register if deleted
        pass

    async def revoke_subscriptions(self) -> None:
        # TODO: delete webhook registrations from Dataverse
        raise NotImplementedError
