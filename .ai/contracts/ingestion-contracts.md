# PHASE 3 — INGESTION CONTRACTS

**Project:** Fabric Universal Connector  
**Author:** Principal Architect Review  
**Date:** 2026-05-14  
**Input:** `.ai/architecture/target-architecture.md`, `.ai/contracts/metadata-model.md`  
**Status:** COMPLETE — Awaiting Phase 4 instruction

---

## TABLE OF CONTENTS

1. Contract Overview
2. BaseConnector — Abstract Interface
3. Module Contracts
   - 3.1 CRM / Dataverse Connector
   - 3.2 Business Central Connector
   - 3.3 SQL Connector
4. Watermark Model
5. AuthContext Types
6. BronzeWriter Interface
7. ConfigLoader Interface
8. SchemaEvolutionHandler Interface
9. RetryPolicy Interface
10. Error Taxonomy
11. Run Lifecycle State Machine
12. Connector Registration Contract (TypeScript)
13. Notebook Deployment Contract

---

## 1. CONTRACT OVERVIEW

This document defines the binding contracts between the layers of the ingestion runtime:

```
ConnectorItemDefinition (config-schema.json)
       ↓ deserialized by
ConfigLoader
       ↓ passed to
BaseConnector (module-specific subclass)
       ↓ uses
  ├── AuthContext        — resolved credentials, never raw secrets
  ├── WatermarkStore     — read/write watermarks from _entity_watermarks
  ├── BronzeWriter       — write Delta tables with standard metadata columns
  ├── MetadataWriter     — write to _connector_runs, _error_log
  ├── SchemaEvolutionHandler — enforce schema policy
  └── RetryPolicy        — handle transient failures
       ↓ produces
RunResult
  └── EntityResult[]
```

**Versioning:** All contracts are versioned at `1.0.0`. Breaking changes require a major version bump and corresponding config schema version update.

---

## 2. BASECONNECTOR — ABSTRACT INTERFACE

`BaseConnector` is the abstract base class all module connectors must extend. It is implemented in `agic_fabric_connector/base/connector_base.py`.

### Class Definition

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from pyspark.sql import SparkSession
import pandas as pd

from agic_fabric_connector.config.config_models import (
    ConnectorItemDefinition, EntityConfig, FeaturesConfiguration
)
from agic_fabric_connector.base.metadata_writer import MetadataWriter
from agic_fabric_connector.base.bronze_writer import BronzeWriter
from agic_fabric_connector.base.schema_evolution import SchemaEvolutionHandler
from agic_fabric_connector.base.retry_policy import RetryPolicy
from agic_fabric_connector.auth.auth_models import AuthContext
from agic_fabric_connector.base.watermark import Watermark, WatermarkStore
from agic_fabric_connector.base.run_result import RunResult, EntityResult


