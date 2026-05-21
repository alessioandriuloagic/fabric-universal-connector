/**
 * workloads/sales-crm/frontend/workloadConfig.ts
 *
 * Sales CRM workload configuration.
 *
 * Source system: Dynamics 365 / Dataverse (CRM module) — sales pipeline entities.
 * Entity set is explicitly distinct from Customer Insight Journey:
 *   CIJ owns: contact, msdynmkt_email, msdynmkt_journey
 *   Sales CRM owns: lead, opportunity, account, contact, quote, salesorder, invoice
 *
 * Note: "contact" appears in both workloads intentionally — it is a shared
 * Dataverse entity. Each workload ingests it into its own bronze path.
 *
 * To run locally in Sales CRM mode:
 *   cd Workload && npm run start:sales-crm
 *
 * To build for production:
 *   cd Workload && npm run build:sales-crm:prod
 */
import type { WorkloadConfig } from "../../../shared/types/workload";
import { createWorkloadFetch } from "../../../shared/utils/apiClient";

// ── Workload identity ─────────────────────────────────────────────────────────

export const WORKLOAD_ID = "sales-crm" as const;

// ── Entity catalog (locked — user cannot deselect) ────────────────────────────

export const SALES_CRM_WORKLOAD_CONFIG: WorkloadConfig = {
  id: WORKLOAD_ID,
  displayName: "Sales CRM",
  source: "crm",
  entities: [
    {
      logicalName: "lead",
      displayName: "Lead",
      bronzeTable: "bronze_crm/lead",
      locked: true,
    },
    {
      logicalName: "opportunity",
      displayName: "Opportunity",
      bronzeTable: "bronze_crm/opportunity",
      locked: true,
    },
    {
      logicalName: "account",
      displayName: "Account",
      bronzeTable: "bronze_crm/account",
      locked: true,
    },
    {
      logicalName: "contact",
      displayName: "Contact",
      bronzeTable: "bronze_crm/contact",
      locked: true,
    },
    {
      logicalName: "quote",
      displayName: "Quote",
      bronzeTable: "bronze_crm/quote",
      locked: true,
    },
    {
      logicalName: "salesorder",
      displayName: "Sales Order",
      bronzeTable: "bronze_crm/salesorder",
      locked: true,
    },
    {
      logicalName: "invoice",
      displayName: "Invoice",
      bronzeTable: "bronze_crm/invoice",
      locked: true,
    },
  ],
};

// ── Backend fetch client (X-Workload-Id pre-injected) ────────────────────────

/**
 * Pre-configured fetch function for Sales CRM backend calls.
 *
 * Automatically sets:
 *   - Content-Type: application/json
 *   - X-Workload-Id: sales-crm
 *
 * @example
 * const res = await salesCrmFetch("/v1/items/abc123/runs");
 * const runs = await res.json();
 */
export const salesCrmFetch = createWorkloadFetch(
  WORKLOAD_ID,
  process.env.REACT_APP_BACKEND_URL ?? "",
);
