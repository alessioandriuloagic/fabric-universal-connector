import {
  ModuleType,
  CrmSourceConfiguration,
  BusinessCentralSourceConfiguration,
  SqlSourceConfiguration,
  StorageConfiguration,
  SchedulingConfiguration,
} from "../ConnectorItemDefinition";

/** Identifier constants for each step in the 7-step configuration wizard. */
export const WIZARD_STEPS = {
  /** Step 1 – choose the data source module (CRM / Business Central / SQL). */
  MODULE:    "wizard-module",
  /** Step 2 – enter source connection parameters (URL, server, environment). */
  SOURCE:    "wizard-source",
  /** Step 3 – configure credentials (Fabric Connection / Key Vault / Service Principal). */
  AUTH:      "wizard-auth",
  /** Step 4 – select entities / tables to extract. */
  ENTITIES:  "wizard-entities",
  /** Step 5 – choose or create the destination Bronze Lakehouse. */
  STORAGE:   "wizard-storage",
  /** Step 6 – configure automated run schedule (cron or interval). */
  SCHEDULE:  "wizard-schedule",
  /** Step 7 – review configuration before activating the connector. */
  REVIEW:    "wizard-review",
} as const;

export type WizardStep = typeof WIZARD_STEPS[keyof typeof WIZARD_STEPS];

/** Ordered sequence of wizard steps; used to navigate forward and backward. */
export const WIZARD_STEP_ORDER: WizardStep[] = [
  WIZARD_STEPS.MODULE,
  WIZARD_STEPS.SOURCE,
  WIZARD_STEPS.AUTH,
  WIZARD_STEPS.ENTITIES,
  WIZARD_STEPS.STORAGE,
  WIZARD_STEPS.SCHEDULE,
  WIZARD_STEPS.REVIEW,
];

/** Authentication fields collected during the wizard's Auth step. */
export interface WizardAuthData {
  /** Selected authentication strategy; null until the user makes a choice. */
  mode: "fabric_connection" | "keyvault_reference" | "service_principal" | null;
  /** Fabric Connection ID (used when mode is "fabric_connection"). */
  fabricConnectionId?: string;
  /** Key Vault base URI (used when mode is "keyvault_reference"). */
  keyVaultUri?: string;
  /** Name of the Key Vault secret containing the client secret. */
  clientSecretName?: string;
  /** Entra tenant ID (used when mode is "service_principal"). */
  tenantId?: string;
  /** Entra application (client) ID (used when mode is "service_principal"). */
  clientId?: string;
}

/** Transient state for the 7-step configuration wizard, held in component state only. */
export interface WizardState {
  /** Currently rendered wizard step. */
  step: WizardStep;
  /** Module type chosen in Step 1; null until selected. */
  moduleType: ModuleType | null;
  /** Partial source configuration accumulated across steps. */
  source: Partial<CrmSourceConfiguration & BusinessCentralSourceConfiguration & SqlSourceConfiguration>;
  /** Authentication data collected in Step 3. */
  auth: WizardAuthData;
  /** Logical names / table names selected in Step 4. */
  selectedEntities: string[];
  /** Storage settings collected in Step 5. */
  storage: Partial<StorageConfiguration>;
  /** Schedule settings collected in Step 6. */
  schedule: Partial<SchedulingConfiguration>;
  /** Field-level validation errors keyed by field name; shown inline in each step. */
  validationErrors: Record<string, string>;
  /** True while the activation API call is in flight; disables the "Activate" button. */
  isActivating: boolean;
}

export const INITIAL_WIZARD_STATE: WizardState = {
  step: WIZARD_STEPS.MODULE,
  moduleType: null,
  source: {},
  auth: { mode: null },
  selectedEntities: [],
  storage: {
    bronzeLakeHouseName: "FabricUniversalConnector-Bronze",
    schemaEvolutionPolicy: "merge",
    useExistingLakehouse: false,
  },
  schedule: {
    scheduleType: "cron",
    cronExpression: "0 2 * * *",
    timezone: "UTC",
    enabled: true,
  },
  validationErrors: {},
  isActivating: false,
};

export function getNextStep(current: WizardStep): WizardStep | null {
  const idx = WIZARD_STEP_ORDER.indexOf(current);
  return idx < WIZARD_STEP_ORDER.length - 1 ? WIZARD_STEP_ORDER[idx + 1] : null;
}

export function getPrevStep(current: WizardStep): WizardStep | null {
  const idx = WIZARD_STEP_ORDER.indexOf(current);
  return idx > 0 ? WIZARD_STEP_ORDER[idx - 1] : null;
}

// Common props interface used by all 7 wizard step components
export interface WizardStepProps {
  wizardState: WizardState;
  onUpdate: (patch: Partial<WizardState>) => void;
  validationErrors: Record<string, string>;
  onActivate?: () => Promise<void>;
}
