"""
CRM / Dataverse connector.

Source:  Dataverse Web API (OData v4)
Auth:    MSAL client credentials → Dataverse token
Change:  OData Change Tracking (@odata.deltaLink)
Schema:  bronze_crm
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List, Optional

import pandas as pd

from app.connectors.base_connector import BaseConnector, Watermark
from app.connectors.crm.dataverse_client import DataverseClient
from app.connectors.crm.entity_catalog import CRM_ENTITY_CATALOG
from app.exceptions import AuthenticationError, ConnectorFatalError, EntityExtractionError
from app.models.connector_item_definition import (
    CrmConnectorItemDefinition,
    CrmEntityConfiguration,
)
from app.services.auth_service import ResolvedCredentials, acquire_msal_token

log = logging.getLogger(__name__)

DATAVERSE_SCOPE_SUFFIX = "/.default"


@dataclass(frozen=True)
class CRMAuthContext:
    access_token: str
    environment_url: str


class CRMConnector(BaseConnector):
    BRONZE_SCHEMA = "bronze_crm"
    MODULE_TYPE = "crm"

    def __init__(
        self,
        config: CrmConnectorItemDefinition,
        workspace_id: str,
        lakehouse_id: str,
        connector_id: str,
        bearer_token: str,
        credentials: ResolvedCredentials,
    ):
        super().__init__(
            config=config,
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            connector_id=connector_id,
            bearer_token=bearer_token,
        )
        self.crm_config = config
        self.credentials = credentials
        self._dv_client = DataverseClient(
            environment_url=config.source.environment_url,
            api_version=config.source.api_version,
            page_size=config.source.page_size,
        )
        self._last_delta_link: Optional[str] = None

    # ── Abstract implementations ───────────────────────────────────────────────

    async def _authenticate(self) -> CRMAuthContext:
        env_url = self.crm_config.source.environment_url.rstrip("/")
        scope = f"{env_url}{DATAVERSE_SCOPE_SUFFIX}"

        token = await acquire_msal_token(self.credentials, scope)
        return CRMAuthContext(
            access_token=token,
            environment_url=env_url,
        )

    async def _extract_entity(
        self,
        entity: CrmEntityConfiguration,
        auth: CRMAuthContext,
        watermark: Optional[Watermark],
    ) -> pd.DataFrame:
        catalog_entry = CRM_ENTITY_CATALOG.get(entity.logical_name)
        if catalog_entry is None:
            raise EntityExtractionError(
                f"Entity '{entity.logical_name}' not in CRM catalog"
            )
        if not catalog_entry.supports_change_tracking:
            raise EntityExtractionError(
                f"Change Tracking not supported for '{entity.logical_name}'"
            )

        select_cols = entity.select_columns or catalog_entry.default_select_columns
        delta_token = watermark.delta_token if watermark else None

        records, new_delta_link = await self._dv_client.fetch_all(
            token=auth.access_token,
            plural_name=catalog_entry.plural_name,
            select_columns=select_cols,
            filter_expression=entity.filter_expression,
            delta_token=delta_token,
        )

        self._last_delta_link = new_delta_link

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df = _clean_odata_columns(df)

        log.info(
            "CRM %s: %d records extracted (delta=%s)",
            entity.logical_name, len(df), bool(delta_token)
        )
        return df

    def _get_new_watermark(
        self,
        entity: CrmEntityConfiguration,
        auth: CRMAuthContext,
        df: pd.DataFrame,
    ) -> Optional[Watermark]:
        if self._last_delta_link is None:
            return None
        return Watermark(
            watermark_type="delta_token",
            delta_token=self._last_delta_link,
        )

    def _get_enabled_entities(self) -> List[CrmEntityConfiguration]:
        return self.crm_config.enabled_entities()

    def _entity_name(self, entity: CrmEntityConfiguration) -> str:
        return entity.logical_name


# ── Helpers ────────────────────────────────────────────────────────────────────

def _clean_odata_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remove OData annotation columns (@odata.*) and @removed markers."""
    odata_cols = [c for c in df.columns if c.startswith("@") or c == "@removed"]
    return df.drop(columns=odata_cols, errors="ignore")
