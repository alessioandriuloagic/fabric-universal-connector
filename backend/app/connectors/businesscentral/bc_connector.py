"""
Business Central connector.

Source:  BC REST API v2.0 (OData v4)
Auth:    MSAL client credentials → BC token
Change:  timestamp watermark (lastModifiedDateTime)
Schema:  bronze_bc
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, List, Optional

import pandas as pd

from app.connectors.base_connector import BaseConnector, Watermark
from app.connectors.businesscentral.bc_client import BusinessCentralClient
from app.exceptions import AuthenticationError, ConnectorFatalError
from app.models.connector_item_definition import (
    BusinessCentralConnectorItemDefinition,
    BusinessCentralEntityConfiguration,
)
from app.services.auth_service import ResolvedCredentials, acquire_msal_token

log = logging.getLogger(__name__)

BC_SCOPE = "https://api.businesscentral.dynamics.com/.default"


@dataclass(frozen=True)
class BCAuthContext:
    access_token: str
    base_url: str


class BusinessCentralConnector(BaseConnector):
    BRONZE_SCHEMA = "bronze_bc"
    MODULE_TYPE = "businesscentral"

    def __init__(
        self,
        config: BusinessCentralConnectorItemDefinition,
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
        self.bc_config = config
        self.credentials = credentials
        self._bc_client = BusinessCentralClient(
            tenant_id=config.source.tenant_id,
            environment=config.source.environment,
            company_id=config.source.company_id,
            api_version=config.source.api_version,
            page_size=config.source.page_size,
        )

    async def _authenticate(self) -> BCAuthContext:
        token = await acquire_msal_token(self.credentials, BC_SCOPE)
        return BCAuthContext(
            access_token=token,
            base_url=self._bc_client.base_url,
        )

    async def _extract_entity(
        self,
        entity: BusinessCentralEntityConfiguration,
        auth: BCAuthContext,
        watermark: Optional[Watermark],
    ) -> pd.DataFrame:
        wm_col = entity.watermark_column
        wm_value = watermark.watermark_value if watermark else None

        records = await self._bc_client.fetch_all(
            token=auth.access_token,
            api_endpoint=entity.api_endpoint,
            select_columns=entity.select_columns,
            watermark_column=wm_col,
            watermark_value=wm_value,
            filter_expression=entity.filter_expression,
        )

        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        df["_operation"] = "insert"

        log.info(
            "BC %s: %d records (watermark=%s)", entity.api_endpoint, len(df), wm_value
        )
        return df

    def _get_new_watermark(
        self,
        entity: BusinessCentralEntityConfiguration,
        auth: BCAuthContext,
        df: pd.DataFrame,
    ) -> Optional[Watermark]:
        col = entity.watermark_column
        if df.empty or col not in df.columns:
            return None

        max_val = df[col].max()
        if pd.isna(max_val):
            return None

        return Watermark(
            watermark_type="timestamp",
            watermark_value=str(max_val),
            watermark_column=col,
        )

    def _get_enabled_entities(self) -> List[BusinessCentralEntityConfiguration]:
        return self.bc_config.enabled_entities()

    def _entity_name(self, entity: BusinessCentralEntityConfiguration) -> str:
        return entity.api_endpoint
