# PHASE 3 — METADATA MODEL

**Project:** Fabric Universal Connector  
**Author:** Principal Architect Review  
**Date:** 2026-05-14  
**Input:** `.ai/architecture/target-architecture.md`  
**Status:** COMPLETE — Awaiting Phase 4 instruction

---

## TABLE OF CONTENTS

1. Model Overview
2. Bronze Data Table — Standard Metadata Columns
3. Metadata Table: `_connector_runs`
4. Metadata Table: `_entity_watermarks`
5. Metadata Table: `_schema_evolution_log`
6. Metadata Table: `_error_log`
7. Schema Namespace Conventions
8. TypeScript Type Definitions
9. Python Dataclass Definitions
10. Lifecycle and Access Patterns

---

## 1. MODEL OVERVIEW

The metadata model defines all Delta Lake table schemas that are managed by the `agic-fabric-connector` Python wheel. These tables serve two purposes:

1. **Bronze data tables** — carry ISV-defined metadata columns (`_`-prefixed) alongside all raw source columns, enabling lineage, deduplication, and operational queries without modifying source data.
2. **Metadata control tables** — stored under `_meta/` within each module schema; support dashboard monitoring, watermark tracking, schema evolution auditing, and error analysis.

### Storage Layout

```
Bronze Lakehouse: FabricUniversalConnector-Bronze
│
├── bronze_crm/
│   ├── contact                    ← Bronze data table (CRM entity)
│   ├── lead                       ← Bronze data table (CRM entity)
│   ├── msdynmkt_marketingform     ← Bronze data table (CRM entity)
│   ├── msdynmkt_marketingemail    ← Bronze data table (CRM entity)
│   ├── msdynmkt_customerjourney   ← Bronze data table (CRM entity)
│   └── _meta/
│       ├── _connector_runs        ← Run execution log
│       ├── _entity_watermarks     ← Per-entity change tracking state
│       ├── _schema_evolution_log  ← Schema change audit log
│       └── _error_log             ← Per-record and per-entity error log
│
├── bronze_bc/
│   ├── customers                  ← Bronze data table (BC entity)
│   └── _meta/
│       ├── _connector_runs
│       ├── _entity_watermarks
│       ├── _schema_evolution_log
│       └── _error_log
│
└── bronze_sql/
    ├── {schema}_{tableName}       ← Bronze data table (SQL table, normalized name)
    └── _meta/
        ├── _connector_runs
        ├── _entity_watermarks
        ├── _schema_evolution_log
        └── _error_log
```

**One set of `_meta/` tables per module schema.** A single customer workspace running all three modules produces three independent sets of metadata tables, one per module.

**Multiple connectors, one schema.** If a customer creates two ConnectorItems of the same module type (e.g., two CRM connectors to different environments), both write to the same `bronze_crm` schema. The `connector_id` column in all metadata tables distinguishes rows per connector instance.

---

## 2. BRONZE DATA TABLE — STANDARD METADATA COLUMNS

Every Bronze data table contains all raw source columns followed by these ISV-defined metadata columns. Source column names are preserved verbatim from the source API response. Metadata columns always use the `_` prefix to avoid collisions.

### Column Definitions

| Column Name | Delta Type | Nullable | Description |
|---|---|---|---|
| `_run_id` | `STRING` | NOT NULL | UUID of the ingestion run that wrote this row. Foreign key to `_connector_runs.run_id`. |
| `_connector_id` | `STRING` | NOT NULL | Fabric item ID (UUID) of the ConnectorItem that produced this row. |
| `_module_type` | `STRING` | NOT NULL | Module identifier: `"crm"`, `"businesscentral"`, or `"sql"`. |
| `_entity_name` | `STRING` | NOT NULL | Logical entity name as defined in the connector config (e.g. `"contact"`, `"customers"`). |
| `_operation` | `STRING` | NOT NULL | Change operation: `"insert"`, `"update"`, `"delete"`. For full-extract tables always `"insert"`. |
| `_is_current` | `BOOLEAN` | NOT NULL | `true` if this row represents the latest known state of the source record. Set to `false` for historical rows superseded by a newer extraction of the same record. Set by the Bronze writer at write time. |
| `_ingestion_utc` | `TIMESTAMP` | NOT NULL | UTC timestamp when this row was written to Bronze. Used for operational queries ("what was ingested today"). |
| `_ingestion_date` | `DATE` | NOT NULL | Date portion of `_ingestion_utc`. **Partition key** for all Bronze data tables. Derived column — do not set independently. |
| `_source_modified_utc` | `TIMESTAMP` | NULLABLE | UTC timestamp of when the source record was last modified, as reported by the source API. May be null if the source does not provide this field. |
| `_source_row_version` | `STRING` | NULLABLE | ETag, `@odata.etag`, `rowversion`, or equivalent concurrency token from the source. Used to detect duplicate extractions. |
| `_schema_version` | `STRING` | NULLABLE | Source-side schema version or API version active at ingestion time. Supports schema evolution auditing. |
| `_wheel_version` | `STRING` | NOT NULL | `agic-fabric-connector` package version that produced this row. Enables auditing and regression analysis across wheel versions. |

