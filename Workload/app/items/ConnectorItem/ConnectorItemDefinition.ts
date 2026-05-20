/** Supported data source module types. */
export type ModuleType = "crm" | "businesscentral" | "sql";

/** Lifecycle state of the connector item. */
export type ConnectorState = "empty" | "configured" | "error" | "paused";

/**
 * Policy applied when the source schema changes between runs.
 * - `merge`     — new columns are added; existing columns are preserved.
 * - `strict`    — schema changes cause the run to fail.
 * - `overwrite` — the table is dropped and recreated with the new schema.
 */
export type SchemaEvolutionPolicy = "merge" | "strict" | "overwrite";

/** Strategy used to resolve credentials at runtime. */
export type AuthMode = "fabric_connection" | "keyvault_reference" | "service_principal";

/**
 * Strategy for extracting records from the source system.
 * - `incremental` — only new/changed records since the last watermark.
 * - `full`        — complete reload of all records.
 */
export type ExtractionMode = "incremental" | "full";

/** Terminal and non-terminal states of a single connector run. */
export type ConnectorRunStatus = "running" | "success" | "partial_success" | "failed" | "cancelled";

/** Origin of a run trigger. */
export type TriggeredBy = "schedule" | "on_demand" | "activation";

/** Mechanism used to track incremental progress for an entity. */
export type WatermarkType = "delta_token" | "timestamp" | "rowversion";

// ── Source configurations ──────────────────────────────────────

/** Connection parameters for a Dataverse / Dynamics 365 CRM environment. */
export interface CrmSourceConfiguration {
  /** Full Dataverse environment URL, e.g. https://org.crm.dynamics.com */
  environmentUrl: string;
  /** Entra ID tenant owning the Dataverse environment. */
  tenantId: string;
  /** Dataverse Web API version (default: "9.2"). */
  apiVersion?: string;
  /** When true, Change Tracking is used for incremental extraction (recommended). */
  enableChangeTracking?: boolean;
  /** Number of records per OData page (default: 5000). */
  pageSize?: number;
}

/** Connection parameters for a Business Central environment via OData v4. */
export interface BusinessCentralSourceConfiguration {
  /** Entra ID tenant owning the BC environment. */
  tenantId: string;
  /** BC environment name (e.g. "Production"). */
  environment: string;
  /** Target company GUID; omit to target the default company. */
  companyId?: string;
  /** BC API version (default: "v2.0"). */
  apiVersion?: string;
  /** Number of records per OData page (default: 1000). */
  pageSize?: number;
}

/** Connection parameters for SQL Server / Azure SQL. */
export interface SqlSourceConfiguration {
  /** Hostname or IP address of the SQL Server instance. */
  server: string;
  /** Target database name. */
  database: string;
  /** TCP port (default: 1433). */
  port?: number;
  /** ODBC driver variant to use. */
  driver?: "sqlserver" | "azuresql";
  /** Enforce TLS encryption on the connection. */
  encrypt?: boolean;
  /** Skip certificate validation (development only). */
  trustServerCertificate?: boolean;
}

// ── Authentication ──────────────────────────────────────────────

/** Auth via a pre-registered Fabric Connection (no secrets in item definition). */
export interface FabricConnectionAuth {
  mode: "fabric_connection";
  /** ID of the Fabric Connection storing the credentials. */
  fabricConnectionId: string;
}

/** Auth by reading secrets from Azure Key Vault at runtime. */
export interface KeyVaultReferenceAuth {
  mode: "keyvault_reference";
  /** Base URI of the Key Vault, e.g. https://myvault.vault.azure.net */
  keyVaultUri: string;
  /** Secret name for the Entra client ID (optional if using managed identity). */
  clientIdSecretName?: string;
  /** Secret name for the Entra client secret. */
  clientSecretName: string;
  /** Secret name for the Entra tenant ID (optional if already known). */
  tenantIdSecretName?: string;
}

