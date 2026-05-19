"""
SQL Server / Azure SQL connector.

Source:  SQL Server via SQLAlchemy + pyodbc (no Spark JDBC)
Auth:    SQL auth via resolved credentials (Fabric Connection or Key Vault)
Change:  Watermark column (datetime / rowversion / integer)
Schema:  bronze_sql
"""
from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from app.connectors.base_connector import BaseConnector, Watermark
from app.exceptions import (
    AuthenticationError,
    ConnectorFatalError,
    EntityExtractionError,
    TransientError,
)
from app.models.connector_item_definition import (
    SqlConnectorItemDefinition,
    SqlEntityConfiguration,
)
from app.services.auth_service import ResolvedCredentials

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SQLAuthContext:
    connection_string: str


def _normalize_table_name(schema: str, table: str) -> str:
    """Converts 'dbo.CustomerOrders' → 'dbo_customerorders' for Delta table naming."""
    return f"{schema}_{table}".lower().replace(" ", "_")


_engine_cache: Dict[str, Any] = {}
_engine_lock = threading.Lock()


def _get_engine(connection_string: str) -> Any:
    """Returns a cached SQLAlchemy engine; creates one on first call per connection string."""
    import sqlalchemy as sa

    with _engine_lock:
        if connection_string not in _engine_cache:
            _engine_cache[connection_string] = sa.create_engine(
                connection_string,
                fast_executemany=True,
                connect_args={"timeout": 30},
                pool_size=5,
                max_overflow=10,
            )
        return _engine_cache[connection_string]


def _run_sql_query(
    connection_string: str,
    query: str,
    params: Optional[Dict[str, Any]] = None,
) -> pd.DataFrame:
    """Synchronous SQL execution — always called via asyncio.to_thread."""
    import sqlalchemy as sa

    engine = _get_engine(connection_string)
    with engine.connect() as conn:
        stmt = sa.text(query) if params else query
        df = pd.read_sql(stmt, conn, params=params)
    return df if df is not None else pd.DataFrame()


class SQLConnector(BaseConnector):
    BRONZE_SCHEMA = "bronze_sql"
    MODULE_TYPE = "sql"

    def __init__(
        self,
        config: SqlConnectorItemDefinition,
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
        self.sql_config = config
        self.credentials = credentials

    async def _authenticate(self) -> SQLAuthContext:
        src = self.sql_config.source

        if not self.credentials.client_id or not self.credentials.client_secret:
            raise ConnectorFatalError(
                "SQL credentials not resolved — check Fabric Connection or Key Vault config",
                "CONFIG_VALIDATION_ERROR",
            )

        driver = "{ODBC Driver 18 for SQL Server}"
        conn_str = (
            f"mssql+pyodbc://{self.credentials.client_id}"
            f":{self.credentials.client_secret}"
            f"@{src.server}:{src.port}/{src.database}"
            f"?driver={driver}"
            f"&Encrypt={'yes' if src.encrypt else 'no'}"
            f"&TrustServerCertificate={'yes' if src.trust_server_certificate else 'no'}"
        )
        return SQLAuthContext(connection_string=conn_str)

    async def _extract_entity(
        self,
        entity: SqlEntityConfiguration,
        auth: SQLAuthContext,
        watermark: Optional[Watermark],
    ) -> pd.DataFrame:
        # Build query (CPU only — no I/O, safe in async context)
        columns = "*"
        if entity.select_columns:
            columns = ", ".join(f"[{c}]" for c in entity.select_columns)

        where_clauses: List[str] = []
        # Watermark value is a bound parameter (:wm_val) to prevent SQL injection.
        # Column/table identifiers come from Pydantic-validated config — they are trusted.
        params: Dict[str, Any] = {}
        if watermark and watermark.watermark_value and entity.watermark_column:
            col = entity.watermark_column
            val = watermark.watermark_value
            wm_type = entity.watermark_column_type or "datetime"
            if wm_type == "datetime":
                where_clauses.append(f"[{col}] > :wm_val")
                params["wm_val"] = val
            elif wm_type == "integer":
                where_clauses.append(f"[{col}] > :wm_val")
                params["wm_val"] = int(val)
            elif wm_type == "rowversion":
                # CONVERT accepts a literal hex string; value is still parameterized.
                where_clauses.append(f"[{col}] > CONVERT(BINARY(8), :wm_val)")
                params["wm_val"] = val

        if entity.where_clause:
            # User-configured free-text clause from the item definition (trusted config).
            where_clauses.append(entity.where_clause)

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        order_sql = f"ORDER BY [{entity.watermark_column}] ASC" if entity.watermark_column else ""

        query = (
            f"SELECT {columns} "
            f"FROM [{entity.schema_name}].[{entity.table_name}] "
            f"{where_sql} {order_sql}"
        ).strip()
        log.debug("SQL query: %s | params: %s", query, list(params.keys()))

        # Execute in thread pool — SQLAlchemy + pyodbc are synchronous
        try:
            df = await asyncio.to_thread(
                _run_sql_query, auth.connection_string, query, params or None
            )
        except Exception as exc:
            if "login" in str(exc).lower() or "authentication" in str(exc).lower():
                raise AuthenticationError(f"SQL auth failed: {exc}") from exc
            if "timeout" in str(exc).lower() or "connection" in str(exc).lower():
                raise TransientError(f"SQL connection error: {exc}") from exc
            raise EntityExtractionError(f"SQL extraction error: {exc}") from exc

        df["_operation"] = "insert"
        log.info(
            "SQL %s.%s: %d records (watermark=%s)",
            entity.schema_name, entity.table_name, len(df),
            watermark.watermark_value if watermark else None,
        )
        return df

    def _get_new_watermark(
        self,
        entity: SqlEntityConfiguration,
        auth: SQLAuthContext,
        df: pd.DataFrame,
    ) -> Optional[Watermark]:
        col = entity.watermark_column
        col_type = entity.watermark_column_type or "datetime"

        if not col or df.empty or col not in df.columns:
            return None

        max_val = df[col].max()
        if pd.isna(max_val):
            return None

        return Watermark(
            watermark_type=col_type,
            watermark_value=str(max_val),
            watermark_column=col,
        )

    def _get_enabled_entities(self) -> List[SqlEntityConfiguration]:
        return self.sql_config.enabled_entities()

    def _entity_name(self, entity: SqlEntityConfiguration) -> str:
        return _normalize_table_name(entity.schema_name, entity.table_name)