### Constraints and Invariants

- `_ingestion_date` is always derived from `_ingestion_utc` — they are never set independently
- `_operation = "delete"` rows contain the source record's primary key columns only; all other source columns are null (Dataverse Change Tracking behavior)
- `_is_current` is computed by the Bronze writer at append time using the source record ID and `_ingestion_utc`; it is not guaranteed to be accurate across concurrent runs
- The `_` prefix namespace is reserved exclusively for ISV metadata columns; no source column may begin with `_`

### Partitioning

```python
df.write \
    .format("delta") \
    .partitionBy("_ingestion_date") \
    .option("mergeSchema", "true") \
    .mode("append") \
    .saveAsTable(f"{schema}.{table_name}")
```

Partition by ingestion date (not source modification date) because:
- Source modification dates are unreliable, historical, or absent for some sources
- "What was ingested today/this week" is the dominant operational access pattern
- Retention policies are cleanly expressible as date ranges

---

## 3. METADATA TABLE: `_connector_runs`

One row is written per ingestion run, at run completion. This is the primary source of truth for the dashboard run history view and for operational SLA monitoring.

**Table path:** `{schema}._meta._connector_runs`

### Schema

| Column | Delta Type | Nullable | Description |
|---|---|---|---|
| `run_id` | `STRING` | NOT NULL | UUID generated at run start. Primary identifier. |
| `connector_id` | `STRING` | NOT NULL | Fabric item ID of the ConnectorItem that triggered this run. |
| `module_type` | `STRING` | NOT NULL | `"crm"`, `"businesscentral"`, or `"sql"`. |
| `run_start_utc` | `TIMESTAMP` | NOT NULL | UTC timestamp when the notebook began execution. |
| `run_end_utc` | `TIMESTAMP` | NULLABLE | UTC timestamp when the run completed or failed. Null if the run is still in progress. |
| `duration_seconds` | `INTEGER` | NULLABLE | Computed: `run_end_utc - run_start_utc` in seconds. |
| `status` | `STRING` | NOT NULL | Run outcome: `"running"`, `"success"`, `"partial_success"`, `"failed"`, `"cancelled"`. |
| `triggered_by` | `STRING` | NOT NULL | How the run was initiated: `"schedule"`, `"on_demand"`, `"activation"`. |
| `entities_enabled` | `INTEGER` | NOT NULL | Number of entities enabled in the config at run time. |
| `entities_processed` | `INTEGER` | NOT NULL | Number of entities actually attempted. |
| `entities_succeeded` | `INTEGER` | NOT NULL | Number of entities that completed without error. |
| `entities_failed` | `INTEGER` | NOT NULL | Number of entities that failed (partial or total failure). |
| `records_ingested` | `LONG` | NOT NULL | Total rows written to Bronze across all entities in this run. |
| `records_failed` | `LONG` | NOT NULL | Total rows that could not be written (parse errors, write failures). |
| `error_message` | `STRING` | NULLABLE | Top-level error message if `status = "failed"`. Null for success. |
| `error_code` | `STRING` | NULLABLE | Structured error code (see §Error Taxonomy in ingestion-contracts.md). |
| `entity_results` | `STRING` | NOT NULL | JSON array of per-entity result summaries (see EntityRunResult structure below). Stored as serialized JSON string for Delta compatibility. |
| `wheel_version` | `STRING` | NOT NULL | Python wheel version used for this run. |
| `config_schema_version` | `STRING` | NOT NULL | JSON Schema version of the item definition at run time. |
| `notebook_item_id` | `STRING` | NULLABLE | Fabric Notebook item ID that executed this run. |
| `workspace_id` | `STRING` | NOT NULL | Customer Fabric workspace ID. |

### `entity_results` JSON Structure (serialized array)