/** Auth using an Entra service principal; secrets resolved via Fabric Connection or Key Vault. */
export interface ServicePrincipalAuth {
  mode: "service_principal";
  /** Entra tenant ID for the service principal. */
  tenantId: string;
  /** Entra application (client) ID. */
  clientId: string;
  /** Reference to the secret (Fabric Connection or Key Vault). */
  secretRef: FabricConnectionAuth | KeyVaultReferenceAuth;
}

/** Discriminated union of all supported authentication strategies. */
export type AuthConfiguration = FabricConnectionAuth | KeyVaultReferenceAuth | ServicePrincipalAuth;

// ── Entity configurations ───────────────────────────────────────

/** Per-entity extraction settings for a CRM / Dataverse source. */
export interface CrmEntityConfiguration {
  /** Dataverse logical name of the entity table (e.g. "contact", "lead"). */
  logicalName: string;
  /** Human-readable label shown in the UI. */
  displayName: string;
  /** Whether this entity is active in the next run. */
  enabled: boolean;
  /** Override the global extraction mode for this entity. */
  extractionMode?: ExtractionMode;
  /** OData $select columns; omit to fetch all columns. */
  selectColumns?: string[];
  /** OData $expand navigation properties to inline. */
  expandRelationships?: string[];
  /** OData $filter expression applied server-side. */
  filterExpression?: string;
  /** Records per API request page. */
  batchSize?: number;
}

/** Per-entity extraction settings for a Business Central OData source. */
export interface BusinessCentralEntityConfiguration {
  /** Relative OData endpoint path (e.g. "companies({id})/customers"). */
  apiEndpoint: string;
  /** Human-readable label shown in the UI. */
  displayName: string;
  /** Whether this entity is active in the next run. */
  enabled: boolean;
  /** Override the global extraction mode for this entity. */
  extractionMode?: ExtractionMode;
  /** Column used as incremental watermark when not using delta links. */
  watermarkColumn?: string;
  /** OData $select columns; omit to fetch all columns. */
  selectColumns?: string[];
  /** OData $filter expression applied server-side. */
  filterExpression?: string;
  /** Records per API request page. */
  batchSize?: number;
}

/** Per-table extraction settings for a SQL Server source. */
export interface SqlEntityConfiguration {
  /** SQL schema name (e.g. "dbo"). */
  schema: string;
  /** Table or view name. */
  tableName: string;
  /** Human-readable label shown in the UI. */
  displayName: string;
  /** Whether this table is active in the next run. */
  enabled: boolean;
  /** Override the global extraction mode for this table. */
  extractionMode?: ExtractionMode;
  /** Column used as incremental watermark (e.g. "ModifiedAt"). */
  watermarkColumn?: string;
  /** Data type of the watermark column, used to build the correct WHERE clause. */
  watermarkColumnType?: "datetime" | "rowversion" | "integer";
  /** Columns to SELECT; omit to fetch all columns. */
  selectColumns?: string[];
  /** Additional WHERE clause fragment appended to every query. */
  whereClause?: string;
  /** Primary key column(s) used for deduplication in merge scenarios. */
  primaryKeys?: string[];
  /** JDBC fetch size for cursor-based reads (default: 10000). */
  fetchSize?: number;
}

// ── Storage / Schedule / Features / Runtime / Metadata ─────────

/** Destination Lakehouse and Bronze layer settings. */
export interface StorageConfiguration {
  /** Fabric item ID of the Bronze Lakehouse; populated after activation. */
  bronzeLakeHouseId?: string;
  /** Display name for the Bronze Lakehouse (created if it does not exist). */
  bronzeLakeHouseName: string;
  /** Policy applied when source schema evolves between runs. */
  schemaEvolutionPolicy?: SchemaEvolutionPolicy;
  /** Number of days to retain run history records in the _meta tables. */
  retentionDays?: number;
  /** When true, attach to an existing Lakehouse instead of creating a new one. */
  useExistingLakehouse?: boolean;
}

