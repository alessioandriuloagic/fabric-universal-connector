/**
 * workloads/sql-db/frontend/workloadConfig.ts
 *
 * SQL DB workload configuration.
 *
 * Source system: Azure SQL / SQL Server.
 * Unlike the other workloads, SQL DB has NO pre-defined entity list —
 * the user provides table names freely in the wizard (WizardEntityStep shows
 * a free-text input instead of a locked checkbox list).
 *
 * The `entities` array is intentionally empty. The backend (sql_db.py) uses
 * ALLOWED_ENTITY_NAMES = frozenset() (permissive — accepts any table name).
 *
 * To run locally in SQL DB mode:
 *   cd Workload && npm run start:sql-db
 *
 * To build for production:
 *   cd Workload && npm run build:sql-db:prod
 */
import type { WorkloadConfig } from "../../../shared/types/workload";
import { createWorkloadFetch } from "../../../shared/utils/apiClient";

// ── Workload identity ─────────────────────────────────────────────────────────

export const WORKLOAD_ID = "sql-db" as const;

// ── Entity catalog (empty — user-defined tables) ──────────────────────────────

export const SQL_DB_WORKLOAD_CONFIG: WorkloadConfig = {
  id: WORKLOAD_ID,
  displayName: "SQL DB Connector",
  source: "sql",
  // No pre-defined entities: the user enters table names manually in the wizard.
  entities: [],
};

// ── Backend fetch client (X-Workload-Id pre-injected) ────────────────────────

/**
 * Pre-configured fetch function for SQL DB backend calls.
 *
 * Automatically sets:
 *   - Content-Type: application/json
 *   - X-Workload-Id: sql-db
 *
 * @example
 * const res = await sqlDbFetch("/v1/items/abc123/runs");
 * const runs = await res.json();
 */
export const sqlDbFetch = createWorkloadFetch(
  WORKLOAD_ID,
  process.env.REACT_APP_BACKEND_URL ?? "",
);
