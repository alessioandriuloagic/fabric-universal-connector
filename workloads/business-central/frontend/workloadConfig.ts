/**
 * workloads/business-central/frontend/workloadConfig.ts
 *
 * Business Central workload configuration.
 *
 * Source system: Dynamics 365 Business Central (OData v4).
 * The full entity catalog mirrors backend/app/workload_config/business_central.py.
 *
 * All entities are pre-selected and locked (no user deselection) because this
 * workload ingests the complete standard BC REST API v2.0 entity set.
 *
 * To run locally in BC mode:
 *   cd Workload && npm run start:business-central
 *
 * To build for production:
 *   cd Workload && npm run build:business-central:prod
 */
import type { WorkloadConfig } from "../../../shared/types/workload";
import { createWorkloadFetch } from "../../../shared/utils/apiClient";

// ── Workload identity ─────────────────────────────────────────────────────────

export const WORKLOAD_ID = "business-central" as const;

// ── Entity catalog (locked — user cannot deselect) ────────────────────────────

export const BC_WORKLOAD_CONFIG: WorkloadConfig = {
  id: WORKLOAD_ID,
  displayName: "Business Central",
  source: "businesscentral",
  entities: [
    {
      logicalName: "customers",
      displayName: "Customer",
      bronzeTable: "bronze_bc/customers",
      locked: true,
    },
    {
      logicalName: "vendors",
      displayName: "Vendor",
      bronzeTable: "bronze_bc/vendors",
      locked: true,
    },
    {
      logicalName: "items",
      displayName: "Item",
      bronzeTable: "bronze_bc/items",
      locked: true,
    },
    {
      logicalName: "salesOrders",
      displayName: "Sales Order",
      bronzeTable: "bronze_bc/salesOrders",
      locked: true,
    },
    {
      logicalName: "salesOrderLines",
      displayName: "Sales Order Line",
      bronzeTable: "bronze_bc/salesOrderLines",
      locked: true,
    },
    {
      logicalName: "salesInvoices",
      displayName: "Sales Invoice",
      bronzeTable: "bronze_bc/salesInvoices",
      locked: true,
    },
    {
      logicalName: "salesInvoiceLines",
      displayName: "Sales Invoice Line",
      bronzeTable: "bronze_bc/salesInvoiceLines",
      locked: true,
    },
    {
      logicalName: "purchaseOrders",
      displayName: "Purchase Order",
      bronzeTable: "bronze_bc/purchaseOrders",
      locked: true,
    },
    {
      logicalName: "purchaseOrderLines",
      displayName: "Purchase Order Line",
      bronzeTable: "bronze_bc/purchaseOrderLines",
      locked: true,
    },
    {
      logicalName: "purchaseInvoices",
      displayName: "Purchase Invoice",
      bronzeTable: "bronze_bc/purchaseInvoices",
      locked: true,
    },
    {
      logicalName: "generalLedgerEntries",
      displayName: "General Ledger Entry",
      bronzeTable: "bronze_bc/generalLedgerEntries",
      locked: true,
    },
    {
      logicalName: "accounts",
      displayName: "Account (Chart of Accounts)",
      bronzeTable: "bronze_bc/accounts",
      locked: true,
    },
    {
      logicalName: "employees",
      displayName: "Employee",
      bronzeTable: "bronze_bc/employees",
      locked: true,
    },
    {
      logicalName: "contacts",
      displayName: "Contact",
      bronzeTable: "bronze_bc/contacts",
      locked: true,
    },
  ],
};

// ── Backend fetch client (X-Workload-Id pre-injected) ────────────────────────

/**
 * Pre-configured fetch function for Business Central backend calls.
 *
 * Automatically sets:
 *   - Content-Type: application/json
 *   - X-Workload-Id: business-central
 *
 * @example
 * const res = await bcFetch("/v1/items/abc123/runs");
 * const runs = await res.json();
 */
export const bcFetch = createWorkloadFetch(
  WORKLOAD_ID,
  process.env.REACT_APP_BACKEND_URL ?? "",
);
