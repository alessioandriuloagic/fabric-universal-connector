/**
 * connectorRegistry.ts
 *
 * Single source-of-truth for all supported connector types.
 *
 * Extensibility contract (open/closed principle):
 *   - TO ADD a new connector: push a new `ConnectorDefinition` into
 *     CONNECTOR_REGISTRY.  That is the ONLY required change.
 *   - Selection UI, validation pipeline and state management are driven
 *     entirely from this registry — they do not contain connector-specific
 *     logic and therefore never need to be modified.
 */
import {
  ModuleType,
  ConnectorEntry,
  CrmConnectorEntry,
  BusinessCentralConnectorEntry,
  SqlConnectorEntry,
} from "../ConnectorItemDefinition";

// ── Per-connector validator functions ───────────────────────────
// Each validator returns a flat error map keyed by "<connectorType>.<field>".
// The key convention keeps errors from different connectors distinct when they
// are merged into a shared `validationErrors` record in the wizard state.

function validateCrm(entry: ConnectorEntry): Record<string, string> {
  if (entry.connectorType !== "crm") return {};
  const errors: Record<string, string> = {};
  if (!entry.source.environmentUrl) {
    errors["crm.environmentUrl"] = "CRM Organisation URL is required.";
  }
  if (!entry.source.tenantId) {
    errors["crm.tenantId"] = "Azure AD Tenant ID is required.";
  }
  if (!entry.auth) {
    errors["crm.auth"] = "Authentication method is required.";
  } else if (entry.auth.mode === "fabric_connection" && !(entry.auth as any).fabricConnectionId) {
    errors["crm.fabricConnectionId"] = "Fabric Connection ID is required.";
  } else if (entry.auth.mode === "keyvault_reference") {
    if (!(entry.auth as any).keyVaultUri) errors["crm.keyVaultUri"] = "Key Vault URI is required.";
    if (!(entry.auth as any).clientSecretName) errors["crm.clientSecretName"] = "Secret name is required.";
  } else if (entry.auth.mode === "service_principal") {
    if (!(entry.auth as any).tenantId) errors["crm.sp.tenantId"] = "Tenant ID is required.";
    if (!(entry.auth as any).clientId) errors["crm.sp.clientId"] = "Client ID is required.";
  }
  return errors;
}

function validateBc(entry: ConnectorEntry): Record<string, string> {
  if (entry.connectorType !== "businesscentral") return {};
  const errors: Record<string, string> = {};
  if (!entry.source.tenantId) {
    errors["bc.tenantId"] = "Tenant ID is required.";
  }
  if (!entry.source.environment) {
    errors["bc.environment"] = "Environment name is required.";
  }
  if (!entry.auth) {
    errors["bc.auth"] = "Authentication method is required.";
  }
  return errors;
}

function validateSql(entry: ConnectorEntry): Record<string, string> {
  if (entry.connectorType !== "sql") return {};
  const errors: Record<string, string> = {};
  if (!entry.source.server) {
    errors["sql.server"] = "Server hostname is required.";
  }
  if (!entry.source.database) {
    errors["sql.database"] = "Database name is required.";
  }
  if (!entry.auth) {
    errors["sql.auth"] = "Authentication method is required.";
  }
  return errors;
}

// ── ConnectorDefinition interface ────────────────────────────────

/** Metadata and behaviour for one connector type in the registry. */
export interface ConnectorDefinition {
  /** Unique key matching `ModuleType`. */
  type: ModuleType;
  /** Display label for the selection card and section header. */
  label: string;
  /** Short description shown below the label. */
  description: string;
  /** Hex accent color applied to the card border when the connector is enabled. */
  accentColor: string;
  /**
   * Factory that returns a brand-new disabled, empty entry for this connector.
   * Used to initialise the wizard state and to migrate v1 definitions.
   */
  createDefault: () => ConnectorEntry;
  /**
   * Returns a flat error map for `entry`.  Keys follow "<type>.<field>" convention.
   * Called per-connector inside the shared validation pipeline — no per-connector
   * logic is needed anywhere else.
   */
  validate: (entry: ConnectorEntry) => Record<string, string>;
}

// ── Registry ─────────────────────────────────────────────────────

/**
 * Ordered list of all supported connectors.
 *
 * ADD a new connector here.  Everything else is data-driven.
 */
export const CONNECTOR_REGISTRY: ConnectorDefinition[] = [
  {
    type: "crm",
    label: "Microsoft Dataverse / Dynamics 365 CRM",
    description: "Incremental extraction using Change Tracking API (OData v9.2)",
    accentColor: "#0078d4",
    createDefault: (): CrmConnectorEntry => ({
      connectorType: "crm",
      enabled: false,
      status: "unconfigured",
      source: {},
      auth: undefined,
      entities: [],
    }),
    validate: validateCrm,
  },
  {
    type: "businesscentral",
    label: "Dynamics 365 Business Central",
    description: "OData v4 API extraction — standard and custom APIs",
    accentColor: "#217346",
    createDefault: (): BusinessCentralConnectorEntry => ({
      connectorType: "businesscentral",
      enabled: false,
      status: "unconfigured",
      source: {},
      auth: undefined,
      entities: [],
    }),
    validate: validateBc,
  },
  {
    type: "sql",
    label: "SQL Server / Azure SQL",
    description: "JDBC / CDC extraction with watermark-based incremental loads",
    accentColor: "#c50f1f",
    createDefault: (): SqlConnectorEntry => ({
      connectorType: "sql",
      enabled: false,
      status: "unconfigured",
      source: {},
      auth: undefined,
      entities: [],
    }),
    validate: validateSql,
  },
];

/** Look up a connector definition by type.  Returns undefined if not registered. */
export function getConnectorDef(type: ModuleType): ConnectorDefinition | undefined {
  return CONNECTOR_REGISTRY.find((d) => d.type === type);
}

/**
 * Build the initial `connectors` array for a fresh wizard run:
 * one disabled entry per registered connector type.
 */
export function buildDefaultConnectors(): ConnectorEntry[] {
  return CONNECTOR_REGISTRY.map((def) => def.createDefault());
}
