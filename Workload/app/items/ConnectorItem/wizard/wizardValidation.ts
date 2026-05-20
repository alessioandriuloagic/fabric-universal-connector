import { ConnectorEntry } from "../ConnectorItemDefinition";
import { CONNECTOR_REGISTRY } from "./connectorRegistry";
import { WizardState, WizardStep, WIZARD_STEPS } from "./wizardState";

export type ValidationResult = {
  isValid: boolean;
  errors: Record<string, string>;
};

/**
 * Validates the given wizard step and returns a flat error map.
 *
 * Per-connector validation in the CONFIG step delegates to each connector's
 * `validate` function in the registry, keeping this function connector-agnostic.
 */
export function validateStep(state: WizardState, step: WizardStep): ValidationResult {
  switch (step) {
    case WIZARD_STEPS.CONNECTORS: return validateConnectorsStep(state);
    case WIZARD_STEPS.CONFIG:     return validateConfigStep(state);
    case WIZARD_STEPS.STORAGE:    return validateStorageStep(state);
    case WIZARD_STEPS.SCHEDULE:   return validateScheduleStep(state);
    case WIZARD_STEPS.REVIEW:     return { isValid: true, errors: {} };
    default:                      return { isValid: true, errors: {} };
  }
}

function validateConnectorsStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (!state.connectors.some((c) => c.enabled)) {
    errors.connectors = "Select at least one connector to continue.";
  }
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateConfigStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  // Iterate enabled connectors and merge per-connector errors from the registry.
  // This loop is connector-agnostic; adding a new connector requires no change here.
  for (const entry of state.connectors) {
    if (!entry.enabled) continue;
    const def = CONNECTOR_REGISTRY.find((d) => d.type === entry.connectorType);
    if (!def) continue;
    Object.assign(errors, def.validate(entry));
  }
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateStorageStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (!state.storage.bronzeLakeHouseName) {
    errors.bronzeLakeHouseName = "Lakehouse name is required.";
  }
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateScheduleStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (!state.schedule.scheduleType) {
    errors.scheduleType = "Schedule type is required.";
  }
  if (state.schedule.scheduleType === "cron" && !state.schedule.cronExpression) {
    errors.cronExpression = "Cron expression is required.";
  }
  if (state.schedule.scheduleType === "interval" && !state.schedule.intervalMinutes) {
    errors.intervalMinutes = "Interval in minutes is required.";
  }
  return { isValid: Object.keys(errors).length === 0, errors };
}

/**
 * Recomputes the `status` field on each connector entry using registry validators.
 *
 * Call this after leaving Step 2 (CONFIG) to refresh the status badges shown
 * in the review step and on the connector selection cards.
 */
export function recomputeConnectorStatuses(
  connectors: ConnectorEntry[],
): ConnectorEntry[] {
  return connectors.map((entry) => {
    if (!entry.enabled) return { ...entry, status: "unconfigured" } as ConnectorEntry;
    const def = CONNECTOR_REGISTRY.find((d) => d.type === entry.connectorType);
    if (!def) return entry;
    const hasErrors = Object.keys(def.validate(entry)).length > 0;
    return { ...entry, status: hasErrors ? "error" : "valid" } as ConnectorEntry;
  });
}
