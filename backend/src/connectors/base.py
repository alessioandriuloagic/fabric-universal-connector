"""
backend/src/connectors/base.py

ConnectorBase — The abstract interface every source system adapter must implement.

Rules:
- Every adapter subclasses ConnectorBase. No exceptions.
- Adapters never import from each other.
- Adapters never write Parquet or call Open Mirroring APIs directly.
- Adapters never call Fabric APIs.
- Adapters return ChangeEvent objects. That is their only job.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, ClassVar, Type

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core data models
# ---------------------------------------------------------------------------

class ChangeType(str, Enum):
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"


class SyncMode(str, Enum):
    WEBHOOK = "webhook"       # Push-based: source notifies us on change
    POLLING = "polling"       # Pull-based: we poll the source on a schedule


@dataclass
class ChangeEvent:
    """
    The single internal currency of the Connector Framework.

    All adapters produce ChangeEvent objects.
    The Open Mirroring Writer consumes ChangeEvent objects.
    Nothing else passes between them.

    If payload is None, the framework calls fetch_record() automatically
    to retrieve the full row before writing to the landing zone.
    """
    source_system: str          # "bc" | "d365" | "salesforce" | "sap"
    tenant_id: str              # Customer Fabric tenant ID
    item_id: str                # Fabric item ID (one item = one connector config)
    entity_type: str            # Source entity name e.g. "salesOrders", "Account"
    record_id: str              # Primary key of the changed record
    change_type: ChangeType
    timestamp: datetime
    payload: dict[str, Any] | None = None   # Full row data, or None if must be fetched


@dataclass
class EntityMetadata:
    """
    Describes a single entity (table/object) available on the source system.
    Returned by discover_entities() and shown in the UI table selection step.
    """
    name: str                           # API name e.g. "salesOrders"
    display_name: str                   # Human-readable e.g. "Sales Orders"
    supports_webhook: bool              # True = push; False = poll only
    estimated_row_count: int | None = None
    description: str = ""


@dataclass
class ConnectorConfig:
    """
    Per-customer connector configuration.
    Non-secret fields come from the Fabric item payload.
    Secret fields (credentials) come from Azure Key Vault at runtime.
    """
    tenant_id: str
    item_id: str
    source_system: str

    # Connection (non-secret)
    base_url: str
    company_id: str | None = None       # BC-specific, None for others

    # Selected entities to sync
    entities: list[str] = field(default_factory=list)

    # Sync configuration
    sync_mode: SyncMode = SyncMode.WEBHOOK
    poll_interval_minutes: int = 15     # Used when sync_mode = POLLING

    # Populated at runtime from Key Vault — never stored in item payload
    credentials: dict[str, str] = field(default_factory=dict)

    # Internal state
    webhook_secret: str = ""            # HMAC secret to validate incoming webhooks
    active_subscription_ids: list[str] = field(default_factory=list)


@dataclass
class ConnectorHealth:
    """
    Returned by health_check() and shown in the SyncMonitor UI component.
    """
    is_healthy: bool
    last_successful_sync: datetime | None
    last_error: str | None
    active_subscriptions: int
    total_events_processed: int
    details: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Custom exceptions — used by adapters to signal specific error conditions
# ---------------------------------------------------------------------------

class ConnectorError(Exception):
    """Base class for all connector errors."""


class ConnectorAuthError(ConnectorError):
    """
    Raised when credentials are invalid or expired.
    Surfaces to the UI as an actionable error with a 'Reconnect' button.
    """


class ConnectorNotFoundError(ConnectorError):
    """Raised when a requested entity or record does not exist on the source."""


class RetryableError(ConnectorError):
    """
    Raised on transient errors (rate limits, 5xx).
    The framework will retry with exponential backoff.
    """
    def __init__(self, message: str, retry_after_seconds: int = 60):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


# ---------------------------------------------------------------------------
# ConnectorBase — the abstract interface
# ---------------------------------------------------------------------------

class ConnectorBase(ABC):
    """
    Abstract base class for all source system adapters.

    Subclass this to add a new source system.
    See docs/adding-a-connector.md for the full guide.

    Lifecycle:
        1. Instantiated with ConnectorConfig when a customer's item is loaded.
        2. authenticate() is called to verify credentials are valid.
        3. discover_entities() is called to populate the UI table selection.
        4. subscribe_changes() is called when the customer saves the configuration.
        5. handle_incoming_event() is called each time the source pushes a notification.
           (For polling adapters, poll_changes() is called on schedule instead.)
        6. fetch_record() is called when payload is None on a ChangeEvent.
        7. initial_load() is called once after the first configuration save.
        8. renew_subscriptions() is called every 2 days by the scheduler.
        9. revoke_subscriptions() is called when the Fabric item is deleted.
    """

    # Set in each subclass. Used by ConnectorRegistry.
    SOURCE_SYSTEM_ID: ClassVar[str]

    # Set True in subclasses that use polling instead of webhooks.
    USES_POLLING: ClassVar[bool] = False

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

    # ------------------------------------------------------------------
    # MANDATORY — must be implemented by every adapter
    # ------------------------------------------------------------------

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Validate that the credentials in self.config.credentials are valid
        and can reach the source system.

        Called when the customer clicks 'Test Connection' in the UI.
        Called again before initial_load() and subscribe_changes().

        Returns True if credentials are valid.
        Raises ConnectorAuthError with a human-readable message if not.

        Example:
            try:
                await self._client.get("/companies")
                return True
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 403):
                    raise ConnectorAuthError(
                        "Invalid Client ID or Client Secret. "
                        "Check your Entra App registration."
                    )
                raise RetryableError(str(e))
        """

    @abstractmethod
    async def discover_entities(self) -> list[EntityMetadata]:
        """
        Return all entities available on the source system that can be synced.

        Called when the customer reaches Step 2 (table selection) in the wizard.
        Must return only entities that are both readable AND trackable for changes.

        For BC: call GET .../webhookSupportedResources?$filter=resource eq 'v2.0*'
        For D365: enumerate Dataverse entities with change tracking enabled.
        For Salesforce: enumerate objects with CDC enabled.
        For SAP: enumerate OData entities or Event Mesh topics.

        Never hardcode entity lists. Always discover dynamically.
        """

    @abstractmethod
    async def subscribe_changes(self, entities: list[str]) -> None:
        """
        Register change notifications for the given entity list on the source system.

        Called once when the customer saves the connector configuration.
        Also called when the customer adds new entities to an existing connector.

        Must store subscription IDs in self.config.active_subscription_ids
        so that renew_subscriptions() and revoke_subscriptions() can find them.

        For push-based adapters: register webhooks pointing to the ISV backend.
        For polling adapters (USES_POLLING=True): register a scheduled poll job
        and set the initial watermark per entity.

        The notificationUrl for webhooks is:
            https://{backend_host}/webhook/{SOURCE_SYSTEM_ID}/{self.config.item_id}

        The webhook clientState/secret for HMAC validation is:
            self.config.webhook_secret
        """

    @abstractmethod
    async def handle_incoming_event(self, raw_payload: dict) -> list[ChangeEvent]:
        """
        Parse a raw webhook payload from the source system into ChangeEvent objects.

        Called by the webhook HTTP endpoint (api/webhook.py) when a notification arrives.
        Must validate the request signature using self.config.webhook_secret before parsing.

        One payload may contain multiple notifications (BC batches up to 1000).
        Return one ChangeEvent per changed record.

        If the source does NOT include record data in the webhook (e.g. BC):
            Set payload=None on the ChangeEvent.
            The framework calls fetch_record() automatically to hydrate it.

        If the source DOES include full record data (e.g. D365 PostEntityImages):
            Set payload=<full row dict> on the ChangeEvent.
            fetch_record() will NOT be called.

        Raises ConnectorAuthError if the signature is invalid.
        """

    @abstractmethod
    async def fetch_record(self, entity_type: str, record_id: str) -> dict[str, Any]:
        """
        Fetch a single record by ID from the source system.

        Called automatically by the framework when a ChangeEvent has payload=None.
        Also called to verify record existence before writing a DELETE event.

        Must return the full row as a flat dict.
        Keys must match the schema returned by discover_entities().

        Raises ConnectorNotFoundError if the record has been deleted before fetch
        (common race condition — handle gracefully, treat as a DELETE event).
        Raises RetryableError on transient failures.
        """

    @abstractmethod
    async def initial_load(self, entity_type: str) -> AsyncIterator[list[dict[str, Any]]]:
        """
        Yield batches of all records for the given entity.

        Called once per entity after the customer saves the configuration for the first time.
        Also called if the customer manually triggers a 'Full Resync'.

        Must use pagination — never load the entire entity into memory.
        Recommended batch size: 500–1000 records per yield.

        Yielded dicts are raw records (no __rowMarker__).
        The Open Mirroring Writer handles the initial load file format.

        Example:
            skip = 0
            while True:
                batch = await self._client.get_page(entity_type, skip=skip, top=500)
                if not batch:
                    break
                yield batch
                skip += len(batch)
        """

    @abstractmethod
    async def renew_subscriptions(self) -> None:
        """
        Renew all active webhook subscriptions before they expire.

        Called every 2 days by the APScheduler job in scheduler/jobs.py.
        Must be idempotent — safe to call multiple times.

        BC subscriptions expire after 3 days without renewal.
        D365 subscriptions have their own expiry.
        For polling adapters: no-op (subscriptions don't expire).

        Must log each renewal with tenant_id, item_id, entity, new_expiry.
        Must raise RetryableError (not silently fail) if renewal fails,
        so the scheduler can retry and alert on repeated failures.
        """

    @abstractmethod
    async def revoke_subscriptions(self) -> None:
        """
        Cancel all active webhook subscriptions on the source system.

        Called when the Fabric item is DELETED (item_lifecycle DELETE endpoint).
        Must clean up ALL subscriptions — leaving orphan subscriptions on the
        source system is unacceptable (it causes phantom webhook traffic).

        After revoking, clear self.config.active_subscription_ids.
        Must not raise if a subscription is already expired or not found.
        """

    # ------------------------------------------------------------------
    # OPTIONAL — override if the source supports polling fallback
    # ------------------------------------------------------------------

    async def poll_changes(self, entity_type: str, since: datetime) -> list[ChangeEvent]:
        """
        Pull incremental changes from the source system since the given timestamp.

        Override this method in polling adapters (USES_POLLING = True).
        Also used as a reconciliation fallback in push adapters
        to catch any events missed due to webhook delivery failures.

        Default implementation returns empty list (no polling).

        For BC: GET /salesOrders?$filter=lastModifiedDateTime gt {since}
        For SAP B1: use DI API or Service Layer with ModifyDate filter.
        """
        return []

    # ------------------------------------------------------------------
    # OPTIONAL — override for richer UI experience
    # ------------------------------------------------------------------

    async def health_check(self) -> ConnectorHealth:
        """
        Return the current health status of this connector.

        Called by the SyncMonitor UI component to display status.
        Default implementation calls authenticate() and returns basic health.

        Override to return richer details: last sync time, event counts, etc.
        """
        try:
            is_healthy = await self.authenticate()
            return ConnectorHealth(
                is_healthy=is_healthy,
                last_successful_sync=None,
                last_error=None,
                active_subscriptions=len(self.config.active_subscription_ids),
                total_events_processed=0,
            )
        except ConnectorAuthError as e:
            return ConnectorHealth(
                is_healthy=False,
                last_successful_sync=None,
                last_error=str(e),
                active_subscriptions=0,
                total_events_processed=0,
            )