class BaseConnector(ABC):
    """
    Abstract base class for all Fabric Universal Connector module implementations.

    Subclasses implement the source-specific extraction logic.
    All shared concerns (Bronze write, metadata, schema evolution, retry)
    are handled by this base class and must NOT be re-implemented in subclasses.
    """

    def __init__(
        self,
        config: ConnectorItemDefinition,
        spark: SparkSession,
        retry_policy: Optional[RetryPolicy] = None
    ):
        self.config = config
        self.spark = spark
        self.retry_policy = retry_policy or RetryPolicy()
        self._metadata_writer = MetadataWriter(config, spark)
        self._bronze_writer = BronzeWriter(config, spark)
        self._watermark_store = WatermarkStore(config, spark)
        self._schema_handler = SchemaEvolutionHandler(
            config.features.schemaEvolutionHandling
        )

    # ────────────────────────────────────────────────────────────
    # PUBLIC ENTRY POINT — do not override
    # ────────────────────────────────────────────────────────────

    def run(self) -> RunResult:
        """
        Main entry point. Orchestrates the full ingestion run.
        Called once per notebook execution.

        Returns: RunResult with per-entity outcomes.
        Raises:  ConnectorFatalError if the run must abort due to
                 unrecoverable failure (e.g. auth failure, config invalid).
        """
        run_record = self._metadata_writer.start_run()
        try:
            self._validate_config()
            auth = self.retry_policy.execute(self._authenticate)
            enabled_entities = self._get_enabled_entities()
            results = self._process_entities(enabled_entities, auth)
            run_record = self._metadata_writer.complete_run(run_record, results)
            return RunResult(
                run_id=run_record.run_id,
                status=run_record.status,
                entity_results=results
            )
        except ConnectorFatalError as e:
            self._metadata_writer.fail_run(run_record, str(e), e.error_code)
            raise
        except Exception as e:
            self._metadata_writer.fail_run(run_record, str(e), "UNEXPECTED_ERROR")
            raise ConnectorFatalError(str(e), "UNEXPECTED_ERROR") from e

    # ────────────────────────────────────────────────────────────
    # ABSTRACT — must implement in each module subclass
    # ────────────────────────────────────────────────────────────

    @abstractmethod
    def _authenticate(self) -> AuthContext:
        """
        Authenticate to the source system.

        CONTRACT:
        - Must resolve credentials via Fabric Connection or Key Vault reference.
        - Must NEVER accept raw credentials as parameters.
        - Must raise AuthenticationError on failure (triggers retry).
        - Must raise ConnectorFatalError if credentials are structurally invalid
          (e.g. missing connection ID) — retrying will not help.

        Returns: AuthContext with resolved credentials for use by _extract_entity.
        """
        ...

    @abstractmethod
    def _extract_entity(
        self,
        entity: EntityConfig,
        auth: AuthContext,
        watermark: Optional[Watermark]
    ) -> pd.DataFrame:
        """
        Extract records for a single entity, respecting the current watermark.

        CONTRACT:
        - If watermark is None: perform full extract (all records).
        - If watermark is set: extract only records changed since the watermark.
        - Must apply entity.extractionMode; raise ValueError if mode unsupported.
        - Must respect entity.batchSize / entity.pageSize for pagination.
        - Must apply entity.filterExpression if set (append to source filter).
        - Must apply entity.selectColumns if set (restrict columns).
        - Must raise ThrottlingError on HTTP 429 (triggers retry with Retry-After).
        - Must raise TransientError on network failures (triggers retry).
        - Must raise EntityExtractionError on logic errors (stops this entity).
        - Must NOT write to Bronze — only return the raw DataFrame.
        - Must NOT update watermarks — this is done by the caller after write.

        The returned DataFrame must contain ONLY source columns.
        ISV metadata columns (_run_id etc.) are added by BronzeWriter.

        Returns: pd.DataFrame of raw source records. May be empty (0 rows) for
                 incremental runs with no changes — this is not an error.
        """
        ...

    @abstractmethod
    def _get_new_watermark(
        self,
        entity: EntityConfig,
        auth: AuthContext,
        extraction_result: pd.DataFrame
    ) -> Optional[Watermark]:
        """
        Compute the new watermark to persist after a successful extraction.

        CONTRACT:
        - Called ONLY after a successful _extract_entity AND successful Bronze write.
        - For delta_token watermarks: return the new delta token from the API response.
        - For timestamp watermarks: return the max value of the watermark column
          in extraction_result.
        - If extraction_result is empty (no changes): return the existing watermark
          unchanged (do not regress the watermark).
        - Must NOT make API calls; derive watermark from extraction_result or
          module-level state set during _extract_entity.
        - Must return None only if the entity does not support watermarking
          (triggers full extract on every run — use only for small reference tables).

        Returns: Watermark to store, or None for non-incremental entities.
        """
        ...

    # ────────────────────────────────────────────────────────────
    # PROVIDED BY BASE — do not override
    # ────────────────────────────────────────────────────────────

    def _get_enabled_entities(self) -> List[EntityConfig]:
        """Returns entities where enabled=True from config."""
        return [e for e in self.config.entities if e.enabled]

    def _process_entities(
        self,
        entities: List[EntityConfig],
        auth: AuthContext
    ) -> List[EntityResult]:
        """
        Processes all enabled entities sequentially.

        Applies error threshold from config.features.errorThresholdPercent.
        If the threshold is exceeded, raises ConnectorFatalError to abort.
        """
        results: List[EntityResult] = []
        failure_count = 0

        for entity in entities:
            result = self._process_single_entity(entity, auth)
            results.append(result)
            if result.status == "failed":
                failure_count += 1
                failure_pct = (failure_count / len(entities)) * 100
                if failure_pct > self.config.features.errorThresholdPercent:
                    raise ConnectorFatalError(
                        f"Error threshold exceeded: {failure_count}/{len(entities)} entities failed.",
                        "ERROR_THRESHOLD_EXCEEDED"
                    )

        return results

    def _process_single_entity(
        self,
        entity: EntityConfig,
        auth: AuthContext
    ) -> EntityResult:
        """Processes one entity: extract → schema evolve → write → watermark."""
        import time
        start = time.monotonic()
        try:
            watermark = self._watermark_store.get(entity.logicalName or entity.apiEndpoint or entity.tableName)
            df = self.retry_policy.execute(self._extract_entity, entity, auth, watermark)
            df = self._schema_handler.handle(df, entity, self.spark)
            self._bronze_writer.write(df, entity)
            new_watermark = self._get_new_watermark(entity, auth, df)
            if new_watermark is not None:
                self._watermark_store.upsert(entity, new_watermark)
            duration = time.monotonic() - start
            return EntityResult(
                entity_name=entity.displayName,
                status="success",
                records_ingested=len(df),
                records_failed=0,
                duration_seconds=duration,
                new_watermark=str(new_watermark) if new_watermark else None,
                error_message=None
            )
        except Exception as e:
            duration = time.monotonic() - start
            self._metadata_writer.log_error(entity, e)
            return EntityResult(
                entity_name=entity.displayName,
                status="failed",
                records_ingested=0,
                records_failed=0,
                duration_seconds=duration,
                new_watermark=None,
                error_message=str(e)
            )

    def _validate_config(self) -> None:
        """Validates the loaded config is structurally complete for this module."""
        from agic_fabric_connector.config.config_validator import ConfigValidator
        ConfigValidator.validate(self.config)
```

---

## 3. MODULE CONTRACTS

### 3.1 CRM / Dataverse Connector

**File:** `agic_fabric_connector/modules/crm/crm_connector.py`

```python
class CRMConnector(BaseConnector):
    """
    Dataverse / Dynamics 365 CRM module connector.

    Source: Dataverse Web API (OData v4)
    Change tracking: OData delta tokens (@odata.deltaLink)
    Auth: Service Principal via MSAL
    Bronze schema: bronze_crm
    """

    MODULE_TYPE = "crm"
    BRONZE_SCHEMA = "bronze_crm"

    # Entities supported in Phase 1 (CRM MVP)
    SUPPORTED_ENTITIES = {
        "contact",
        "lead",
        "msdynmkt_marketingform",
        "msdynmkt_marketingemail",
        "msdynmkt_customerjourney"
    }

    def _authenticate(self) -> "CRMAuthContext":
        """
        Authenticates to Dataverse using MSAL client credentials.

        CONTRACT SPECIFICS:
        - Acquires token for scope: {environmentUrl}/.default
        - Token cached for the duration of the run (re-used across entities)
        - Raises AuthenticationError if token acquisition fails after retry
        """
        ...

    def _extract_entity(
        self,
        entity: "CRMEntityConfig",
        auth: "CRMAuthContext",
        watermark: Optional[Watermark]
    ) -> pd.DataFrame:
        """
        Extracts Dataverse entity records using Change Tracking API.

        INCREMENTAL (watermark.type = "delta_token"):
          GET {environmentUrl}/api/data/{apiVersion}/{entity}?$deltatoken={token}
          Follows @odata.nextLink pagination until exhausted.
          Returns DataFrame including deleted records (with @odata.context = "delete").

        FULL EXTRACT (watermark is None):
          GET {environmentUrl}/api/data/{apiVersion}/{entity}
          Adds Prefer: odata.track-changes header to initialize delta tracking.
          Captures first @odata.deltaLink for use as new watermark.
          Paginates via @odata.nextLink.

        DELETED RECORD HANDLING:
          Deleted records in Change Tracking response have only @odata.id + id.
          These are materialized as rows with _operation="delete" and all
          source columns null except the primary key.
        """
        ...

    def _get_new_watermark(
        self,
        entity: "CRMEntityConfig",
        auth: "CRMAuthContext",
        extraction_result: pd.DataFrame
    ) -> Optional[Watermark]:
        """
        Returns the @odata.deltaLink captured during _extract_entity.

        The delta link is captured from the LAST @odata.nextLink response
        that also contains @odata.deltaLink (end of page chain).
        Stored on self during extraction; retrieved here.
        """
        ...
