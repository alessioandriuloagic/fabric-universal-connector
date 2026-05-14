import {
  ModuleType,
  CrmSourceConfiguration,
  BusinessCentralSourceConfiguration,
  SqlSourceConfiguration,
  StorageConfiguration,
  SchedulingConfiguration,
} from "../ConnectorItemDefinition";

export const WIZARD_STEPS = {
  MODULE:    "wizard-module",
  SOURCE:    "wizard-source",
  AUTH:      "wizard-auth",
  ENTITIES:  "wizard-entities",
  STORAGE:   "wizard-storage",
  SCHEDULE:  "wizard-schedule",
  REVIEW:    "wizard-review",
} as const;

export type WizardStep = typeof WIZARD_STEPS[keyof typeof WIZARD_STEPS];

export const WIZARD_STEP_ORDER: WizardStep[] = [
  WIZARD_STEPS.MODULE,
  WIZARD_STEPS.SOURCE,
  WIZARD_STEPS.AUTH,
  WIZARD_STEPS.ENTITIES,
  WIZARD_STEPS.STORAGE,
  WIZARD_STEPS.SCHEDULE,
  WIZARD_STEPS.REVIEW,
];

export interface WizardAuthData {
  mode: "fabric_connection" | "keyvault_reference" | "service_principal" | null;
  fabricConnectionId?: string;
  keyVaultUri?: string;
  clientSecretName?: string;
  tenantId?: string;
  clientId?: string;
}

export interface WizardState {
  step: WizardStep;
  moduleType: ModuleType | null;
  source: Partial<CrmSourceConfiguration & BusinessCentralSourceConfiguration & SqlSourceConfiguration>;
  auth: WizardAuthData;
  selectedEntities: string[];
  storage: Partial<StorageConfiguration>;
  schedule: Partial<SchedulingConfiguration>;
  validationErrors: Record<string, string>;
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
}