# ---------------------------------------------------------------------------
# ConnectorRegistry — maps source_system_id → adapter class
# ---------------------------------------------------------------------------

class ConnectorRegistry:
    """
    Central registry of all available connector adapters.

    When adding a new connector:
    1. Implement ConnectorBase in connectors/{system}.py
    2. Import the class here and add it to _registry below.
    3. That's it — the framework handles the rest.
    """

    _registry: dict[str, Type[ConnectorBase]] = {}

    @classmethod
    def register(cls, adapter_class: Type[ConnectorBase]) -> Type[ConnectorBase]:
        """Decorator to register a connector adapter."""
        system_id = adapter_class.SOURCE_SYSTEM_ID
        if system_id in cls._registry:
            raise ValueError(
                f"Connector '{system_id}' is already registered. "
                f"Each SOURCE_SYSTEM_ID must be unique."
            )
        cls._registry[system_id] = adapter_class
        logger.info(f"Registered connector: {system_id} → {adapter_class.__name__}")
        return adapter_class

    @classmethod
    def get(cls, source_system_id: str) -> Type[ConnectorBase]:
        """
        Resolve a connector class by its SOURCE_SYSTEM_ID.

        Raises ValueError if the system is not registered.
        """
        if source_system_id not in cls._registry:
            registered = list(cls._registry.keys())
            raise ValueError(
                f"No connector registered for source system '{source_system_id}'. "
                f"Registered systems: {registered}"
            )
        return cls._registry[source_system_id]

    @classmethod
    def create(cls, config: ConnectorConfig) -> ConnectorBase:
        """
        Instantiate the correct adapter for a given ConnectorConfig.

        Usage:
            adapter = ConnectorRegistry.create(config)
            await adapter.authenticate()
        """
        adapter_class = cls.get(config.source_system)
        return adapter_class(config)

    @classmethod
    def available_systems(cls) -> list[str]:
        """Return all registered source system IDs."""
        return list(cls._registry.keys())


# ---------------------------------------------------------------------------
# Register all adapters
# Add new adapters here after implementing them.
# ---------------------------------------------------------------------------

def _register_all_adapters() -> None:
    """
    Import and register all connector adapters.
    Called once at application startup (main.py).

    Add your new adapter import here when you implement it.
    The @ConnectorRegistry.register decorator does the actual registration.
    """
    # pylint: disable=import-outside-toplevel
    from connectors.business_central import BCAdapter       # noqa: F401
    from connectors.dynamics365 import D365Adapter          # noqa: F401
    from connectors.salesforce import SalesforceAdapter     # noqa: F401
    from connectors.sap import SAPAdapter                   # noqa: F401