```json
[
  {
    "entityName": "contact",
    "status": "success",
    "recordsIngested": 4821,
    "recordsFailed": 0,
    "durationSeconds": 34,
    "newWatermark": "W/\"datetime'2026-05-14T09%3A00%3A00Z'\"",
    "errorMessage": null
  },
  {
    "entityName": "lead",
    "status": "failed",
    "recordsIngested": 0,
    "recordsFailed": 0,
    "durationSeconds": 2,
    "newWatermark": null,
    "errorMessage": "Dataverse Change Tracking not enabled on 'lead'"
  }
]
```

### Invariants

- Every run creates exactly one row in `_connector_runs`
- `run_id` is generated by the notebook at `run()` entry, before any entity processing begins
- The row is written in two phases: an initial `"running"` row at start, then updated to final status at completion
- The initial write uses `mode="append"`; the final write uses `MERGE INTO ... WHEN MATCHED UPDATE` on `run_id`
- `status = "partial_success"` when `entities_failed > 0` AND `entities_succeeded > 0`

---

## 4. METADATA TABLE: `_entity_watermarks`

One row per `(connector_id, entity_name)` pair. Upserted after each successful entity extraction. This is the runtime state that enables incremental extraction — the most critical metadata table for correctness.

**Table path:** `{schema}._meta._entity_watermarks`

### Schema

| Column | Delta Type | Nullable | Description |
|---|---|---|---|
| `connector_id` | `STRING` | NOT NULL | Fabric item ID of the ConnectorItem. Part of composite primary key. |
| `entity_name` | `STRING` | NOT NULL | Entity logical name. Part of composite primary key. |
| `module_type` | `STRING` | NOT NULL | `"crm"`, `"businesscentral"`, or `"sql"`. |
| `watermark_type` | `STRING` | NOT NULL | Type of watermark: `"delta_token"` (CRM Change Tracking), `"timestamp"` (BC, SQL datetime), `"rowversion"` (SQL rowversion/integer). |
| `delta_token` | `STRING` | NULLABLE | OData `@odata.deltaLink` or delta token. Set only when `watermark_type = "delta_token"`. |
| `watermark_value` | `STRING` | NULLABLE | ISO 8601 datetime string or numeric string for timestamp/rowversion watermarks. |
| `watermark_column` | `STRING` | NULLABLE | Name of the source column used as watermark (for timestamp/rowversion types). |
| `last_run_id` | `STRING` | NOT NULL | `run_id` of the most recent run that updated this watermark. |
| `last_success_utc` | `TIMESTAMP` | NOT NULL | UTC timestamp of the last successful extraction for this entity. |
| `records_at_last_run` | `LONG` | NOT NULL | Number of records ingested in the last successful run for this entity. |
| `records_at_source_est` | `LONG` | NULLABLE | Estimated total record count at source (if queryable). May be null. |
| `is_initial_load_complete` | `BOOLEAN` | NOT NULL | `false` until the first full or incremental run completes. Enables the UI to show "Initial load in progress" status. |
| `workspace_id` | `STRING` | NOT NULL | Customer Fabric workspace ID. |

### Write Pattern

```python
# Watermark upsert — executed after each successful entity extraction
spark.sql(f"""
MERGE INTO {schema}._meta._entity_watermarks AS target
USING (SELECT
  '{connector_id}' AS connector_id,
  '{entity_name}' AS entity_name,
  '{module_type}' AS module_type,
  '{watermark_type}' AS watermark_type,
  {delta_token_expr} AS delta_token,
  {watermark_value_expr} AS watermark_value,
  '{watermark_column}' AS watermark_column,
  '{run_id}' AS last_run_id,
  current_timestamp() AS last_success_utc,
  {records_ingested} AS records_at_last_run,
  true AS is_initial_load_complete,
  '{workspace_id}' AS workspace_id
) AS source
ON target.connector_id = source.connector_id
AND target.entity_name = source.entity_name
WHEN MATCHED THEN UPDATE SET *
WHEN NOT MATCHED THEN INSERT *
""")
```

### Invariants

- Watermarks are updated only after a fully successful entity write. A failed write must not advance the watermark.
- If a watermark row does not exist for a `(connector_id, entity_name)` pair, the runtime performs a full extract (initial load).
- `delta_token` and `watermark_value` are mutually exclusive per row — only one is populated based on `watermark_type`.
- Watermark reset (user action from entity-detail ribbon) deletes the row for the affected entity, triggering a full re-extract on the next run.

---

## 5. METADATA TABLE: `_schema_evolution_log`

