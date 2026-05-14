"""
backend/src/connectors/salesforce.py

Salesforce Change Data Capture (CDC) Connector Adapter.

Change detection: Salesforce Streaming API (CometD) — persistent async connection.
NOT a traditional HTTP webhook endpoint — the backend maintains a long-lived listener.
Salesforce CDC events include only changed fields — fetch_record() called for full row.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, AsyncIterator

import asyncio

import token_validator

from connectors.base import (
    ChangeEvent, ChangeType, ConnectorAuthError, ConnectorBase,
    EntityMetadata, ConnectorRegistry, RetryableError,
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
class SalesforceAdapter(ConnectorBase):
    """
    Salesforce connector using Change Data Capture (CDC).

    Source system ID: "salesforce"
    Auth: OAuth2 (Connected App — client credentials or JWT bearer)
    Change detection: Salesforce Streaming API (CometD / bayeux protocol)
                      Persistent async listener — NOT a webhook endpoint.
    Subscription channel: /data/{ObjectName}ChangeEvent

    Credentials expected in config.credentials:
        client_id: str          # Connected App consumer key
        client_secret: str      # Connected App consumer secret
        instance_url: str       # e.g. https://yourorg.my.salesforce.com
        # OR for JWT:
        private_key: str        # PEM private key
        username: str           # Salesforce user for JWT subject

    IMPORTANT: subscribe_changes() starts an async background task that
    maintains the CometD connection. It does NOT register an HTTP endpoint.
    The scheduler monitors this task and restarts it if it dies.
    """

    SOURCE_SYSTEM_ID = "salesforce"
    USES_POLLING = False

    async def authenticate(self) -> bool:
        # TODO: implement OAuth2 token request to Salesforce
        # POST https://login.salesforce.com/services/oauth2/token
        raise NotImplementedError

    async def discover_entities(self) -> list[EntityMetadata]:
        # TODO: list Salesforce objects with CDC enabled
        # GET /services/data/v59.0/sobjects/ then filter HasChangeDataCapture
        # Or GET /services/data/v59.0/event/eventDefinitions (CDC channels)
        raise NotImplementedError

    async def subscribe_changes(self, entities: list[str]) -> None:
        # TODO: for each entity, enable CDC in Salesforce setup if not already enabled
        # Then start the CometD streaming listener as an asyncio background task
        # Channel format: /data/{ObjectName}ChangeEvent
        # e.g. /data/AccountChangeEvent, /data/OpportunityChangeEvent
        raise NotImplementedError

    async def handle_incoming_event(self, raw_payload: dict) -> list[ChangeEvent]:
        # Called from the CometD listener loop (not from an HTTP endpoint)
        # raw_payload is a Salesforce CDC event:
        #   payload.ChangeEventHeader.changeType: CREATE/UPDATE/DELETE/UNDELETE
        #   payload.ChangeEventHeader.recordIds: [list of affected record IDs]
        #   payload.ChangeEventHeader.changedFields: [list of changed field names]
        #   payload.<field>: changed field values (NOT full row)
        # Must call fetch_record() to get full row on UPDATE events
        raise NotImplementedError

    async def fetch_record(self, entity_type: str, record_id: str) -> dict[str, Any]:
        # TODO: GET /services/data/v59.0/sobjects/{entity_type}/{record_id}
        raise NotImplementedError

    async def initial_load(self, entity_type: str) -> AsyncIterator[list[dict[str, Any]]]:
        # TODO: SOQL query with pagination
        # SELECT Id, ... FROM {entity_type} ORDER BY Id LIMIT 500 OFFSET {n}
        raise NotImplementedError
        yield []

    async def renew_subscriptions(self) -> None:
        # CometD connections don't "expire" like BC webhooks
        # But verify the background listener task is alive — restart if dead
        pass

    async def revoke_subscriptions(self) -> None:
        # Stop the CometD background listener task
        # Optionally disable CDC on the Salesforce objects (may affect other integrations)
        raise NotImplementedError