/** Automated run schedule for the connector. */
export interface SchedulingConfiguration {
  /** Trigger type: `cron` for cron expressions, `interval` for fixed intervals. */
  scheduleType: "cron" | "interval";
  /** Standard cron expression (5-field). Required when scheduleType is "cron". */
  cronExpression?: string;
  /** Interval in minutes between runs. Required when scheduleType is "interval". */
  intervalMinutes?: number;
  /** IANA time zone for evaluating cron expressions (default: "UTC"). */
  timezone?: string;
  /** Master switch — false disables the schedule without deleting it. */
  enabled: boolean;
  /** ISO-8601 date from which the schedule is active. */
  startDate?: string;
}

/** Optional feature flags controlling runtime behaviour. */
export interface FeaturesConfiguration {
  /** Override for schema evolution; falls back to StorageConfiguration.schemaEvolutionPolicy. */
  schemaEvolutionHandling?: SchemaEvolutionPolicy;
  /** Percentage of failed records (0-100) above which the run is marked as failed. */
  errorThresholdPercent?: number;
  /** When true, a run succeeds even if some entities failed (partial_success status). */
  enablePartialRun?: boolean;
  /** Send anonymous usage telemetry to Agic Technology for product improvement. */
  enableTelemetry?: boolean;
  /** Hard cap on records extracted per entity per run (useful for initial loads). */
  maxRecordsPerEntityPerRun?: number;
  /** Run OPTIMIZE on Delta tables after each successful write (improves query performance). */
  enableDeltaLakeOptimize?: boolean;
}

/** Metadata about the deployed runtime artefacts; populated automatically after activation. */
export interface RuntimeConfiguration {
  /** Fabric item ID of the deployed connector notebook. */
  notebookItemId?: string;
  /** Fabric item ID of the Bronze Lakehouse resolved at activation time. */
  bronzeLakeHouseId?: string;
  /** ISO-8601 timestamp of the last successful notebook deployment. */
  deployedAt?: string;
  /** Version of the agic-fabric-connector wheel deployed in the notebook. */
  wheelVersion?: string;
  /** JSON schema version of the item definition persisted in OneLake. */
  configSchemaVersion?: string;
  /** Fabric job schedule ID bound to this connector (if scheduling is enabled). */
  jobScheduleId?: string;
}

/** User-facing metadata attached to the connector item. */
export interface ConnectorMetadata {
  /** Display name shown in the Fabric workspace item list. */
  displayName?: string;
  /** Free-text description of the connector's purpose. */
  description?: string;
  /** Searchable labels for organisation and filtering. */
  tags?: string[];
  /** ISO-8601 creation timestamp (set by the platform on first save). */
  createdAt?: string;
  /** ISO-8601 last-modified timestamp (updated on every save). */
  updatedAt?: string;
  /** ISO-8601 timestamp of the first successful activation. */
  activatedAt?: string;
}

// ── Top-level discriminated union ───────────────────────────────

/**
 * Shared fields present in every connector item definition variant.
 * Not exported directly — use the module-specific types below.
 */
interface ConnectorItemDefinitionBase {
  /** JSON schema version; used for forward-compatible deserialization. */
  schemaVersion: "1.0.0";
  /** Current lifecycle state of this connector item. */
  state: ConnectorState;
  authentication?: AuthConfiguration;
  storage?: StorageConfiguration;
  scheduling?: SchedulingConfiguration;
  features?: FeaturesConfiguration;
  runtime?: RuntimeConfiguration;
  metadata?: ConnectorMetadata;
}

/** Full item definition for a Dataverse / Dynamics 365 CRM connector. */
export interface CrmConnectorItemDefinition extends ConnectorItemDefinitionBase {
  moduleType: "crm";
  source: CrmSourceConfiguration;
  entities: CrmEntityConfiguration[];
}

