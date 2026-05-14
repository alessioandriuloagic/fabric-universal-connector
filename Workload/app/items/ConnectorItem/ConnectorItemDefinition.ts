export type ModuleType = "crm" | "businesscentral" | "sql";
export type ConnectorState = "empty" | "configured" | "error" | "paused";
export type SchemaEvolutionPolicy = "merge" | "strict" | "overwrite";
export type AuthMode = "fabric_connection" | "keyvault_reference" | "service_principal";
export type ExtractionMode = "incremental" | "full";
export type ConnectorRunStatus = "running" | "success" | "partial_success" | "failed" | "cancelled";
export type TriggeredBy = "schedule" | "on_demand" | "activation";
export type WatermarkType = "delta_token" | "timestamp" | "rowversion";

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

// ── Authentication ──────────────────────────────────────────────

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

// ── Entity configurations ───────────────────────────────────────

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

// ── Storage / Schedule / Features / Runtime / Metadata ─────────

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

// ── Top-level discriminated union ───────────────────────────────

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

// ── Runtime metadata types (dashboard) ─────────────────────────

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
  runStartUtc: string;
  runEndUtc: string | null;
  durationSeconds: number | null;
  status: ConnectorRunStatus;
  triggeredBy: TriggeredBy;
  entitiesSucceeded: number;
  entitiesFailed: number;
  recordsIngested: number;
  errorMessage: string | null;
  entityResults: EntityRunResult[];
  wheelVersion: string;
}

export interface EntityWatermark {
  connectorId: string;
  entityName: string;
  watermarkType: WatermarkType;
  lastSuccessUtc: string;
  recordsAtLastRun: number;
  isInitialLoadComplete: boolean;
}

// ── Type guards ─────────────────────────────────────────────────

export function isCrmConnector(def: ConnectorItemDefinition): def is CrmConnectorItemDefinition {
  return def.moduleType === "crm";
}

export function isBusinessCentralConnector(def: ConnectorItemDefinition): def is BusinessCentralConnectorItemDefinition {
  return def.moduleType === "businesscentral";
}

export function isSqlConnector(def: ConnectorItemDefinition): def is SqlConnectorItemDefinition {
  return def.moduleType === "sql";
}

export function createEmptyDefinition(): Pick<ConnectorItemDefinitionBase, "schemaVersion" | "state"> {
  return { schemaVersion: "1.0.0", state: "empty" };
}