```

#### CRM Phase 1 Entity Catalog

```python
# agic_fabric_connector/modules/crm/entity_catalog.py

CRM_ENTITY_CATALOG = {
    "contact": EntityCatalogEntry(
        logicalName="contact",
        displayName="Contact",
        primaryKey="contactid",
        supportsChangeTracking=True,
        defaultSelectColumns=["contactid", "fullname", "emailaddress1",
                               "telephone1", "statecode", "statuscode",
                               "modifiedon", "createdon", "ownerid"]
    ),
    "lead": EntityCatalogEntry(
        logicalName="lead",
        displayName="Lead",
        primaryKey="leadid",
        supportsChangeTracking=True,
        defaultSelectColumns=["leadid", "fullname", "emailaddress1",
                               "subject", "statecode", "statuscode",
                               "modifiedon", "createdon", "ownerid"]
    ),
    "msdynmkt_marketingform": EntityCatalogEntry(
        logicalName="msdynmkt_marketingform",
        displayName="Marketing Form",
        primaryKey="msdynmkt_marketingformid",
        supportsChangeTracking=True,
        defaultSelectColumns=["msdynmkt_marketingformid", "msdynmkt_name",
                               "statecode", "statuscode", "modifiedon", "createdon"]
    ),
    "msdynmkt_marketingemail": EntityCatalogEntry(
        logicalName="msdynmkt_marketingemail",
        displayName="Marketing Email",
        primaryKey="msdynmkt_marketingemailid",
        supportsChangeTracking=True,
        defaultSelectColumns=["msdynmkt_marketingemailid", "msdynmkt_name",
                               "msdynmkt_subject", "statecode", "statuscode",
                               "modifiedon", "createdon"]
    ),
    "msdynmkt_customerjourney": EntityCatalogEntry(
        logicalName="msdynmkt_customerjourney",
        displayName="Customer Journey",
        primaryKey="msdynmkt_customerjourneyid",
        supportsChangeTracking=True,
        defaultSelectColumns=["msdynmkt_customerjourneyid", "msdynmkt_name",
                               "statecode", "statuscode", "modifiedon", "createdon"]
    )
}
```

---

### 3.2 Business Central Connector

**File:** `agic_fabric_connector/modules/businesscentral/bc_connector.py`

```python
class BusinessCentralConnector(BaseConnector):
    """
    Microsoft Dynamics 365 Business Central module connector.

    Source: BC REST API v2.0 (OData v4)
    Change tracking: lastModifiedDateTime watermark
    Auth: OAuth 2.0 client credentials via MSAL
    Bronze schema: bronze_bc
    """

    MODULE_TYPE = "businesscentral"
    BRONZE_SCHEMA = "bronze_bc"
    BASE_URL_TEMPLATE = (
        "https://api.businesscentral.dynamics.com/v2.0/"
        "{tenantId}/{environment}/api/v{apiVersion}"
    )

    def _authenticate(self) -> "BCAuthContext":
        """
        Acquires token for scope: https://api.businesscentral.dynamics.com/.default
        """
        ...

    def _extract_entity(
        self,
        entity: "BCEntityConfig",
        auth: "BCAuthContext",
        watermark: Optional[Watermark]
    ) -> pd.DataFrame:
        """
        INCREMENTAL (watermark.type = "timestamp"):
          GET .../companies({companyId})/{apiEndpoint}
            ?$filter=lastModifiedDateTime gt {watermark.watermarkValue}
            &$top={batchSize}
            &$orderby=lastModifiedDateTime asc
          Paginates via @odata.nextLink.

        FULL EXTRACT (watermark is None):
          Same endpoint without $filter.
          Captures max(lastModifiedDateTime) from result set as new watermark.

        NOTE: BC OData does not support delta tokens. Watermark is always
              the maximum lastModifiedDateTime seen in the last successful run.
        """
        ...

    def _get_new_watermark(
        self,
        entity: "BCEntityConfig",
        auth: "BCAuthContext",
        extraction_result: pd.DataFrame
    ) -> Optional[Watermark]:
        """
        Returns max(lastModifiedDateTime) from the result DataFrame.
        If DataFrame is empty (no changes since watermark), returns existing watermark.
        """
        ...