Append-only audit log of detected schema changes. Written by the `SchemaEvolutionHandler` when a column is added, removed, or has its type changed relative to the existing Bronze Delta table schema.

**Table path:** `{schema}._meta._schema_evolution_log`

### Schema

| Column | Delta Type | Nullable | Description |
|---|---|---|---|
| `event_id` | `STRING` | NOT NULL | UUID of this schema change event. |
| `connector_id` | `STRING` | NOT NULL | ConnectorItem that detected the change. |
| `entity_name` | `STRING` | NOT NULL | Entity where the schema change occurred. |
| `run_id` | `STRING` | NOT NULL | Run ID during which the change was detected. |
| `detected_utc` | `TIMESTAMP` | NOT NULL | UTC timestamp when the schema change was detected. |
| `change_type` | `STRING` | NOT NULL | Type of change: `"column_added"`, `"column_removed"`, `"type_changed"`, `"column_renamed_suspected"`. |
| `column_name` | `STRING` | NOT NULL | Name of the affected column. |
| `old_type` | `STRING` | NULLABLE | Previous Delta type. Null for `"column_added"`. |
| `new_type` | `STRING` | NULLABLE | New Delta type. Null for `"column_removed"`. |
| `handled_by` | `STRING` | NOT NULL | How the change was handled: `"merged"`, `"rejected"` (strict), `"overwritten"`, `"ignored"`. |
| `evolution_policy` | `STRING` | NOT NULL | The `schemaEvolutionPolicy` active at the time: `"merge"`, `"strict"`, `"overwrite"`. |
| `run_aborted` | `BOOLEAN` | NOT NULL | `true` if this event caused the run to abort (strict policy). |
| `wheel_version` | `STRING` | NOT NULL | Wheel version that detected and handled this change. |

### Invariants

- Append-only. Schema evolution events are never updated or deleted.
- One row per column per run per entity. If three columns change in one run, three rows are written.
- `handled_by = "rejected"` always corresponds to `run_aborted = true`.

---

## 6. METADATA TABLE: `_error_log`

Append-only error log written when individual record processing errors or entity-level errors occur. Not used for run-level failures (those are in `_connector_runs.error_message`).

**Table path:** `{schema}._meta._error_log`

### Schema

| Column | Delta Type | Nullable | Description |
|---|---|---|---|
| `error_id` | `STRING` | NOT NULL | UUID of this error record. |
| `run_id` | `STRING` | NOT NULL | Run ID during which the error occurred. |
| `connector_id` | `STRING` | NOT NULL | ConnectorItem that produced this error. |
| `entity_name` | `STRING` | NOT NULL | Entity being processed when the error occurred. |
| `error_level` | `STRING` | NOT NULL | Scope of the error: `"entity"` (entity-level failure) or `"record"` (single record failure). |
| `error_type` | `STRING` | NOT NULL | Error taxonomy code (see §Error Taxonomy in ingestion-contracts.md). |
| `error_code` | `STRING` | NULLABLE | Vendor-specific error code (e.g. HTTP status, SQL error number). |
| `error_message` | `STRING` | NOT NULL | Full error message text. |
| `record_id` | `STRING` | NULLABLE | Source record identifier (primary key or OData ID) for record-level errors. Null for entity-level errors. |
| `occurred_utc` | `TIMESTAMP` | NOT NULL | UTC timestamp when the error occurred. |
| `retry_attempt` | `INTEGER` | NOT NULL | Which retry attempt this error occurred on (0 = first attempt). |
| `was_retried` | `BOOLEAN` | NOT NULL | Whether the operation was retried after this error. |
| `stack_trace` | `STRING` | NULLABLE | Python stack trace (truncated to 4000 chars). Included only for unexpected errors. |
| `wheel_version` | `STRING` | NOT NULL | Wheel version that logged this error. |

### Invariants

- Append-only. Errors are never updated.
- Errors that lead to retry are logged per attempt — a 3-attempt failure produces 3 rows in `_error_log`.
- Record-level errors do not increment the run's `entities_failed` counter; only entity-level errors do.

---

## 7. SCHEMA NAMESPACE CONVENTIONS

### Table Naming Rules

| Module | Schema | Data table name | Meta table prefix |
|---|---|---|---|
| CRM / Dataverse | `bronze_crm` | `{entity_logical_name}` | `bronze_crm._meta._` |
| Business Central | `bronze_bc` | `{api_endpoint}` | `bronze_bc._meta._` |
| SQL Server | `bronze_sql` | `{sql_schema}_{table_name}` (lowercase) | `bronze_sql._meta._` |

