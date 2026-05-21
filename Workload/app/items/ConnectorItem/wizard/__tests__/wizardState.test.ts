/**
 * app/items/ConnectorItem/wizard/__tests__/wizardState.test.ts
 *
 * Unit tests for wizardState helpers and the validation layer.
 * No DOM required — pure TypeScript logic.
 */
import {
  getNextStep,
  getPrevStep,
  WIZARD_STEPS,
  WIZARD_STEP_ORDER,
  INITIAL_WIZARD_STATE,
  WizardState,
} from "../wizardState";
import { validateStep } from "../wizardValidation";

// ── Step navigation ───────────────────────────────────────────────────────────

describe("getNextStep", () => {
  it("returns the next step in order", () => {
    expect(getNextStep(WIZARD_STEPS.CONNECTORS)).toBe(WIZARD_STEPS.CONFIG);
    expect(getNextStep(WIZARD_STEPS.CONFIG)).toBe(WIZARD_STEPS.STORAGE);
    expect(getNextStep(WIZARD_STEPS.STORAGE)).toBe(WIZARD_STEPS.SCHEDULE);
    expect(getNextStep(WIZARD_STEPS.SCHEDULE)).toBe(WIZARD_STEPS.REVIEW);
  });

  it("returns null from the last step", () => {
    expect(getNextStep(WIZARD_STEPS.REVIEW)).toBeNull();
  });
});

describe("getPrevStep", () => {
  it("returns the previous step in order", () => {
    expect(getPrevStep(WIZARD_STEPS.REVIEW)).toBe(WIZARD_STEPS.SCHEDULE);
    expect(getPrevStep(WIZARD_STEPS.SCHEDULE)).toBe(WIZARD_STEPS.STORAGE);
    expect(getPrevStep(WIZARD_STEPS.STORAGE)).toBe(WIZARD_STEPS.CONFIG);
    expect(getPrevStep(WIZARD_STEPS.CONFIG)).toBe(WIZARD_STEPS.CONNECTORS);
  });

  it("returns null from the first step", () => {
    expect(getPrevStep(WIZARD_STEPS.CONNECTORS)).toBeNull();
  });
});

describe("WIZARD_STEP_ORDER", () => {
  it("starts with CONNECTORS and ends with REVIEW", () => {
    expect(WIZARD_STEP_ORDER[0]).toBe(WIZARD_STEPS.CONNECTORS);
    expect(WIZARD_STEP_ORDER[WIZARD_STEP_ORDER.length - 1]).toBe(WIZARD_STEPS.REVIEW);
  });

  it("has exactly 5 steps", () => {
    expect(WIZARD_STEP_ORDER).toHaveLength(5);
  });

  it("contains all WIZARD_STEPS values", () => {
    const allSteps = Object.values(WIZARD_STEPS);
    expect(WIZARD_STEP_ORDER).toEqual(expect.arrayContaining(allSteps));
  });
});

// ── INITIAL_WIZARD_STATE ──────────────────────────────────────────────────────

describe("INITIAL_WIZARD_STATE", () => {
  it("starts at the CONNECTORS step", () => {
    expect(INITIAL_WIZARD_STATE.step).toBe(WIZARD_STEPS.CONNECTORS);
  });

  it("has no validation errors", () => {
    expect(INITIAL_WIZARD_STATE.validationErrors).toEqual({});
  });

  it("is not activating", () => {
    expect(INITIAL_WIZARD_STATE.isActivating).toBe(false);
  });

  it("has at least one connector registered", () => {
    expect(INITIAL_WIZARD_STATE.connectors.length).toBeGreaterThan(0);
  });

  it("has pre-configured storage defaults", () => {
    expect(INITIAL_WIZARD_STATE.storage.bronzeLakeHouseName).toBeTruthy();
    expect(INITIAL_WIZARD_STATE.storage.schemaEvolutionPolicy).toBe("merge");
  });

  it("has pre-configured schedule defaults", () => {
    expect(INITIAL_WIZARD_STATE.schedule.scheduleType).toBe("cron");
    expect(INITIAL_WIZARD_STATE.schedule.cronExpression).toBeTruthy();
    expect(INITIAL_WIZARD_STATE.schedule.enabled).toBe(true);
  });
});

// ── validateStep — CONNECTORS step ───────────────────────────────────────────

describe("validateStep (CONNECTORS)", () => {
  it("is invalid when no connectors are enabled", () => {
    const state: WizardState = {
      ...INITIAL_WIZARD_STATE,
      connectors: INITIAL_WIZARD_STATE.connectors.map((c) => ({
        ...c,
        enabled: false,
      })),
    };
    const result = validateStep(state, WIZARD_STEPS.CONNECTORS);
    expect(result.isValid).toBe(false);
    expect(result.errors.connectors).toBeTruthy();
  });

  it("is valid when at least one connector is enabled", () => {
    const state: WizardState = {
      ...INITIAL_WIZARD_STATE,
      connectors: INITIAL_WIZARD_STATE.connectors.map((c, i) => ({
        ...c,
        enabled: i === 0, // enable only the first
      })),
    };
    const result = validateStep(state, WIZARD_STEPS.CONNECTORS);
    expect(result.isValid).toBe(true);
  });
});

// ── validateStep — STORAGE step ───────────────────────────────────────────────

describe("validateStep (STORAGE)", () => {
  it("is invalid when bronzeLakeHouseName is missing", () => {
    const state: WizardState = {
      ...INITIAL_WIZARD_STATE,
      storage: { ...INITIAL_WIZARD_STATE.storage, bronzeLakeHouseName: "" },
    };
    const result = validateStep(state, WIZARD_STEPS.STORAGE);
    expect(result.isValid).toBe(false);
    expect(result.errors.bronzeLakeHouseName).toBeTruthy();
  });

  it("is valid when bronzeLakeHouseName is set", () => {
    const result = validateStep(INITIAL_WIZARD_STATE, WIZARD_STEPS.STORAGE);
    expect(result.isValid).toBe(true);
  });
});

// ── validateStep — SCHEDULE step ─────────────────────────────────────────────

describe("validateStep (SCHEDULE)", () => {
  it("is invalid when scheduleType is missing", () => {
    const state: WizardState = {
      ...INITIAL_WIZARD_STATE,
      schedule: { ...INITIAL_WIZARD_STATE.schedule, scheduleType: undefined },
    };
    const result = validateStep(state, WIZARD_STEPS.SCHEDULE);
    expect(result.isValid).toBe(false);
    expect(result.errors.scheduleType).toBeTruthy();
  });

  it("is invalid when cron expression is empty for cron schedule", () => {
    const state: WizardState = {
      ...INITIAL_WIZARD_STATE,
      schedule: { scheduleType: "cron", cronExpression: "" },
    };
    const result = validateStep(state, WIZARD_STEPS.SCHEDULE);
    expect(result.isValid).toBe(false);
    expect(result.errors.cronExpression).toBeTruthy();
  });

  it("is valid for default initial state schedule", () => {
    const result = validateStep(INITIAL_WIZARD_STATE, WIZARD_STEPS.SCHEDULE);
    expect(result.isValid).toBe(true);
  });
});

// ── validateStep — REVIEW step ────────────────────────────────────────────────

describe("validateStep (REVIEW)", () => {
  it("is always valid", () => {
    const result = validateStep(INITIAL_WIZARD_STATE, WIZARD_STEPS.REVIEW);
    expect(result.isValid).toBe(true);
    expect(result.errors).toEqual({});
  });
});
