/**
 * shared/hooks/useWorkload.ts
 *
 * React hook that returns the WorkloadConfig for a given WorkloadId.
 *
 * The registry is the single source of truth for workload metadata on the
 * frontend. It mirrors the backend workload_config/ Python modules so that
 * both sides stay in sync.
 *
 * Usage:
 *   const config = useWorkload("customer-insight-journey");
 *   console.log(config.entities); // pre-defined locked entities
 *
 * When to update the registry:
 *   - New workload added → add entry here + backend workload_config/*.py
 *   - Entity list changes → update both here and backend
 */
import { useMemo } from "react";
import type { WorkloadId, WorkloadConfig, EntityDefinition } from "../types/workload";

// ── Customer Insight Journey entities ─────────────────────────────────────────

const CIJ_ENTITIES: EntityDefinition[] = [
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
];

// ── Sales CRM entities ────────────────────────────────────────────────────────

const SALES_CRM_ENTITIES: EntityDefinition[] = [
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
];

// ── Business Central entities ─────────────────────────────────────────────────
// BC uses logicalName as the OData api_endpoint segment.

const BC_ENTITIES: EntityDefinition[] = [
  {
    logicalName: "customers",
    displayName: "Customer",
    bronzeTable: "bronze_bc/customers",
  },
  {
    logicalName: "vendors",
    displayName: "Vendor",
    bronzeTable: "bronze_bc/vendors",
  },
  {
    logicalName: "items",
    displayName: "Item",
    bronzeTable: "bronze_bc/items",
  },
  {
    logicalName: "salesOrders",
    displayName: "Sales Order",
    bronzeTable: "bronze_bc/salesOrders",
  },
  {
    logicalName: "salesInvoices",
    displayName: "Sales Invoice",
    bronzeTable: "bronze_bc/salesInvoices",
  },
  {
    logicalName: "purchaseOrders",
    displayName: "Purchase Order",
    bronzeTable: "bronze_bc/purchaseOrders",
  },
  {
    logicalName: "purchaseInvoices",
    displayName: "Purchase Invoice",
    bronzeTable: "bronze_bc/purchaseInvoices",
  },
  {
    logicalName: "generalLedgerEntries",
    displayName: "General Ledger Entry",
    bronzeTable: "bronze_bc/generalLedgerEntries",
  },
  {
    logicalName: "accounts",
    displayName: "Account (G/L)",
    bronzeTable: "bronze_bc/accounts",
  },
  {
    logicalName: "contacts",
    displayName: "Contact",
    bronzeTable: "bronze_bc/contacts",
  },
];

// ── Workload registry ─────────────────────────────────────────────────────────

const WORKLOAD_REGISTRY: Readonly<Record<string, WorkloadConfig>> = {
  "customer-insight-journey": {
    id: "customer-insight-journey",
    displayName: "Customer Insight Journey",
    source: "crm",
    entities: CIJ_ENTITIES,
  },
  "sales-crm": {
    id: "sales-crm",
    displayName: "Sales CRM",
    source: "crm",
    entities: SALES_CRM_ENTITIES,
  },
  "business-central": {
    id: "business-central",
    displayName: "Business Central",
    source: "businesscentral",
    entities: BC_ENTITIES,
  },
  "sql-db": {
    id: "sql-db",
    displayName: "SQL DB Connector",
    source: "sql",
    entities: [], // User-defined tables — no pre-defined entity list
  },
  universal: {
    id: "universal",
    displayName: "Universal Connector",
    source: "crm",
    entities: [], // No restriction — all entities configurable
  },
};

// ── Hook ──────────────────────────────────────────────────────────────────────

/**
 * Returns the WorkloadConfig for the given workload ID.
 *
 * Falls back to the "universal" config for unknown IDs.
 * Result is memoized and only recomputes when `workloadId` changes.
 *
 * @param workloadId - One of the registered WorkloadId values.
 */
export function useWorkload(workloadId: WorkloadId): WorkloadConfig {
  return useMemo(
    () => WORKLOAD_REGISTRY[workloadId] ?? WORKLOAD_REGISTRY["universal"],
    [workloadId],
  );
}

/**
 * Synchronous helper for non-component contexts (e.g., controller code).
 * Returns the WorkloadConfig without requiring a React component tree.
 */
export function getWorkloadConfig(workloadId: WorkloadId): WorkloadConfig {
  return WORKLOAD_REGISTRY[workloadId] ?? WORKLOAD_REGISTRY["universal"];
}