/** Full item definition for a Business Central OData connector. */
export interface BusinessCentralConnectorItemDefinition extends ConnectorItemDefinitionBase {
  moduleType: "businesscentral";
  source: BusinessCentralSourceConfiguration;
  entities: BusinessCentralEntityConfiguration[];
}

/** Full item definition for a SQL Server / Azure SQL connector. */
export interface SqlConnectorItemDefinition extends ConnectorItemDefinitionBase {
  moduleType: "sql";
  source: SqlSourceConfiguration;
  entities: SqlEntityConfiguration[];
}

/**
 * Top-level discriminated union representing all supported connector item definitions.
 * Narrow by checking `moduleType` to access module-specific `source` and `entities` fields.
 */
export type ConnectorItemDefinition =
  | CrmConnectorItemDefinition
  | BusinessCentralConnectorItemDefinition
  | SqlConnectorItemDefinition;

// ── Runtime metadata types (dashboard) ─────────────────────────

/** Extraction outcome for a single entity within a connector run. */
export interface EntityRunResult {
  /** Logical name / table name of the entity. */
  entityName: string;
  /** Terminal outcome for this entity in the run. */
  status: "success" | "failed" | "skipped";
  /** Total records successfully written to the Bronze Lakehouse. */
  recordsIngested: number;
  /** Total records that could not be processed (logged to _error_log). */
  recordsFailed: number;
  /** Wall-clock seconds from first API call to last write. */
  durationSeconds: number;
  /** New watermark value persisted for the next incremental run; null on full loads. */
  newWatermark: string | null;
  /** Human-readable error message if status is "failed". */
  errorMessage: string | null;
}

/** Summary record for a completed or in-progress connector run, as displayed in the dashboard. */
export interface ConnectorRun {
  /** Unique run identifier (UUID v4). */
  runId: string;
  /** ID of the connector item that triggered the run. */
  connectorId: string;
  /** Source module that executed the run. */
  moduleType: ModuleType;
  /** ISO-8601 UTC timestamp when the run started. */
  runStartUtc: string;
  /** ISO-8601 UTC timestamp when the run ended; null if still in progress. */
  runEndUtc: string | null;
  /** Total run duration in seconds; null if still in progress. */
  durationSeconds: number | null;
  /** Aggregate run outcome. */
  status: ConnectorRunStatus;
  /** How this run was initiated. */
  triggeredBy: TriggeredBy;
  /** Number of entities that completed successfully. */
  entitiesSucceeded: number;
  /** Number of entities that failed. */
  entitiesFailed: number;
  /** Total records ingested across all entities. */
  recordsIngested: number;
  /** Top-level error message if the run failed fatally. */
  errorMessage: string | null;
  /** Per-entity breakdown of this run. */
  entityResults: EntityRunResult[];
  /** Version of the agic-fabric-connector wheel used for this run. */
  wheelVersion: string;
}

/** Incremental sync checkpoint for a single entity, persisted in the _meta/watermarks table. */
export interface EntityWatermark {
  /** ID of the owning connector item. */
  connectorId: string;
  /** Logical name / table name of the entity. */
  entityName: string;
  /** Strategy used to track progress (delta token, timestamp, or rowversion). */
  watermarkType: WatermarkType;
  /** ISO-8601 UTC timestamp of the last successful extraction for this entity. */
  lastSuccessUtc: string;
  /** Record count written during the last successful run for this entity. */
  recordsAtLastRun: number;
  /** True once the first full load has completed and incremental mode is active. */
  isInitialLoadComplete: boolean;
}

// ── Type guards ─────────────────────────────────────────────────

/** Narrows `def` to `CrmConnectorItemDefinition`. */
export function isCrmConnector(def: ConnectorItemDefinition): def is CrmConnectorItemDefinition {
  return def.moduleType === "crm";
}

