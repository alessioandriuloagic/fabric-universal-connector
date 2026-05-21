/**
 * workloadConfig.ts
 *
 * Build-time workload identity and entity scope.
 *
 * Set REACT_APP_WORKLOAD_ID in the appropriate .env.* file to activate a
 * scoped workload.  Omitting the variable (or setting it to "universal")
 * preserves the original Universal Connector behaviour — all connectors
 * selectable, all entities user-configurable.
 *
 * Adding a new scoped workload: add an entry to CONFIGS below.
 * No other file needs to change.
 */
import {
  WizardState,
  INITIAL_WIZARD_STATE,
  WIZARD_STEPS,
} from "./wizard/wizardState";
import { buildDefaultConnectors } from "./wizard/connectorRegistry";
import { expandCrmEntities } from "./wizard/crmCatalog";

export interface WorkloadConfig {
  workloadId: string;
  /** true = scoped workload (fixed source + entities), false = Universal Connector */
  isScoped: boolean;
  lockedConnectorType?: "crm" | "businesscentral" | "sql";
  /** CRM_CATALOG keys for the locked entity set (used to build the initial state) */
  lockedEntityKeys?: string[];
  /** Human-readable labels for the locked entities (shown read-only in CONFIG step) */
  lockedEntityLabels?: string[];
  /** When true the CONNECTORS step is skipped; wizard starts at CONFIG */
  skipConnectorStep: boolean;
}

const CONFIGS: Record<string, WorkloadConfig> = {
  "customer-insight-journey": {
    workloadId: "customer-insight-journey",
    isScoped: true,
    lockedConnectorType: "crm",
    lockedEntityKeys: ["contact", "msdynmkt_email", "msdynmkt_journey"],
    lockedEntityLabels: [
      "Contact",
      "Marketing Email (Customer Insights Journey)",
      "Journey (Customer Insights Journey)",
    ],
    skipConnectorStep: true,
  },
  "sales-crm": {
    workloadId: "sales-crm",
    isScoped: true,
    lockedConnectorType: "crm",
    lockedEntityKeys: ["lead", "opportunity", "account", "contact", "quote", "salesorder", "invoice"],
    lockedEntityLabels: [
      "Lead",
      "Opportunity",
      "Account",
      "Contact",
      "Quote",
      "Sales Order",
      "Invoice",
    ],
    skipConnectorStep: true,
  },
  "business-central": {
    workloadId: "business-central",
    isScoped: true,
    lockedConnectorType: "businesscentral",
    lockedEntityKeys: [],
    lockedEntityLabels: [],
    skipConnectorStep: true,
  },
  "sql-db": {
    workloadId: "sql-db",
    isScoped: true,
    lockedConnectorType: "sql",
    lockedEntityKeys: [],
    lockedEntityLabels: [],
    skipConnectorStep: true,
  },
};

const WORKLOAD_ID: string =
  (process.env.REACT_APP_WORKLOAD_ID as string | undefined) ?? "universal";

export const WORKLOAD_CONFIG: WorkloadConfig =
  CONFIGS[WORKLOAD_ID] ?? {
    workloadId: "universal",
    isScoped: false,
    skipConnectorStep: false,
  };

/**
 * Returns the initial wizard state for the active workload.
 *
 * Scoped workload: locked connector pre-enabled, entities pre-filled, wizard
 * starts at the CONFIG step (CONNECTORS step is skipped entirely).
 *
 * Universal: standard INITIAL_WIZARD_STATE — no pre-selections.
 */
export function buildWorkloadInitialState(): WizardState {
  if (!WORKLOAD_CONFIG.isScoped || !WORKLOAD_CONFIG.lockedConnectorType) {
    return INITIAL_WIZARD_STATE;
  }

  const connectors = buildDefaultConnectors().map((c) => {
    if (c.connectorType !== WORKLOAD_CONFIG.lockedConnectorType) return c;
    const entities =
      WORKLOAD_CONFIG.lockedConnectorType === "crm"
        ? expandCrmEntities(WORKLOAD_CONFIG.lockedEntityKeys ?? [])
        : [];
    return { ...c, enabled: true, entities };
  });

  return {
    ...INITIAL_WIZARD_STATE,
    step: WIZARD_STEPS.CONFIG,
    connectors: connectors as WizardState["connectors"],
  };
}
