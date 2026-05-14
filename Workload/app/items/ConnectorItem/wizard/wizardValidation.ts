import { WizardState, WizardStep, WIZARD_STEPS } from "./wizardState";

export type ValidationResult = {
  isValid: boolean;
  errors: Record<string, string>;
};

export function validateStep(state: WizardState, step: WizardStep): ValidationResult {
  switch (step) {
    case WIZARD_STEPS.MODULE:   return validateModuleStep(state);
    case WIZARD_STEPS.SOURCE:   return validateSourceStep(state);
    case WIZARD_STEPS.AUTH:     return validateAuthStep(state);
    case WIZARD_STEPS.ENTITIES: return validateEntitiesStep(state);
    case WIZARD_STEPS.STORAGE:  return validateStorageStep(state);
    case WIZARD_STEPS.SCHEDULE: return validateScheduleStep(state);
    case WIZARD_STEPS.REVIEW:   return validateReviewStep(state);
    default:                    return { isValid: true, errors: {} };
  }
}

function validateModuleStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (!state.moduleType) errors.moduleType = "Please select a module type.";
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateSourceStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (state.moduleType === "crm") {
    if (!state.source.environmentUrl) errors.environmentUrl = "Environment URL is required.";
    if (!state.source.tenantId) errors.tenantId = "Tenant ID is required.";
  }
  if (state.moduleType === "businesscentral") {
    if (!state.source.tenantId) errors.tenantId = "Tenant ID is required.";
    if (!state.source.environment) errors.environment = "Environment name is required.";
  }
  if (state.moduleType === "sql") {
    if (!state.source.server) errors.server = "Server hostname is required.";
    if (!state.source.database) errors.database = "Database name is required.";
  }
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateAuthStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (!state.auth.mode) {
    errors.mode = "Please select an authentication method.";
    return { isValid: false, errors };
  }
  if (state.auth.mode === "fabric_connection" && !state.auth.fabricConnectionId) {
    errors.fabricConnectionId = "Please select a Fabric Connection.";
  }
  if (state.auth.mode === "keyvault_reference") {
    if (!state.auth.keyVaultUri) errors.keyVaultUri = "Key Vault URI is required.";
    if (!state.auth.clientSecretName) errors.clientSecretName = "Secret name is required.";
  }
  if (state.auth.mode === "service_principal") {
    if (!state.auth.tenantId) errors.tenantId = "Tenant ID is required.";
    if (!state.auth.clientId) errors.clientId = "Client ID is required.";
  }
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateEntitiesStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (state.selectedEntities.length === 0) {
    errors.entities = "At least one entity must be selected.";
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

function validateReviewStep(_state: WizardState): ValidationResult {
  return { isValid: true, errors: {} };
}