/** Narrows `def` to `BusinessCentralConnectorItemDefinition`. */
export function isBusinessCentralConnector(def: ConnectorItemDefinition): def is BusinessCentralConnectorItemDefinition {
  return def.moduleType === "businesscentral";
}

/** Narrows `def` to `SqlConnectorItemDefinition`. */
export function isSqlConnector(def: ConnectorItemDefinition): def is SqlConnectorItemDefinition {
  return def.moduleType === "sql";
}

/** Returns the minimal valid item definition for a newly created, unconfigured connector. */
export function createEmptyDefinition(): Pick<ConnectorItemDefinitionBase, "schemaVersion" | "state"> {
  return { schemaVersion: "1.0.0", state: "empty" };
}

// ── v2 Multi-Connector types ────────────────────────────────────
//
// Architectural decision: moving from a single-connector discriminated union
// (v1, schemaVersion "1.0.0") to a multi-connector array model (v2, "2.0.0").
// All three connector types are always present in the array; `enabled: false`
// means the connector is inactive.  Adding a fourth connector requires only a
// new entry in connectorRegistry.ts — this file does not need to change.

/** Per-connector readiness, computed from field-level validation. */
export type ConnectorStatus = "unconfigured" | "valid" | "error";

/** Per-connector configuration block for a Dataverse / Dynamics 365 CRM connector. */
export interface CrmConnectorEntry {
  connectorType: "crm";
  /** Whether this connector participates in the next ingestion run. */
  enabled: boolean;
  /** Computed from field validation; drives the status badge in the UI. */
  status: ConnectorStatus;
  source: Partial<CrmSourceConfiguration>;
  auth?: AuthConfiguration;
  entities: CrmEntityConfiguration[];
}

/** Per-connector configuration block for a Business Central OData connector. */
export interface BusinessCentralConnectorEntry {
  connectorType: "businesscentral";
  enabled: boolean;
  status: ConnectorStatus;
  source: Partial<BusinessCentralSourceConfiguration>;
  auth?: AuthConfiguration;
  entities: BusinessCentralEntityConfiguration[];
}

/** Per-connector configuration block for a SQL Server / Azure SQL connector. */
export interface SqlConnectorEntry {
  connectorType: "sql";
  enabled: boolean;
  status: ConnectorStatus;
  source: Partial<SqlSourceConfiguration>;
  auth?: AuthConfiguration;
  entities: SqlEntityConfiguration[];
}

/**
 * Discriminated union of all supported per-connector config entries.
 * Narrow by checking `connectorType`.
 */
export type ConnectorEntry =
  | CrmConnectorEntry
  | BusinessCentralConnectorEntry
  | SqlConnectorEntry;

/**
 * v2 item definition supporting multiple simultaneous connectors.
 * Storage, scheduling, features, runtime and metadata are shared across all
 * active connectors (they write to the same Bronze Lakehouse on the same schedule).
 *
 * schemaVersion "2.0.0" is the discriminator used by normalizeToV2() to skip
 * migration when the payload is already in the new format.
 */
export interface MultiConnectorItemDefinition {
  schemaVersion: "2.0.0";
  state: ConnectorState;
  /**
   * Ordered list of connector entries — one per registered connector type.
   * All connector types are always present so the UI can render toggle cards
   * even before any connector is configured.
   */
  connectors: ConnectorEntry[];
  storage?: StorageConfiguration;
  scheduling?: SchedulingConfiguration;
  features?: FeaturesConfiguration;
  runtime?: RuntimeConfiguration;
  metadata?: ConnectorMetadata;
}

/**
 * Union of all storable item-definition shapes.
 * Use `normalizeToV2` (migrationAdapter.ts) to coerce any loaded payload to
 * `MultiConnectorItemDefinition` before passing it to UI or service logic.
 */
export type AnyConnectorItemDefinition = ConnectorItemDefinition | MultiConnectorItemDefinition;