```

---

### 3.3 SQL Connector

**File:** `agic_fabric_connector/modules/sql/sql_connector.py`

```python
class SQLConnector(BaseConnector):
    """
    SQL Server / Azure SQL module connector.

    Source: JDBC (Spark native SQL Server driver)
    Change tracking: watermark column (datetime, rowversion, or integer)
    Auth: SQL auth via Fabric Connection OR MSI for Azure SQL
    Bronze schema: bronze_sql
    """

    MODULE_TYPE = "sql"
    BRONZE_SCHEMA = "bronze_sql"

    def _authenticate(self) -> "SQLAuthContext":
        """
        Resolves JDBC connection string from:
        - Fabric Connection (preferred): retrieves username + password from Fabric
        - Key Vault reference: resolves username/password from Key Vault secrets
        - MSI (Azure SQL only): uses Spark notebook MSI identity (no secret needed)

        Returns SQLAuthContext with jdbc_url and properties dict ready for Spark.
        """
        ...

    def _extract_entity(
        self,
        entity: "SQLEntityConfig",
        auth: "SQLAuthContext",
        watermark: Optional[Watermark]
    ) -> pd.DataFrame:
        """
        Uses Spark JDBC reader with pushdown predicate for incremental extraction.

        INCREMENTAL:
          SELECT {columns} FROM [{schema}].[{tableName}]
          WHERE {watermarkColumn} > {watermark.watermarkValue}
          [AND {entity.whereClause}]
          ORDER BY {watermarkColumn} ASC

        FULL EXTRACT:
          SELECT {columns} FROM [{schema}].[{tableName}]
          [WHERE {entity.whereClause}]

        Uses spark.read.jdbc() with:
          - fetchsize = entity.fetchSize
          - numPartitions based on watermark range (for parallelism on large tables)
          - lowerBound / upperBound for partition pushdown on integer/rowversion columns
        """
        ...

    def _get_new_watermark(
        self,
        entity: "SQLEntityConfig",
        auth: "SQLAuthContext",
        extraction_result: pd.DataFrame
    ) -> Optional[Watermark]:
        """
        For watermark_type = "datetime":  max(watermarkColumn) from result.
        For watermark_type = "rowversion": max(watermarkColumn) as hex string.
        For watermark_type = "integer":   max(watermarkColumn) as string.
        If result is empty: return existing watermark (no regression).
        If extractionMode = "full": return None (no watermark for full-extract entities).
        """
        ...
```

---

## 4. WATERMARK MODEL

The `Watermark` type captures the incremental extraction state for a single entity. The `WatermarkStore` manages persistence to `_entity_watermarks`.

### Watermark Types

```python
from dataclasses import dataclass
from typing import Optional, Literal
from enum import Enum


class WatermarkType(str, Enum):
    DELTA_TOKEN = "delta_token"    # CRM: OData @odata.deltaLink
    TIMESTAMP   = "timestamp"      # BC / SQL datetime column
    ROWVERSION  = "rowversion"     # SQL ROWVERSION or integer monotonic column


@dataclass
class Watermark:
    """
    Represents the incremental extraction boundary for one entity.

    For DELTA_TOKEN:   delta_token is set; watermark_value is None.
    For TIMESTAMP:     watermark_value is ISO 8601 string; delta_token is None.
    For ROWVERSION:    watermark_value is numeric string (decimal or hex); delta_token is None.
    """
    watermark_type: WatermarkType
    delta_token: Optional[str]          # Only for DELTA_TOKEN type
    watermark_value: Optional[str]      # Only for TIMESTAMP / ROWVERSION types
    watermark_column: Optional[str]     # Source column name (for TIMESTAMP / ROWVERSION)

    def is_initial_load(self) -> bool:
        """True if no watermark is set — triggers full extract."""
        return self.delta_token is None and self.watermark_value is None

    def to_filter_value(self) -> str:
        """Returns the value to embed in a filter predicate."""
        if self.watermark_type == WatermarkType.DELTA_TOKEN:
            return self.delta_token or ""
        return self.watermark_value or ""
```

### WatermarkStore Interface

```python
class WatermarkStore:
    """
    Reads and writes entity watermarks to/from the _entity_watermarks Delta table.
    """

    def get(self, entity_name: str) -> Optional[Watermark]:
        """
        Returns the current watermark for the entity, or None if no watermark exists.
        None triggers a full extract (initial load) for this entity.
        """
        ...

    def upsert(self, entity: EntityConfig, watermark: Watermark) -> None:
        """
        Persists the new watermark after a successful entity extraction and Bronze write.

        CONTRACT:
        - Must be called ONLY after both extraction AND write succeed.
        - Uses MERGE INTO to upsert the single row for (connector_id, entity_name).
        - Must be idempotent — repeated calls with the same watermark are safe.
        """
        ...

    def reset(self, entity_name: str) -> None:
        """
        Deletes the watermark row for the entity.
        Triggers a full extract on the next run.
        Called when the user clicks "Reset Watermark" in the entity-detail view.
        """
        ...
```

### Watermark Invariants

```
1. Watermarks are advanced ONLY after a successful Bronze write.
   A partial write (write fails mid-batch) must NOT advance the watermark.

2. An empty extraction result (0 rows, no changes) must NOT regress the watermark.
   The existing watermark is retained unchanged.

3. For CRM delta tokens: the token is opaque — never parse, modify, or construct it.
   Pass it verbatim to the next API call.

4. For BC/SQL timestamps: the watermark comparison uses ">" (strictly greater than)
   to avoid re-extracting the boundary record on the next run.

5. Watermark reset deletes the row from _entity_watermarks.
   The absence of a row is the canonical "initial load" signal — not a null column value.
```

---

## 5. AUTHCONTEXT TYPES

`AuthContext` is a sealed union type. Module connectors return their specific subtype from `_authenticate()`. The base class treats it as opaque and passes it to `_extract_entity()` and `_get_new_watermark()`.

```python
from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class CRMAuthContext:
    """Resolved Dataverse authentication state."""
    access_token: str          # Bearer token for Dataverse API calls
    environment_url: str       # Dataverse environment root URL
    token_expiry_utc: float    # Unix timestamp — refresh before expiry


@dataclass(frozen=True)
class BCAuthContext:
    """Resolved Business Central authentication state."""
    access_token: str          # Bearer token for BC API calls
    base_url: str              # Constructed BC API base URL for this tenant+env
    token_expiry_utc: float


@dataclass(frozen=True)
class SQLAuthContext:
    """Resolved SQL Server authentication state."""
    jdbc_url: str              # Full JDBC connection URL
    jdbc_properties: dict      # Spark JDBC properties dict (user, password, driver, etc.)
    # NOTE: password in jdbc_properties is resolved at auth time from Fabric Connection
    # or Key Vault. Never stored in item definition or logs.


