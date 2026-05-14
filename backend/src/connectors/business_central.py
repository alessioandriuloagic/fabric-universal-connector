"""
backend/src/connectors/business_central.py

Business Central Connector Adapter.

Change detection: Webhook (push), 30s debounce by BC.
BC webhook notifications do NOT include record data — fetch_record() is always called.
Subscriptions expire after 3 days — renew_subscriptions() handles renewal.

POC INTEGRATION NOTES:
    Your existing POC code maps to these methods:
    - POC bc_connector.py → authenticate(), fetch_record(), initial_load()
    - POC open_mirroring_writer.py → REMOVE from here, it lives in open_mirroring/writer.py
    - POC scheduler / polling loop → subscribe_changes() + renew_subscriptions()
    - POC DevOps parameters → self.config (loaded from Fabric item payload + Key Vault)
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator

import httpx
import os
import asyncio
import token_validator

from connectors.base import (
    ChangeEvent,
    ChangeType,
    ConnectorAuthError,
    ConnectorBase,
    ConnectorConfig,
    ConnectorHealth,
    ConnectorNotFoundError,
    ConnectorRegistry,
    EntityMetadata,
    RetryableError,
)

logger = logging.getLogger(__name__)


@ConnectorRegistry.register
class BCAdapter(ConnectorBase):
    """
    Microsoft Dynamics 365 Business Central connector.

    Source system ID: "bc"
    Auth: OAuth2 (Entra ID client credentials) or Basic Auth (API key)
    API: BC API v2.0 (OData v4)
    Change detection: REST webhooks (push), 30s debounce
    Subscription expiry: 3 days — auto-renewed by scheduler

    Credentials expected in config.credentials:
        For OAuth2:
            client_id: str
            client_secret: str
            tenant_id: str          # BC tenant (may differ from Fabric tenant)
        For Basic Auth:
            username: str
            password: str           # Web service access key
    """

    SOURCE_SYSTEM_ID = "bc"
    USES_POLLING = False

    # BC API base path template
    _API_BASE = "{base_url}/api/v2.0/companies({company_id})"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None
        self._access_token: str | None = None
        self._token_expiry: datetime | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _api_url(self, path: str) -> str:
        """Build a full BC API URL."""
        base = self._API_BASE.format(
            base_url=self.config.base_url.rstrip("/"),
            company_id=self.config.company_id,
        )
        return f"{base}/{path.lstrip('/')}"

    async def _get_client(self) -> httpx.AsyncClient:
        """Return an authenticated httpx client, refreshing token if needed."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        # Token refresh logic — replace with your POC OAuth2 flow
        # ── POC INTEGRATION POINT ──────────────────────────────────────
        # If your POC has a _get_access_token() or similar function,
        # move that logic here. self.config.credentials contains:
        # {"client_id": ..., "client_secret": ..., "tenant_id": ...}
        # ────────────────────────────────────────────────────────────────
        if self._needs_token_refresh():
            await self._refresh_token()
        return self._client

    def _needs_token_refresh(self) -> bool:
        if self._access_token is None:
            return True
        if self._token_expiry is None:
            return True
        # Refresh 5 minutes before expiry
        remaining = (self._token_expiry - datetime.now(timezone.utc)).total_seconds()
        return remaining < 300

    async def _refresh_token(self) -> None:
        """
        Obtain OAuth2 access token from Entra ID.

        This implementation prefers MSAL (client credentials) when the
        environment is configured with ENTRA_CLIENT_ID and ENTRA_CLIENT_SECRET
        or when USE_MSAL_FOR_SOURCE_AUTH is set. MSAL acquisition runs in a
        background thread to avoid blocking the event loop.

        Falls back to the previous httpx-based token endpoint POST when MSAL
        configuration is not available.
        """
        creds = self.config.credentials

        # If the connector was configured with a user assertion (delegated token),
        # prefer OBO: exchange the user token for a token to call the source API.
        if creds.get('user_assertion'):
            scope = ["https://api.businesscentral.dynamics.com/.default"]
            try:
                obo_res = await token_validator.acquire_token_on_behalf_of_async(creds['user_assertion'], scope)
            except Exception as e:
                raise ConnectorAuthError(f"OBO token exchange failed: {e}") from e
            self._access_token = obo_res.get('access_token')
            expires_in = int(obo_res.get('expires_in', 3600))
            self._token_expiry = datetime.fromtimestamp(
                datetime.now(timezone.utc).timestamp() + expires_in,
                tz=timezone.utc,
            )
            if self._client:
                self._client.headers.update({"Authorization": f"Bearer {self._access_token}"})
            return

        use_msal = os.getenv('USE_MSAL_FOR_SOURCE_AUTH', '').lower() in ('1', 'true') or (
            os.getenv('ENTRA_CLIENT_ID') and os.getenv('ENTRA_CLIENT_SECRET')
        )

        if use_msal:
            # Acquire app token via MSAL in a thread (blocking msal call)
            scope = ["https://api.businesscentral.dynamics.com/.default"]
            try:
                result = await asyncio.to_thread(token_validator.acquire_app_token, scope)
            except Exception as e:
                raise ConnectorAuthError(f"MSAL client credentials failed: {e}") from e

            self._access_token = result.get('access_token')
            expires_in = int(result.get('expires_in', 3600))
            self._token_expiry = datetime.fromtimestamp(
                datetime.now(timezone.utc).timestamp() + expires_in,
                tz=timezone.utc,
            )
            if self._client:
                self._client.headers.update({"Authorization": f"Bearer {self._access_token}"})
            return

        # Fallback: direct token endpoint POST (legacy POC flow)
        token_url = (
            f"https://login.microsoftonline.com/{creds['tenant_id']}"
            f"/oauth2/v2.0/token"
        )
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": creds["client_id"],
                        "client_secret": creds["client_secret"],
                        "scope": "https://api.businesscentral.dynamics.com/.default",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                self._access_token = data["access_token"]
                self._token_expiry = datetime.fromtimestamp(
                    datetime.now(timezone.utc).timestamp() + data.get("expires_in", 3600),
                    tz=timezone.utc,
                )
                if self._client:
                    self._client.headers.update({"Authorization": f"Bearer {self._access_token}"})
            except httpx.HTTPStatusError as e:
                raise ConnectorAuthError(
                    f"Failed to obtain BC access token: {e.response.status_code} "
                    f"{e.response.text}"
                ) from e

    def _verify_webhook_signature(self, raw_body: bytes, client_state: str) -> bool:
        """Verify the BC webhook clientState matches our stored secret."""
        return hmac.compare_digest(client_state, self.config.webhook_secret)

    # ------------------------------------------------------------------
    # ConnectorBase implementation
    # ------------------------------------------------------------------

    async def authenticate(self) -> bool:
        """
        Validate credentials by calling the BC companies endpoint.

        ── POC INTEGRATION POINT ──────────────────────────────────────
        If your POC has a test_connection() or similar, the logic goes here.
        ────────────────────────────────────────────────────────────────
        """
        try:
            client = await self._get_client()
            url = f"{self.config.base_url.rstrip('/')}/api/v2.0/companies"
            resp = await client.get(url)
            resp.raise_for_status()
            self.logger.info(
                "BC authentication successful",
                extra={"tenant_id": self.config.tenant_id, "item_id": self.config.item_id},
            )
            return True
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                raise ConnectorAuthError(
                    "Business Central credentials are invalid or expired. "
                    "Check your Client ID, Client Secret, and Tenant ID."
                )
            raise RetryableError(
                f"BC API returned {e.response.status_code}", retry_after_seconds=60
            )

    async def discover_entities(self) -> list[EntityMetadata]:
        """
        Discover all webhook-supported entities from BC.

        Calls the BC runtime API to get the list dynamically.
        Never hardcoded.
        """
        client = await self._get_client()
        url = (
            f"{self.config.base_url.rstrip('/')}/api/microsoft/runtime/beta"
            f"/companies({self.config.company_id})/webhookSupportedResources"
            f"?$filter=resource eq 'v2.0*'"
        )
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            resources = resp.json().get("value", [])
        except httpx.HTTPStatusError as e:
            raise RetryableError(f"Failed to discover BC entities: {e}") from e

        return [
            EntityMetadata(
                name=r["resource"].replace("v2.0/", ""),
                display_name=self._to_display_name(r["resource"].replace("v2.0/", "")),
                supports_webhook=True,
            )
            for r in resources
        ]

    async def subscribe_changes(self, entities: list[str]) -> None:
        """
        Register BC webhook subscriptions for each entity.

        BC subscriptions expire in 3 days — scheduler renews them every 2 days.
        """
        client = await self._get_client()
        sub_url = f"{self.config.base_url.rstrip('/')}/api/v2.0/subscriptions"
        notification_url = (
            f"https://{{BACKEND_HOST}}/webhook/bc/{self.config.item_id}"
        )  # TODO: inject BACKEND_HOST from config

        new_subscription_ids = []
        for entity in entities:
            try:
                resp = await client.post(sub_url, json={
                    "notificationUrl": notification_url,
                    "resource": f"v2.0/{entity}",
                    "clientState": self.config.webhook_secret,
                })
                resp.raise_for_status()
                sub_id = resp.json()["id"]
                new_subscription_ids.append(sub_id)
                self.logger.info(
                    "BC webhook subscription created",
                    extra={
                        "tenant_id": self.config.tenant_id,
                        "item_id": self.config.item_id,
                        "entity": entity,
                        "subscription_id": sub_id,
                    },
                )
            except httpx.HTTPStatusError as e:
                raise RetryableError(
                    f"Failed to subscribe to BC entity '{entity}': {e.response.status_code}"
                ) from e

        self.config.active_subscription_ids.extend(new_subscription_ids)

    async def handle_incoming_event(self, raw_payload: dict) -> list[ChangeEvent]:
        """
        Parse a BC webhook notification payload.

        BC sends batched notifications. Each notification contains:
        - entityName: the entity type (e.g. "salesOrder")
        - id: the record ID
        - changeType: "created" | "updated" | "deleted" | "collection"

        BC does NOT include record data — payload is always None here.
        The framework calls fetch_record() automatically.

        ── POC INTEGRATION POINT ──────────────────────────────────────
        If your POC has webhook handling logic, bring it here.
        Map changeType strings to ChangeType enum values.
        ────────────────────────────────────────────────────────────────
        """
        # Validate clientState
        client_state = raw_payload.get("clientState", "")
        if not self._verify_webhook_signature(b"", client_state):
            raise ConnectorAuthError("BC webhook signature validation failed")

        events = []
        for notification in raw_payload.get("value", []):
            change_type_str = notification.get("changeType", "")
            change_type = self._map_change_type(change_type_str)
            if change_type is None:
                # "collection" type — BC signals bulk changes, trigger poll fallback
                self.logger.warning(
                    "BC collection notification received — scheduling poll reconciliation",
                    extra={
                        "tenant_id": self.config.tenant_id,
                        "item_id": self.config.item_id,
                        "entity": notification.get("entityName"),
                    },
                )
                continue

            events.append(ChangeEvent(
                source_system="bc",
                tenant_id=self.config.tenant_id,
                item_id=self.config.item_id,
                entity_type=notification["entityName"],
                record_id=notification["id"],
                change_type=change_type,
                timestamp=datetime.now(timezone.utc),
                payload=None,  # BC never sends data in webhook — fetch_record() called next
            ))

        return events

    async def fetch_record(self, entity_type: str, record_id: str) -> dict[str, Any]:
        """
        Fetch a single BC record by ID via OData.

        ── POC INTEGRATION POINT ──────────────────────────────────────
        Your POC likely has this logic already — bring it here.
        Map the OData response to a flat dict.
        ────────────────────────────────────────────────────────────────
        """
        client = await self._get_client()
        url = self._api_url(f"{entity_type}({record_id})")
        try:
            resp = await client.get(url)
            if resp.status_code == 404:
                raise ConnectorNotFoundError(
                    f"BC record not found: {entity_type}({record_id})"
                )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise RetryableError(
                f"BC fetch_record failed: {e.response.status_code}"
            ) from e

    async def initial_load(self, entity_type: str) -> AsyncIterator[list[dict[str, Any]]]:
        """
        Page through all records for a BC entity using OData $top/$skip.

        ── POC INTEGRATION POINT ──────────────────────────────────────
        If your POC does a full data load, that logic goes here.
        Use pagination — never load everything at once.
        ────────────────────────────────────────────────────────────────
        """
        client = await self._get_client()
        skip = 0
        page_size = 500

        while True:
            url = self._api_url(f"{entity_type}?$top={page_size}&$skip={skip}")
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                records = resp.json().get("value", [])
            except httpx.HTTPStatusError as e:
                raise RetryableError(
                    f"BC initial_load page failed at skip={skip}: {e}"
                ) from e

            if not records:
                break

            yield records
            skip += len(records)

            if len(records) < page_size:
                break  # Last page

    async def renew_subscriptions(self) -> None:
        """
        Renew all active BC webhook subscriptions (PATCH with new expiry).

        Called every 2 days by the scheduler.
        BC subscriptions expire after 3 days without renewal.
        """
        client = await self._get_client()
        for sub_id in self.config.active_subscription_ids:
            url = f"{self.config.base_url.rstrip('/')}/api/v2.0/subscriptions({sub_id})"
            try:
                resp = await client.patch(url, json={
                    "notificationUrl": (
                        f"https://{{BACKEND_HOST}}/webhook/bc/{self.config.item_id}"
                    ),
                    "clientState": self.config.webhook_secret,
                })
                resp.raise_for_status()
                new_expiry = resp.json().get("expirationDateTime", "unknown")
                self.logger.info(
                    "BC subscription renewed",
                    extra={
                        "tenant_id": self.config.tenant_id,
                        "item_id": self.config.item_id,
                        "subscription_id": sub_id,
                        "new_expiry": new_expiry,
                    },
                )
            except httpx.HTTPStatusError as e:
                raise RetryableError(
                    f"BC subscription renewal failed for {sub_id}: {e.response.status_code}"
                ) from e

    async def revoke_subscriptions(self) -> None:
        """
        Delete all BC webhook subscriptions.
        Called when the Fabric item is deleted.
        """
        client = await self._get_client()
        for sub_id in list(self.config.active_subscription_ids):
            url = f"{self.config.base_url.rstrip('/')}/api/v2.0/subscriptions({sub_id})"
            try:
                resp = await client.delete(url)
                if resp.status_code == 404:
                    pass  # Already gone — fine
                else:
                    resp.raise_for_status()
                self.config.active_subscription_ids.remove(sub_id)
                self.logger.info(
                    "BC subscription revoked",
                    extra={
                        "tenant_id": self.config.tenant_id,
                        "item_id": self.config.item_id,
                        "subscription_id": sub_id,
                    },
                )
            except httpx.HTTPStatusError as e:
                self.logger.warning(
                    f"Could not revoke BC subscription {sub_id}: {e.response.status_code}",
                    extra={"tenant_id": self.config.tenant_id, "item_id": self.config.item_id},
                )

    async def poll_changes(
        self, entity_type: str, since: datetime
    ) -> list[ChangeEvent]:
        """
        Fallback poll for records modified since a given timestamp.

        Used for reconciliation after missed webhook events (e.g. BC delivery failure).
        Note: BC lastModifiedDateTime does NOT capture deletes.

        ── POC INTEGRATION POINT ──────────────────────────────────────
        If your POC uses polling as its primary mechanism, that logic is here.
        ────────────────────────────────────────────────────────────────
        """
        client = await self._get_client()
        since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        url = self._api_url(
            f"{entity_type}?$filter=lastModifiedDateTime gt {since_str}"
        )
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            records = resp.json().get("value", [])
        except httpx.HTTPStatusError as e:
            raise RetryableError(f"BC poll_changes failed: {e}") from e

        return [
            ChangeEvent(
                source_system="bc",
                tenant_id=self.config.tenant_id,
                item_id=self.config.item_id,
                entity_type=entity_type,
                record_id=r["id"],
                change_type=ChangeType.UPDATE,  # poll can't detect deletes
                timestamp=datetime.now(timezone.utc),
                payload=r,  # poll returns full data — no fetch needed
            )
            for r in records
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_change_type(bc_change_type: str) -> ChangeType | None:
        """Map BC changeType strings to internal ChangeType enum."""
        return {
            "created": ChangeType.INSERT,
            "updated": ChangeType.UPDATE,
            "deleted": ChangeType.DELETE,
            "collection": None,  # Signals bulk change — handle separately
        }.get(bc_change_type.lower())

    @staticmethod
    def _to_display_name(api_name: str) -> str:
        """Convert camelCase API name to human-readable display name."""
        import re
        words = re.sub(r"([A-Z])", r" \1", api_name).strip()
        return words.title()