**SQL table name normalization:**
- `dbo.CustomerOrders` → `bronze_sql.dbo_customerorders`
- `sales.order_lines` → `bronze_sql.sales_order_lines`
- Special characters (spaces, dots within name) → replaced with `_`

**Reserved table name prefixes in all Bronze schemas:** `_` (reserved for ISV metadata tables)

### Schema Evolution Rules

| Rule | Applies to |
|---|---|
| Source column names are preserved verbatim | All Bronze data tables |
| New source columns are always added as NULLABLE | Merge policy |
| Dropped source columns remain as NULLABLE with null values | Merge policy |
| ISV `_`-prefixed columns are never removed or renamed | All schemas, all versions |
| Data type widening is allowed (e.g. INT → LONG) | Merge policy |
| Data type narrowing causes a `_schema_evolution_log` event | All policies |
| Overwrite policy drops and recreates the table | Overwrite policy only |

---

## 8. TYPESCRIPT TYPE DEFINITIONS

The following TypeScript types correspond to the metadata table schemas and are used in the ConnectorItem dashboard components to model API responses and runtime metadata.

```typescript
// Located in: Workload/app/items/ConnectorItem/ConnectorItemDefinition.ts

export type ConnectorRunStatus =
  | "running"
  | "success"
  | "partial_success"
  | "failed"
  | "cancelled";

export type TriggeredBy = "schedule" | "on_demand" | "activation";

export type WatermarkType = "delta_token" | "timestamp" | "rowversion";

export type SchemaChangeType =
  | "column_added"
  | "column_removed"
  | "type_changed"
  | "column_renamed_suspected";

export type ErrorLevel = "entity" | "record";

export interface EntityRunResult {
  entityName: string;
  status: "success" | "failed" | "skipped";
  recordsIngested: number;
  recordsFailed: number;
  durationSeconds: number;
  newWatermark: string | null;
  errorMessage: string | null;
}

export interface ConnectorRun {
  runId: string;
  connectorId: string;
  moduleType: ModuleType;
  runStartUtc: string;          // ISO 8601
  runEndUtc: string | null;
  durationSeconds: number | null;
  status: ConnectorRunStatus;
  triggeredBy: TriggeredBy;
  entitiesEnabled: number;
  entitiesProcessed: number;
  entitiesSucceeded: number;
  entitiesFailed: number;
  recordsIngested: number;
  recordsFailed: number;
  errorMessage: string | null;
  errorCode: string | null;
  entityResults: EntityRunResult[];
  wheelVersion: string;
  configSchemaVersion: string;
}

export interface EntityWatermark {
  connectorId: string;
  entityName: string;
  moduleType: ModuleType;
  watermarkType: WatermarkType;
  deltaToken: string | null;
  watermarkValue: string | null;
  watermarkColumn: string | null;
  lastRunId: string;
  lastSuccessUtc: string;       // ISO 8601
  recordsAtLastRun: number;
  recordsAtSourceEst: number | null;
  isInitialLoadComplete: boolean;
}

export interface SchemaEvolutionEvent {
  eventId: string;
  connectorId: string;
  entityName: string;
  runId: string;
  detectedUtc: string;          // ISO 8601
  changeType: SchemaChangeType;
  columnName: string;
  oldType: string | null;
  newType: string | null;
  handledBy: "merged" | "rejected" | "overwritten" | "ignored";
  evolutionPolicy: SchemaEvolutionPolicy;
  runAborted: boolean;
}

export interface ConnectorError {
  errorId: string;
  runId: string;
  connectorId: string;
  entityName: string;
  errorLevel: ErrorLevel;
  errorType: string;
  errorCode: string | null;
  errorMessage: string;
  recordId: string | null;
  occurredUtc: string;          // ISO 8601
  retryAttempt: number;
  wasRetried: boolean;
}
```

---

## 9. PYTHON DATACLASS DEFINITIONS

The following Python dataclasses are implemented in `agic_fabric_connector/config/config_models.py` and `agic_fabric_connector/base/metadata_writer.py`.