# Union type for type annotations in the base class
AuthContext = Union[CRMAuthContext, BCAuthContext, SQLAuthContext]
```

### Authentication Contract

```
INVARIANT: No raw credential value (password, client secret, API key) may appear in:
  - Item definition (config-schema.json payload)
  - Log output (_error_log.error_message, _connector_runs.error_message)
  - Notebook code or notebook parameters
  - Stack traces

Credential references (connection IDs, Key Vault secret names) are permitted in item definitions.
The actual secret values are resolved at runtime by auth resolvers and exist only in memory.
```

---

## 6. BRONZEWRITER INTERFACE

`BronzeWriter` is provided by the base class and handles all Delta Lake writes. Module connectors must NOT write to Bronze directly.

```python
class BronzeWriter:
    """
    Writes a pandas DataFrame to a Bronze Delta table.
    Applies standard ISV metadata columns and enforces partition scheme.
    """

    def write(self, df: pd.DataFrame, entity: EntityConfig) -> int:
        """
        Writes the DataFrame to the appropriate Bronze Delta table.

        CONTRACT:
        - Converts pd.DataFrame to Spark DataFrame.
        - Appends ISV metadata columns (_run_id, _connector_id, etc.).
        - Validates no source column name starts with '_'.
        - Sets _ingestion_utc = current_timestamp(), _ingestion_date = date().
        - Writes with mode="append", partitionBy="_ingestion_date".
        - Applies mergeSchema="true" if schemaEvolutionPolicy="merge".
        - Returns the number of rows written.

        Raises:
        - BronzeWriteError if the write fails.
        - SchemaConflictError if schemaEvolutionPolicy="strict" and schema changed.
        """
        ...

    def _build_table_name(self, entity: EntityConfig) -> str:
        """
        Returns the fully qualified Delta table name for this entity.
        CRM:  bronze_crm.{entity.logicalName}
        BC:   bronze_bc.{entity.apiEndpoint}
        SQL:  bronze_sql.{entity.schema}_{entity.tableName} (normalized)
        """
        ...

    def _add_metadata_columns(
        self,
        spark_df,
        run_id: str,
        entity: EntityConfig
    ):
        """
        Adds the 12 ISV metadata columns to the Spark DataFrame.
        Column order: source columns first, then _-prefixed metadata columns.
        """
        from pyspark.sql import functions as F
        return spark_df \
            .withColumn("_run_id", F.lit(run_id)) \
            .withColumn("_connector_id", F.lit(self.config.runtime.connectorId)) \
            .withColumn("_module_type", F.lit(self.config.moduleType)) \
            .withColumn("_entity_name", F.lit(entity.displayName)) \
            .withColumn("_operation", F.lit(entity._operation or "insert")) \
            .withColumn("_is_current", F.lit(True)) \
            .withColumn("_ingestion_utc", F.current_timestamp()) \
            .withColumn("_ingestion_date", F.current_date()) \
            .withColumn("_source_modified_utc", F.col(entity.sourceModifiedColumn) if entity.sourceModifiedColumn else F.lit(None)) \
            .withColumn("_source_row_version", F.col(entity.etagColumn) if entity.etagColumn else F.lit(None)) \
            .withColumn("_schema_version", F.lit(self.config.source.apiVersion or "")) \
            .withColumn("_wheel_version", F.lit(WHEEL_VERSION))
```

---

## 7. CONFIGLOADER INTERFACE

`ConfigLoader` deserializes and validates the item definition from the Fabric Items API.

```python
class ConfigLoader:
    """
    Loads and validates the ConnectorItemDefinition from a Fabric item.
    Used as the notebook entry point.
    """

    @staticmethod
    def from_item_definition(
        item_id: str,
        workspace_id: str,
        spark: SparkSession
    ) -> ConnectorItemDefinition:
        """
        Loads config from Fabric Items API using the notebook's built-in token.

        Steps:
        1. Acquire Fabric token via mssparkutils.credentials.getToken()
        2. GET /v1/workspaces/{workspaceId}/items/{itemId}/definitions/files/payload.json
        3. Base64-decode the response content
        4. JSON-parse the decoded content
        5. Validate against config-schema.json (version check + structural validation)
        6. Deserialize into ConnectorItemDefinition dataclass
        7. Return validated config object

        Raises:
        - ConfigLoadError if the API call fails
        - ConfigValidationError if the schema version is unknown or config is invalid
        - ConnectorFatalError if state != "configured" (notebook ran before activation)
        """
        ...

    @staticmethod
    def validate(config: ConnectorItemDefinition) -> None:
        """
        Validates a config object for structural completeness.
        Called by BaseConnector._validate_config() at run start.

        Checks:
        - schemaVersion is known (current: "1.0.0")
        - state == "configured"
        - authentication.mode is set and has required fields
        - At least one entity is enabled
        - runtime.notebookItemId is set
        - runtime.bronzeLakeHouseId is set
        - Module-specific required fields present (e.g. environmentUrl for CRM)
        """
        ...
```

---

## 8. SCHEMAEVOLUTIONHANDLER INTERFACE

```python
class SchemaEvolutionHandler:
    """
    Enforces the configured schema evolution policy when a source schema change
    is detected relative to the existing Bronze Delta table.
    """

    def __init__(self, policy: SchemaEvolutionPolicy):
        self.policy = policy

    def handle(
        self,
        df: pd.DataFrame,
        entity: EntityConfig,
        spark: SparkSession
    ) -> pd.DataFrame:
        """
        Checks for schema changes and applies the policy.

        For MERGE policy:
          - New columns in df: allowed (Delta mergeSchema=true handles it)
          - Removed columns: kept in Delta as null — no action needed
          - Type conflicts: attempt widening; log as schema change event
          - Returns df unchanged

        For STRICT policy:
          - Any column added, removed, or type-changed: raises SchemaConflictError
          - Aborts the run immediately (propagates to ConnectorFatalError)

        For OVERWRITE policy:
          - Drops the existing Delta table and recreates with new schema
          - Logs the overwrite event as a schema_evolution_log entry
          - Returns df unchanged (write will use mode="overwrite")

        In all cases: writes schema change events to _schema_evolution_log.
        Returns the (possibly modified) DataFrame to pass to BronzeWriter.
        """
        ...
