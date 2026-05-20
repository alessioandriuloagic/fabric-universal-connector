import {
  ConnectorEntry,
  StorageConfiguration,
  SchedulingConfiguration,
} from "../ConnectorItemDefinition";
import { buildDefaultConnectors } from "./connectorRegistry";

/**
 * Identifier constants for each step in the 5-step configuration wizard.
 *
 * Wizard flow (v2 multi-connector):
 *   1. CONNECTORS — multi-select toggle cards (replaces single radio MODULE step)
 *   2. CONFIG     — per-connector config panels (source + auth + entities per enabled connector)
 *   3. STORAGE    — shared Bronze Lakehouse settings
 *   4. SCHEDULE   — shared ingestion schedule
 *   5. REVIEW     — summary + activate button
 */
export const WIZARD_STEPS = {
  /** Step 1 – enable/disable connectors via toggle cards (multi-select). */
  CONNECTORS: "wizard-connectors",
  /** Step 2 – source, auth and entity configuration for each enabled connector. */
  CONFIG:     "wizard-config",
  /** Step 3 – choose or create the destination Bronze Lakehouse (shared). */
  STORAGE:    "wizard-storage",
  /** Step 4 – configure automated run schedule (shared). */
  SCHEDULE:   "wizard-schedule",
  /** Step 5 – review configuration before activating. */
  REVIEW:     "wizard-review",
} as const;

export type WizardStep = typeof WIZARD_STEPS[keyof typeof WIZARD_STEPS];

/** Ordered sequence of wizard steps; used to navigate forward and backward. */
export const WIZARD_STEP_ORDER: WizardStep[] = [
  WIZARD_STEPS.CONNECTORS,
  WIZARD_STEPS.CONFIG,
  WIZARD_STEPS.STORAGE,
  WIZARD_STEPS.SCHEDULE,
  WIZARD_STEPS.REVIEW,
];

/**
 * Transient state for the 5-step configuration wizard, held in component state only.
 *
 * Key change from v1 wizard state:
 *   `connectors` replaces `moduleType`, `source`, `auth` and `selectedEntities`.
 *   Each element of `connectors` is an independent `ConnectorEntry` so that
 *   source, auth and entity settings are isolated per connector type.
 */
export interface WizardState {
  /** Currently rendered wizard step. */
  step: WizardStep;
  /**
   * Per-connector configuration — one entry per registered connector type.
   * Entries with `enabled: false` appear as inactive toggle cards in Step 1
   * and are excluded from validation and activation.
   */
  connectors: ConnectorEntry[];
  /** Shared storage settings collected in Step 3. */
  storage: Partial<StorageConfiguration>;
  /** Shared schedule settings collected in Step 4. */
  schedule: Partial<SchedulingConfiguration>;
  /** Field-level validation errors keyed by "<connectorType>.<field>"; shown inline. */
  validationErrors: Record<string, string>;
  /** True while the activation API call is in flight; disables the "Activate" button. */
  isActivating: boolean;
}

export const INITIAL_WIZARD_STATE: WizardState = {
  step: WIZARD_STEPS.CONNECTORS,
  // Initialise from the registry so new connector types appear automatically
  connectors: buildDefaultConnectors(),
  storage: {
    bronzeLakeHouseName: "Timevision-Bronze",
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

/** Common props interface shared by all 5 wizard step components. */
export interface WizardStepProps {
  wizardState: WizardState;
  onUpdate: (patch: Partial<WizardState>) => void;
  validationErrors: Record<string, string>;
  onActivate?: () => Promise<void>;
}