```python
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid


class ConnectorRunStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WatermarkType(str, Enum):
    DELTA_TOKEN = "delta_token"
    TIMESTAMP = "timestamp"
    ROWVERSION = "rowversion"


class SchemaEvolutionPolicy(str, Enum):
    MERGE = "merge"
    STRICT = "strict"
    OVERWRITE = "overwrite"


@dataclass
class EntityRunResult:
    entity_name: str
    status: str
    records_ingested: int
    records_failed: int
    duration_seconds: float
    new_watermark: Optional[str]
    error_message: Optional[str]


@dataclass
class ConnectorRunRecord:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connector_id: str = ""
    module_type: str = ""
    run_start_utc: datetime = field(default_factory=datetime.utcnow)
    run_end_utc: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: ConnectorRunStatus = ConnectorRunStatus.RUNNING
    triggered_by: str = "schedule"
    entities_enabled: int = 0
    entities_processed: int = 0
    entities_succeeded: int = 0
    entities_failed: int = 0
    records_ingested: int = 0
    records_failed: int = 0
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    entity_results: List[EntityRunResult] = field(default_factory=list)
    wheel_version: str = ""
    config_schema_version: str = "1.0.0"
    notebook_item_id: Optional[str] = None
    workspace_id: str = ""


@dataclass
class EntityWatermarkRecord:
    connector_id: str
    entity_name: str
    module_type: str
    watermark_type: WatermarkType
    delta_token: Optional[str]
    watermark_value: Optional[str]
    watermark_column: Optional[str]
    last_run_id: str
    last_success_utc: datetime
    records_at_last_run: int
    records_at_source_est: Optional[int]
    is_initial_load_complete: bool
    workspace_id: str


@dataclass
class SchemaEvolutionLogRecord:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connector_id: str = ""
    entity_name: str = ""
    run_id: str = ""
    detected_utc: datetime = field(default_factory=datetime.utcnow)
    change_type: str = ""
    column_name: str = ""
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    handled_by: str = ""
    evolution_policy: str = ""
    run_aborted: bool = False
    wheel_version: str = ""


@dataclass
class ErrorLogRecord:
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str = ""
    connector_id: str = ""
    entity_name: str = ""
    error_level: str = ""
    error_type: str = ""
    error_code: Optional[str] = None
    error_message: str = ""
    record_id: Optional[str] = None
    occurred_utc: datetime = field(default_factory=datetime.utcnow)
    retry_attempt: int = 0
    was_retried: bool = False
    stack_trace: Optional[str] = None
    wheel_version: str = ""
```

---

## 10. LIFECYCLE AND ACCESS PATTERNS

### Dashboard Read Pattern (Phase 1)

In Phase 1, the dashboard reads run history from `JobSchedulerClient` (Fabric Job Scheduler API), not from `_connector_runs`. The metadata tables are written by the notebook and read via Fabric SQL analytics endpoint in Phase 2.

```
Phase 1 Dashboard data sources:
├── Run list: JobSchedulerClient.listItemJobInstances() → job statuses from Fabric
├── Schedule info: JobSchedulerClient.listItemSchedules() → next run time
└── Entity health: stored in runtime metadata of item definition (lightweight fallback)

Phase 2 Dashboard data sources:
├── Run details: SELECT * FROM bronze_{module}._meta._connector_runs WHERE connector_id = ?
├── Entity watermarks: SELECT * FROM bronze_{module}._meta._entity_watermarks WHERE connector_id = ?
├── Schema changes: SELECT * FROM bronze_{module}._meta._schema_evolution_log WHERE connector_id = ?
└── Errors: SELECT * FROM bronze_{module}._meta._error_log WHERE run_id = ?
```

### Watermark Reset Flow

```
User clicks "Reset Watermark" in entity-detail ribbon
  ↓
UI calls Fabric Items API to update item definition
  ↓
Notebook next run: watermark row absent for entity
  ↓
Runtime performs full extract (initial load mode)
  ↓
New watermark row written after completion
```

### Retention Policy

```
Bronze data tables: managed by customer (no ISV-enforced retention)
_connector_runs:    retain all rows (run history = audit trail)
_entity_watermarks: only current row per (connector_id, entity_name) — no history
_schema_evolution_log: retain all rows (permanent audit log)
_error_log: retain all rows (permanent audit log; archive to cold storage after 90 days)
```

### Index Recommendations (Phase 2 — Z-Order)

```sql
-- Applied via Delta OPTIMIZE after initial load
OPTIMIZE bronze_crm._meta._connector_runs ZORDER BY (connector_id, run_start_utc);
OPTIMIZE bronze_crm._meta._error_log ZORDER BY (run_id, entity_name);
OPTIMIZE bronze_crm.contact ZORDER BY (_connector_id, _ingestion_date);
```