```

---

## 9. RETRYPOLICY INTERFACE

```python
from typing import Callable, TypeVar, Any
import time

T = TypeVar("T")


class RetryPolicy:
    """
    Configurable retry with exponential backoff.
    Applied to _authenticate() and _extract_entity() calls.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        initial_backoff_seconds: float = 5.0,
        backoff_multiplier: float = 2.0,
        max_backoff_seconds: float = 300.0,
        respect_retry_after_header: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_backoff_seconds = initial_backoff_seconds
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff_seconds = max_backoff_seconds
        self.respect_retry_after_header = respect_retry_after_header

    def execute(self, fn: Callable[..., T], *args, **kwargs) -> T:
        """
        Executes fn with retry on transient errors.

        Retries on: ThrottlingError, TransientError, AuthenticationError
        Does NOT retry on: ConnectorFatalError, EntityExtractionError (logic errors)

        For ThrottlingError with a Retry-After value:
          - If respect_retry_after_header = True: sleep for Retry-After duration
          - Retry-After takes precedence over calculated backoff
        """
        last_error = None
        for attempt in range(self.max_attempts):
            try:
                return fn(*args, **kwargs)
            except (ThrottlingError, TransientError, AuthenticationError) as e:
                last_error = e
                wait = self._calculate_wait(e, attempt)
                time.sleep(wait)
            except (ConnectorFatalError, EntityExtractionError):
                raise  # non-retryable — propagate immediately
        raise ConnectorFatalError(
            f"Max retry attempts ({self.max_attempts}) exhausted: {last_error}",
            "MAX_RETRIES_EXCEEDED"
        )

    def _calculate_wait(self, error: Exception, attempt: int) -> float:
        if isinstance(error, ThrottlingError) and self.respect_retry_after_header:
            retry_after = getattr(error, "retry_after_seconds", None)
            if retry_after:
                return min(retry_after, self.max_backoff_seconds)
        backoff = self.initial_backoff_seconds * (self.backoff_multiplier ** attempt)
        return min(backoff, self.max_backoff_seconds)
```

---

## 10. ERROR TAXONOMY

All errors produced by the runtime are classified using this taxonomy. Error codes appear in `_connector_runs.error_code` and `_error_log.error_type`.

### Error Classes

```python
class ConnectorError(Exception):
    """Base class for all connector errors."""
    error_code: str = "UNKNOWN_ERROR"


class ConnectorFatalError(ConnectorError):
    """
    Non-recoverable error. Aborts the entire run.
    Examples: invalid config, auth failure after retries, error threshold exceeded.
    """
    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.error_code = error_code


class AuthenticationError(ConnectorError):
    """
    Authentication failed. Retryable.
    Examples: token endpoint unreachable, token expired mid-run.
    Not raised for invalid credentials (those are ConnectorFatalError).
    """
    error_code = "AUTH_ERROR"


class ThrottlingError(ConnectorError):
    """
    Source system is throttling requests. Retryable with Retry-After.
    Examples: Dataverse HTTP 429, BC HTTP 429.
    """
    error_code = "THROTTLING_ERROR"
    def __init__(self, message: str, retry_after_seconds: Optional[float] = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class TransientError(ConnectorError):
    """
    Transient network or service error. Retryable.
    Examples: HTTP 503, connection timeout, DNS failure.
    """
    error_code = "TRANSIENT_ERROR"


class EntityExtractionError(ConnectorError):
    """
    Logic error during entity extraction. Not retryable. Stops this entity.
    Examples: invalid OData query, entity not found, Change Tracking not enabled.
    """
    error_code = "EXTRACTION_ERROR"


class BronzeWriteError(ConnectorError):
    """
    Delta Lake write failure. Not retryable (Spark handles its own retry).
    Examples: OneLake quota exceeded, ABFS auth error.
    """
    error_code = "BRONZE_WRITE_ERROR"


class SchemaConflictError(ConnectorError):
    """
    Schema evolution conflict under 'strict' policy. Not retryable.
    Aborts the run when raised.
    """
    error_code = "SCHEMA_CONFLICT_ERROR"


class ConfigValidationError(ConnectorError):
    """
    Item definition config is invalid or incomplete.
    Examples: missing environmentUrl, unknown moduleType, state != "configured".
    """
    error_code = "CONFIG_VALIDATION_ERROR"


class ConfigLoadError(ConnectorError):
    """
    Failed to load item definition from Fabric Items API.
    Examples: item not found, insufficient permissions.
    """
    error_code = "CONFIG_LOAD_ERROR"
```

### Error Code Reference Table

| Error Code | Class | Retryable | Run Impact |
|---|---|---|---|
| `AUTH_ERROR` | `AuthenticationError` | Yes (3 attempts) | Aborts run if all retries fail |
| `THROTTLING_ERROR` | `ThrottlingError` | Yes (respects Retry-After) | Per-entity retry |
| `TRANSIENT_ERROR` | `TransientError` | Yes (3 attempts) | Per-entity retry |
| `EXTRACTION_ERROR` | `EntityExtractionError` | No | Fails entity; run continues if below threshold |
| `BRONZE_WRITE_ERROR` | `BronzeWriteError` | No | Fails entity; watermark NOT advanced |
| `SCHEMA_CONFLICT_ERROR` | `SchemaConflictError` | No | Fails entity (strict) or run (overwrite) |
| `CONFIG_VALIDATION_ERROR` | `ConfigValidationError` | No | Aborts run immediately |
| `CONFIG_LOAD_ERROR` | `ConfigLoadError` | No | Aborts run immediately |
| `ERROR_THRESHOLD_EXCEEDED` | `ConnectorFatalError` | No | Aborts run |
| `MAX_RETRIES_EXCEEDED` | `ConnectorFatalError` | No | Aborts run |
| `UNEXPECTED_ERROR` | `ConnectorFatalError` | No | Aborts run |

---

## 11. RUN LIFECYCLE STATE MACHINE

```
                          ┌─────────────────────┐
                          │     RUN STARTED       │
                          │  status = "running"   │
                          │  Row written to        │
                          │  _connector_runs       │
                          └──────────┬────────────┘
                                     │
                           ┌─────────▼──────────┐
                           │  _validate_config() │
                           └─────────┬──────────┘
                                     │
                        ┌────────────▼─────────────┐
                        │  _authenticate()          │
                        │  (with retry)             │
                        └────────────┬─────────────┘
                                     │
                   ┌─────────────────▼──────────────────┐
                   │  For each enabled entity:           │
                   │    - get watermark                  │
                   │    - _extract_entity() (with retry) │
                   │    - _schema_handler.handle()       │
                   │    - _bronze_writer.write()         │
                   │    - _get_new_watermark()           │
                   │    - watermark_store.upsert()       │
                   └─────────────────┬──────────────────┘
                                     │
                     ┌───────────────┴──────────────┐
                     │                              │
               ┌─────▼──────┐              ┌───────▼───────┐
               │  All pass  │              │  Some failed  │
               └─────┬──────┘              └───────┬───────┘
                     │                             │
                     │                   ┌─────────▼──────────┐
                     │                   │  > errorThreshold? │
                     │                   └─────────┬──────────┘
                     │                        ┌────┴────┐
                     │                       Yes        No
                     │                        │         │
                     │               ┌────────▼──┐  ┌───▼──────────────┐
                     │               │  ABORTED  │  │  PARTIAL_SUCCESS │
                     │               │  status=  │  │  status=         │
                     │               │  "failed" │  │  "partial_success│
                     │               └───────────┘  └──────────────────┘
                     │
              ┌──────▼──────────┐
              │    SUCCESS      │
              │  status=        │
              │  "success"      │
              └─────────────────┘

  All terminal states update the _connector_runs row via MERGE INTO.
  All terminal states write the run_end_utc and duration_seconds.
```

---

## 12. CONNECTOR REGISTRATION CONTRACT (TYPESCRIPT)

The TypeScript side must define a module registry that maps `moduleType` to the correct display name, icon, entity catalog, and wizard configuration. This registry is used by the wizard steps.

```typescript
// Located in: Workload/app/items/ConnectorItem/ConnectorItemDefinition.ts

export type ModuleType = "crm" | "businesscentral" | "sql";
export type ConnectorState = "empty" | "configured" | "error" | "paused";
export type SchemaEvolutionPolicy = "merge" | "strict" | "overwrite";
export type AuthMode = "fabric_connection" | "keyvault_reference" | "service_principal";
export type ExtractionMode = "incremental" | "full";

// ── Source configurations ──────────────────────────────────────

export interface CrmSourceConfiguration {
  environmentUrl: string;
  tenantId: string;
  apiVersion?: string;
  enableChangeTracking?: boolean;
  pageSize?: number;
}

export interface BusinessCentralSourceConfiguration {
  tenantId: string;
  environment: string;
  companyId?: string;
  apiVersion?: string;
  pageSize?: number;
}

export interface SqlSourceConfiguration {
  server: string;
  database: string;
  port?: number;
  driver?: "sqlserver" | "azuresql";
  encrypt?: boolean;
  trustServerCertificate?: boolean;
}

// ── Authentication ─────────────────────────────────────────────

export interface FabricConnectionAuth {
  mode: "fabric_connection";
  fabricConnectionId: string;
}

export interface KeyVaultReferenceAuth {
  mode: "keyvault_reference";
  keyVaultUri: string;
  clientIdSecretName?: string;
  clientSecretName: string;
  tenantIdSecretName?: string;
}

export interface ServicePrincipalAuth {
  mode: "service_principal";
  tenantId: string;
  clientId: string;
  secretRef: FabricConnectionAuth | KeyVaultReferenceAuth;
}

export type AuthConfiguration = FabricConnectionAuth | KeyVaultReferenceAuth | ServicePrincipalAuth;

// ── Entity configurations ──────────────────────────────────────

export interface CrmEntityConfiguration {
  logicalName: string;
  displayName: string;
  enabled: boolean;
  extractionMode?: ExtractionMode;
  selectColumns?: string[];
  expandRelationships?: string[];
  filterExpression?: string;
  batchSize?: number;
}

export interface BusinessCentralEntityConfiguration {
  apiEndpoint: string;
  displayName: string;
  enabled: boolean;
  extractionMode?: ExtractionMode;
  watermarkColumn?: string;
  selectColumns?: string[];
  filterExpression?: string;
  batchSize?: number;
}

export interface SqlEntityConfiguration {
  schema: string;
  tableName: string;
  displayName: string;
  enabled: boolean;
  extractionMode?: ExtractionMode;
  watermarkColumn?: string;
  watermarkColumnType?: "datetime" | "rowversion" | "integer";
  selectColumns?: string[];
  whereClause?: string;
  primaryKeys?: string[];
  fetchSize?: number;
}

// ── Top-level definition (discriminated union by moduleType) ───

interface ConnectorItemDefinitionBase {
  schemaVersion: "1.0.0";
  state: ConnectorState;
  authentication?: AuthConfiguration;
  storage?: StorageConfiguration;
  scheduling?: SchedulingConfiguration;
  features?: FeaturesConfiguration;
  runtime?: RuntimeConfiguration;
  metadata?: ConnectorMetadata;
}

export interface CrmConnectorItemDefinition extends ConnectorItemDefinitionBase {
  moduleType: "crm";
  source: CrmSourceConfiguration;
  entities: CrmEntityConfiguration[];
}

export interface BusinessCentralConnectorItemDefinition extends ConnectorItemDefinitionBase {
  moduleType: "businesscentral";
  source: BusinessCentralSourceConfiguration;
  entities: BusinessCentralEntityConfiguration[];
}

export interface SqlConnectorItemDefinition extends ConnectorItemDefinitionBase {
  moduleType: "sql";
  source: SqlSourceConfiguration;
  entities: SqlEntityConfiguration[];
}

export type ConnectorItemDefinition =
  | CrmConnectorItemDefinition
  | BusinessCentralConnectorItemDefinition
  | SqlConnectorItemDefinition;

// ── Storage, Schedule, Features, Runtime, Metadata ────────────

export interface StorageConfiguration {
  bronzeLakeHouseId?: string;
  bronzeLakeHouseName: string;
  schemaEvolutionPolicy?: SchemaEvolutionPolicy;
  retentionDays?: number;
  useExistingLakehouse?: boolean;
}

export interface SchedulingConfiguration {
  scheduleType: "cron" | "interval";
  cronExpression?: string;
  intervalMinutes?: number;
  timezone?: string;
  enabled: boolean;
  startDate?: string;
}

export interface FeaturesConfiguration {
  schemaEvolutionHandling?: SchemaEvolutionPolicy;
  errorThresholdPercent?: number;
  enablePartialRun?: boolean;
  enableTelemetry?: boolean;
  maxRecordsPerEntityPerRun?: number;
  enableDeltaLakeOptimize?: boolean;
}

export interface RuntimeConfiguration {
  notebookItemId?: string;
  bronzeLakeHouseId?: string;
  deployedAt?: string;
  wheelVersion?: string;
  configSchemaVersion?: string;
  jobScheduleId?: string;
}

export interface ConnectorMetadata {
  displayName?: string;
  description?: string;
  tags?: string[];
  createdAt?: string;
  updatedAt?: string;
  activatedAt?: string;
}

// ── Type guard helpers ─────────────────────────────────────────

export function isCrmConnector(def: ConnectorItemDefinition): def is CrmConnectorItemDefinition {
  return def.moduleType === "crm";
}

export function isBusinessCentralConnector(def: ConnectorItemDefinition): def is BusinessCentralConnectorItemDefinition {
  return def.moduleType === "businesscentral";
}

export function isSqlConnector(def: ConnectorItemDefinition): def is SqlConnectorItemDefinition {
  return def.moduleType === "sql";
}

// ── Empty state factory ────────────────────────────────────────

export function createEmptyDefinition(): Pick<ConnectorItemDefinitionBase, "schemaVersion" | "state"> {
  return {
    schemaVersion: "1.0.0",
    state: "empty"
  };
}
```

---

## 13. NOTEBOOK DEPLOYMENT CONTRACT

The Activate handler deploys a notebook template to the customer workspace. The deployed notebook must conform to this contract.

### Notebook Template Structure

Each module has a static template file in `connector/runtime/notebooks/`:

```
connector/runtime/notebooks/
├── connector_runtime_crm.ipynb      ← CRM module notebook
├── connector_runtime_bc.ipynb       ← Business Central notebook
└── connector_runtime_sql.ipynb      ← SQL module notebook
```

### Notebook Content Contract

```python
# Cell 1 — Package installation (executed on each run)
# IMPORTANT: Version is pinned at notebook deploy time, replaced by Activate handler
%pip install agic-fabric-connector==%%WHEEL_VERSION%%

# Cell 2 — Imports and configuration load
from agic_fabric_connector.config.config_loader import ConfigLoader
from agic_fabric_connector.modules.crm import CRMConnector   # module-specific

# IDs injected at deploy time by NotebookDeploymentController
CONNECTOR_ITEM_ID = "%%CONNECTOR_ITEM_ID%%"
WORKSPACE_ID      = "%%WORKSPACE_ID%%"

config = ConfigLoader.from_item_definition(
    item_id=CONNECTOR_ITEM_ID,
    workspace_id=WORKSPACE_ID,
    spark=spark
)

# Cell 3 — Execution
connector = CRMConnector(config, spark)    # module-specific
result = connector.run()

print(f"Run complete: {result.status} | "
      f"Entities: {len(result.entity_results)} | "
      f"Records: {sum(r.records_ingested for r in result.entity_results)}")
```

### Deployment Contract (TypeScript)

```typescript
// Located in: Workload/app/controller/NotebookDeploymentController.ts

export interface NotebookDeploymentParams {
  workspaceId: string;
  connectorItemId: string;
  moduleType: ModuleType;
  wheelVersion: string;
}

export interface NotebookDeploymentResult {
  notebookItemId: string;
  deployedAt: string;     // ISO 8601
  wheelVersion: string;
}

export async function deployConnectorNotebook(
  workloadClient: WorkloadClientAPI,
  params: NotebookDeploymentParams
): Promise<NotebookDeploymentResult>;
```

### Notebook Name Convention

| Module | Notebook display name |
|---|---|
| `crm` | `FUC-CRM-Runtime-{connectorItemId}` |
| `businesscentral` | `FUC-BC-Runtime-{connectorItemId}` |
| `sql` | `FUC-SQL-Runtime-{connectorItemId}` |

The `connectorItemId` suffix ensures uniqueness when multiple ConnectorItems of the same module type exist in the same workspace.

### Placeholder Replacement

The Activate handler performs exact string replacement of template placeholders before deploying:

| Placeholder | Replaced with |
|---|---|
| `%%WHEEL_VERSION%%` | Current wheel version from `CURRENT_WHEEL_VERSION` constant |
| `%%CONNECTOR_ITEM_ID%%` | Fabric item ID of the ConnectorItem being activated |
| `%%WORKSPACE_ID%%` | Fabric workspace ID from item context |

The replacement must be exact string match (not regex) and must not alter any other content of the notebook JSON.
