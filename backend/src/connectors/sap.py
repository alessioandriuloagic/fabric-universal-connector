"""
backend/src/connectors/sap.py

SAP Connector Adapter.

Supports two SAP deployment types with different change detection capabilities:

1. SAP S/4HANA Cloud — SAP Event Mesh (Business Events)
   Change detection: Webhook (push) via SAP Event Mesh
   USES_POLLING = False

2. SAP Business One / SAP on-premise — no native push
   Change detection: Scheduled pull with watermark (DI API / Service Layer)
   USES_POLLING = True

The adapter detects which mode to use based on config.credentials["sap_type"].
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
class SAPAdapter(ConnectorBase):
    """
    SAP connector — supports S/4HANA Cloud (push) and SAP B1 / on-premise (poll).

    Source system ID: "sap"

    Credentials expected in config.credentials:
        sap_type: "s4hana_cloud" | "business_one" | "on_premise"

        For S/4HANA Cloud (Event Mesh):
            event_mesh_url: str
            event_mesh_client_id: str
            event_mesh_client_secret: str

        For SAP Business One / on-premise (Service Layer):
            service_layer_url: str      # e.g. https://server:50000/b1s/v1
            company_db: str
            username: str
            password: str

    IMPORTANT: For SAP B1, USES_POLLING is effectively True at runtime.
    The class sets self._uses_polling based on sap_type after authentication.
    """

    SOURCE_SYSTEM_ID = "sap"
    USES_POLLING = False  # overridden at runtime for B1/on-premise

    def __init__(self, config):
        super().__init__(config)
        sap_type = config.credentials.get("sap_type", "business_one")
        self._uses_polling = sap_type != "s4hana_cloud"
        if self._uses_polling:
            self.logger.info(
                "SAP adapter initialized in POLLING mode (no native push available)",
                extra={"tenant_id": config.tenant_id, "sap_type": sap_type},
            )

    async def authenticate(self) -> bool:
        # TODO: branch on sap_type
        # S/4HANA Cloud: authenticate against SAP Event Mesh OAuth2 endpoint
        # SAP B1: POST /b1s/v1/Login with company_db, username, password
        raise NotImplementedError

    async def discover_entities(self) -> list[EntityMetadata]:
        # S/4HANA Cloud: list available Business Event types from Event Mesh catalog
        # SAP B1: list Service Layer entity types (OData metadata)
        # Return supports_webhook=True only for S/4HANA Cloud
        raise NotImplementedError

    async def subscribe_changes(self, entities: list[str]) -> None:
        # S/4HANA Cloud: subscribe to SAP Event Mesh queues/topics for each entity
        #   POST to Event Mesh management API to create subscriptions
        #   Webhook delivery to: /webhook/sap/{item_id}
        # SAP B1 / on-premise: register poll job in scheduler with watermark per entity
        #   No actual subscription on SAP side
        raise NotImplementedError

    async def handle_incoming_event(self, raw_payload: dict) -> list[ChangeEvent]:
        # S/4HANA Cloud only — called from HTTP webhook endpoint
        # SAP B1 never calls this — uses poll_changes() instead
        # SAP Event Mesh payload format varies by Business Event type
        raise NotImplementedError

    async def fetch_record(self, entity_type: str, record_id: str) -> dict[str, Any]:
        # S/4HANA Cloud: GET via OData API
        # SAP B1: GET /b1s/v1/{entity_type}({record_id})
        raise NotImplementedError

    async def initial_load(self, entity_type: str) -> AsyncIterator[list[dict[str, Any]]]:
        # Both: OData pagination ($top/$skip or $skiptoken)
        raise NotImplementedError
        yield []

    async def renew_subscriptions(self) -> None:
        # S/4HANA Cloud: verify Event Mesh subscription is active
        # SAP B1: verify poll jobs are registered (no-op if scheduler is running)
        pass

    async def revoke_subscriptions(self) -> None:
        # S/4HANA Cloud: delete Event Mesh subscriptions
        # SAP B1: unregister poll jobs from scheduler
        raise NotImplementedError

    async def poll_changes(
        self, entity_type: str, since: datetime
    ) -> list[ChangeEvent]:
        """
        SAP B1 / on-premise fallback: pull records modified since timestamp.

        Primary sync mechanism for SAP B1 (no native push).
        Fallback reconciliation for S/4HANA Cloud.

        Use the SAP B1 Service Layer with a date filter on UpdateDate/UpdateTime.
        Note: SAP B1 does not natively track deletes via Service Layer —
        implement a shadow key table strategy if delete detection is required.
        """
        # TODO: implement SAP B1 Service Layer incremental pull
        # GET /b1s/v1/{entity_type}?$filter=UpdateDate ge datetime'{since}'
        return []
