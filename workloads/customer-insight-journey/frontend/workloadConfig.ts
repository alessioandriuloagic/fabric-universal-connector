/**
 * workloads/customer-insight-journey/frontend/workloadConfig.ts
 *
 * CIJ-specific workload configuration — used by the main Workload app when
 * started with REACT_APP_WORKLOAD_ID=customer-insight-journey, and by any
 * future standalone CIJ frontend build.
 *
 * This file is the single source of truth for:
 *   - Which entities are pre-selected and locked (read-only)
 *   - The X-Workload-Id header value injected on backend calls
 *   - The wizard steps enabled for this workload
 *
 * To run locally in CIJ mode:
 *   cd Workload && npm run start:customer-insight-journey
 *
 * To build for production:
 *   cd Workload && npm run build:customer-insight-journey:prod
 */
import type { WorkloadConfig } from "../../../shared/types/workload";
import { createWorkloadFetch } from "../../../shared/utils/apiClient";

// ── Workload identity ─────────────────────────────────────────────────────────

export const WORKLOAD_ID = "customer-insight-journey" as const;

// ── Entity catalog (locked — user cannot deselect) ────────────────────────────

export const CIJ_WORKLOAD_CONFIG: WorkloadConfig = {
  id: WORKLOAD_ID,
  displayName: "Customer Insight Journey",
  source: "crm",
  entities: [
    {
      logicalName: "contact",
      displayName: "Contact",
      bronzeTable: "bronze_crm/contact",
      locked: true,
    },
    {
      logicalName: "msdynmkt_email",
      displayName: "Marketing Email (Customer Insights Journey)",
      bronzeTable: "bronze_crm/msdynmkt_email",
      locked: true,
    },
    {
      logicalName: "msdynmkt_journey",
      displayName: "Journey (Customer Insights Journey)",
      bronzeTable: "bronze_crm/msdynmkt_journey",
      locked: true,
    },
  ],
};

// ── Backend fetch client (X-Workload-Id pre-injected) ────────────────────────

/**
 * Pre-configured fetch function for CIJ backend calls.
 *
 * Automatically sets:
 *   - Content-Type: application/json
 *   - X-Workload-Id: customer-insight-journey
 *
 * @example
 * const res = await cijFetch("/v1/items/abc123/runs");
 * const runs = await res.json();
 */
export const cijFetch = createWorkloadFetch(
  WORKLOAD_ID,
  process.env.REACT_APP_BACKEND_URL ?? "",
);
