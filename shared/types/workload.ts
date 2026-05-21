/**
 * shared/types/workload.ts
 *
 * Single source of truth for workload identity types shared across all
 * workload frontends and the shared utility layer.
 *
 * Keep this file dependency-free (no React, no Fabric SDK imports) so it
 * can be imported from anywhere — frontend apps, shared utilities, tests.
 */

// ── Workload identity ─────────────────────────────────────────────────────────

/**
 * Union of all registered workload IDs.
 * Must stay in sync with:
 *   - backend/app/api/workloads.py  (WorkloadId enum)
 *   - Workload/app/items/ConnectorItem/workloadConfig.ts  (CONFIGS keys)
 */
export type WorkloadId =
  | "customer-insight-journey"
  | "sales-crm"
  | "business-central"
  | "sql-db"
  | "universal";

// ── Source system ─────────────────────────────────────────────────────────────

/** Connector/source type used by this workload. */
export type WorkloadSource = "crm" | "businesscentral" | "sql";

// ── Entity definitions ────────────────────────────────────────────────────────

/**
 * Describes a single data entity exposed by a workload.
 *
 * CRM workloads use `logicalName` (Dataverse entity logical name).
 * BC workloads use `logicalName` as the OData api_endpoint (e.g. "customers").
 * SQL workloads have no pre-defined entities — list is empty.
 */
export interface EntityDefinition {
  /** Unique entity identifier (Dataverse logical name or BC OData endpoint). */
  logicalName: string;
  /** Human-readable label shown in the UI. */
  displayName: string;
  /** Delta table path under the Bronze Lakehouse (e.g. "bronze_crm/contact"). */
  bronzeTable: string;
  /**
   * When true the entity is pre-selected and cannot be deselected by the user.
   * Used for scoped workloads where the entity set is fixed.
   */
  locked?: boolean;
}

// ── Workload config ───────────────────────────────────────────────────────────

/**
 * Full configuration for a scoped workload.
 *
 * Used by:
 *   - shared/utils/apiClient.ts  (header injection)
 *   - workloads/{workload}/frontend/workloadConfig.ts  (per-workload overrides)
 *   - Workload/app/items/ConnectorItem/workloadConfig.ts  (CONFIGS registry)
 */
export interface WorkloadConfig {
  /** Unique workload identifier — must match WorkloadId. */
  id: WorkloadId;
  /** Human-readable workload name shown in the UI. */
  displayName: string;
  /** Source system this workload ingests from. */
  source: WorkloadSource;
  /**
   * Pre-defined entity list.
   * Empty for "sql-db" (user-defined) and "universal" (all entities).
   */
  entities: EntityDefinition[];
}
