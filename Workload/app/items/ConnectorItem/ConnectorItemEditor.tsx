import React, { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button, MessageBar, MessageBarBody, MessageBarTitle } from "@fluentui/react-components";
import { WorkloadClientAPI, NotificationType, NotificationToastDuration } from "@ms-fabric/workload-client";
import { callNotificationOpen } from "../../controller/NotificationController";
import { PageProps, ContextProps } from "../../App";
import {
  ItemWithDefinition,
  getWorkloadItem,
  saveItemDefinition,
} from "../../controller/ItemCRUDController";
import { callOpenSettings } from "../../controller/SettingsController";
import {
  ItemEditor,
  useViewNavigation,
  RegisteredNotification,
  RegisteredView,
} from "../../components/ItemEditor";

import {
  MultiConnectorItemDefinition,
  AnyConnectorItemDefinition,
  ConnectorRun,
  EntityWatermark,
} from "./ConnectorItemDefinition";
import { normalizeToV2 } from "./wizard/migrationAdapter";
import { recomputeConnectorStatuses, validateStep } from "./wizard/wizardValidation";
import { ConnectorItemEmptyView } from "./ConnectorItemEmptyView";
import { ConnectorItemRibbon } from "./ribbon/ConnectorItemRibbon";
import { WizardConnectorStep } from "./wizard/WizardConnectorStep";
import { WizardConfigStep } from "./wizard/WizardConfigStep";
import { WizardStorageStep } from "./wizard/WizardStorageStep";
import { WizardScheduleStep } from "./wizard/WizardScheduleStep";
import { WizardReviewStep } from "./wizard/WizardReviewStep";
import { ConnectorDashboard } from "./dashboard/ConnectorDashboard";
import { RunDetailView } from "./dashboard/RunDetailView";
import { EntityDetailView } from "./dashboard/EntityDetailView";
import {
  WizardState,
  WIZARD_STEPS,
  WIZARD_STEP_ORDER,
  WizardStep,
} from "./wizard/wizardState";
import { WORKLOAD_CONFIG, buildWorkloadInitialState, buildWizardStateFromDefinition } from "./workloadConfig";
import "./ConnectorItem.scss";

export const VIEWS = {
  EMPTY:         "empty",
  WIZARD:        "wizard",
  DASHBOARD:     "dashboard",
  RUN_DETAIL:    "run-detail",
  ENTITY_DETAIL: "entity-detail",
} as const;

// ── Error boundary for wizard and dashboard views ─────────────────────────────

interface ErrorBoundaryState { hasError: boolean; }

class ConnectorErrorBoundary extends React.Component<
  React.PropsWithChildren<{ label: string }>,
  ErrorBoundaryState
> {
  constructor(props: React.PropsWithChildren<{ label: string }>) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(`[ConnectorErrorBoundary:${this.props.label}]`, error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 24 }}>
          <MessageBar intent="error">
            <MessageBarBody>
              <MessageBarTitle>Something went wrong</MessageBarTitle>
              An unexpected error occurred in the {this.props.label}. Reload the page to try again.
            </MessageBarBody>
          </MessageBar>
        </div>
      );
    }
    return this.props.children;
  }
}

// ── Shared editor context ──────────────────────────────────────────────────────
// Placing view components and the context at module level (outside ConnectorItemEditor)
// ensures their function references are stable across re-renders, preventing React
// from unmounting/remounting them on every state update (which caused focus loss in
// text inputs and configuration resets).

interface ConnectorEditorCtxValue {
  workloadClient: WorkloadClientAPI;
  item: ItemWithDefinition<MultiConnectorItemDefinition> | undefined;
  setItem: React.Dispatch<React.SetStateAction<ItemWithDefinition<MultiConnectorItemDefinition> | undefined>>;
  wizardState: WizardState;
  updateWizard: (patch: Partial<WizardState>) => void;
  setWizardState: React.Dispatch<React.SetStateAction<WizardState>>;
  isLoading: boolean;
  runs: ConnectorRun[];
  watermarks: EntityWatermark[];
  selectedRunId: string | null;
  setSelectedRunId: React.Dispatch<React.SetStateAction<string | null>>;
  selectedEntityName: string | null;
  setSelectedEntityName: React.Dispatch<React.SetStateAction<string | null>>;
  handleActivate: () => Promise<void>;
}

const ConnectorEditorCtx = React.createContext<ConnectorEditorCtxValue | null>(null);

function useConnectorEditorCtx(): ConnectorEditorCtxValue {
  const ctx = React.useContext(ConnectorEditorCtx);
  if (!ctx) throw new Error("ConnectorEditorCtx not provided");
  return ctx;
}

// ── Module-level view wrappers (stable component types) ───────────────────────

const EmptyViewWrapper: React.FC = () => {
  const { workloadClient, item, setWizardState } = useConnectorEditorCtx();
  const { setCurrentView } = useViewNavigation();
  return (
    <ConnectorItemEmptyView
      workloadClient={workloadClient}
      item={item}
      onConfigure={() => {
        setWizardState(buildWorkloadInitialState());
        setCurrentView(VIEWS.WIZARD);
      }}
    />
  );
};

const WizardViewWrapper: React.FC = () => {
  const { wizardState, updateWizard, handleActivate } = useConnectorEditorCtx();
  const { setCurrentView } = useViewNavigation();
  const { t } = useTranslation();

  const effectiveStepOrder: WizardStep[] = WORKLOAD_CONFIG.skipConnectorStep
    ? [WIZARD_STEPS.CONFIG, WIZARD_STEPS.STORAGE, WIZARD_STEPS.SCHEDULE, WIZARD_STEPS.REVIEW]
    : WIZARD_STEP_ORDER;

  const localNext = (step: WizardStep): WizardStep | null => {
    const idx = effectiveStepOrder.indexOf(step);
    return idx < effectiveStepOrder.length - 1 ? effectiveStepOrder[idx + 1] : null;
  };
  const localPrev = (step: WizardStep): WizardStep | null => {
    const idx = effectiveStepOrder.indexOf(step);
    return idx > 0 ? effectiveStepOrder[idx - 1] : null;
  };

  const isFirstStep = wizardState.step === effectiveStepOrder[0];
  const isReviewStep = wizardState.step === WIZARD_STEPS.REVIEW;

  const commonProps = {
    wizardState,
    onUpdate: updateWizard,
    validationErrors: wizardState.validationErrors,
  };

  const handleNext = () => {
    const { isValid, errors } = validateStep(wizardState, wizardState.step);
    if (!isValid) {
      updateWizard({ validationErrors: errors });
      return;
    }
    updateWizard({ validationErrors: {} });
    const next = localNext(wizardState.step);
    if (next) {
      if (wizardState.step === WIZARD_STEPS.CONFIG) {
        updateWizard({
          step: next,
          connectors: recomputeConnectorStatuses(wizardState.connectors),
        });
      } else {
        updateWizard({ step: next });
      }
    }
  };

  const handlePrev = () => {
    const prev = localPrev(wizardState.step);
    if (prev) {
      updateWizard({ step: prev });
    } else {
      setCurrentView(VIEWS.EMPTY);
    }
  };

  const handleActivateAndNavigate = async () => {
    await handleActivate();
    setCurrentView(VIEWS.DASHBOARD);
  };

  const stepIndex = effectiveStepOrder.indexOf(wizardState.step);
  const totalSteps = effectiveStepOrder.length;
  const hasEnabledConnector = wizardState.connectors.some((c) => c.enabled);

  const renderStep = () => {
    switch (wizardState.step) {
      case WIZARD_STEPS.CONNECTORS: return <WizardConnectorStep {...commonProps} />;
      case WIZARD_STEPS.CONFIG:     return <WizardConfigStep    {...commonProps} />;
      case WIZARD_STEPS.STORAGE:    return <WizardStorageStep   {...commonProps} />;
      case WIZARD_STEPS.SCHEDULE:   return <WizardScheduleStep  {...commonProps} />;
      case WIZARD_STEPS.REVIEW:     return (
        <WizardReviewStep {...commonProps} onActivate={handleActivateAndNavigate} />
      );
      default: return null;
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100%" }}>
      <div style={{ padding: "8px 24px", color: "var(--colorNeutralForeground3)", fontSize: 12 }}>
        {t("Wizard_StepCounter", "Step {{current}} of {{total}}", {
          current: stepIndex + 1,
          total: totalSteps,
        })}
      </div>
      <div style={{ flex: 1 }}>
        {renderStep()}
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          padding: "16px 24px",
          borderTop: "1px solid var(--colorNeutralStroke1)",
          marginTop: 16,
        }}
      >
        <Button appearance="secondary" onClick={handlePrev}>
          {isFirstStep
            ? t("Wizard_Nav_Cancel", "Cancel")
            : t("Wizard_Nav_Previous", "Previous")}
        </Button>
        {!isReviewStep && (
          <Button
            appearance="primary"
            onClick={handleNext}
            disabled={isFirstStep && !hasEnabledConnector}
          >
            {t("Wizard_Nav_Next", "Next")}
          </Button>
        )}
      </div>
    </div>
  );
};

const DashboardViewWrapper: React.FC = () => {
  const { item, runs, watermarks, isLoading, setSelectedRunId, setSelectedEntityName } = useConnectorEditorCtx();
  const { setCurrentView } = useViewNavigation();
  return (
    <ConnectorDashboard
      item={item}
      runs={runs}
      watermarks={watermarks}
      isLoading={isLoading}
      onRunClick={(runId) => {
        setSelectedRunId(runId);
        setCurrentView(VIEWS.RUN_DETAIL);
      }}
      onEntityClick={(entityName) => {
        setSelectedEntityName(entityName);
        setCurrentView(VIEWS.ENTITY_DETAIL);
      }}
    />
  );
};

const RunDetailViewWrapper: React.FC = () => {
  const { runs, selectedRunId } = useConnectorEditorCtx();
  return <RunDetailView runs={runs} runId={selectedRunId} />;
};

const EntityDetailViewWrapper: React.FC = () => {
  const { item, watermarks, selectedEntityName } = useConnectorEditorCtx();
  const configuredEntities: { name: string; displayName: string }[] = [];
  for (const c of item?.definition?.connectors ?? []) {
    if (!c.enabled) continue;
    switch (c.connectorType) {
      case "crm":
        for (const e of c.entities) if (e.enabled) configuredEntities.push({ name: e.logicalName, displayName: e.displayName });
        break;
      case "businesscentral":
        for (const e of c.entities) if (e.enabled) configuredEntities.push({ name: e.apiEndpoint, displayName: e.displayName });
        break;
      case "sql":
        for (const e of c.entities) if (e.enabled) configuredEntities.push({ name: e.tableName, displayName: e.displayName });
        break;
    }
  }
  return <EntityDetailView configuredEntities={configuredEntities} watermarks={watermarks} entityName={selectedEntityName} />;
};

// ── Static view definitions ────────────────────────────────────────────────────
// Defined at module level so component types are stable and React never
// unmounts/remounts them during normal state updates.

const STATIC_VIEWS: RegisteredView[] = [
  { name: VIEWS.EMPTY, component: <EmptyViewWrapper /> },
  {
    name: VIEWS.WIZARD,
    component: (
      <ConnectorErrorBoundary label="wizard">
        <WizardViewWrapper />
      </ConnectorErrorBoundary>
    ),
  },
  {
    name: VIEWS.DASHBOARD,
    component: (
      <ConnectorErrorBoundary label="dashboard">
        <DashboardViewWrapper />
      </ConnectorErrorBoundary>
    ),
  },
  {
    name: VIEWS.RUN_DETAIL,
    component: <RunDetailViewWrapper />,
    isDetailView: true,
  },
  {
    name: VIEWS.ENTITY_DETAIL,
    component: <EntityDetailViewWrapper />,
    isDetailView: true,
  },
];

// ── Main component ─────────────────────────────────────────────────────────────

export function ConnectorItemEditor({ workloadClient }: PageProps) {
  const pageContext = useParams<ContextProps>();
  const { pathname } = useLocation();
  const { t } = useTranslation();

  const [isLoading, setIsLoading] = useState(true);
  const [item, setItem] = useState<ItemWithDefinition<MultiConnectorItemDefinition>>();
  // useRef avoids a re-render cycle when the view setter is first received from ItemEditor
  const viewSetterRef = useRef<((view: string) => void) | null>(null);
  const [wizardState, setWizardState] = useState<WizardState>(buildWorkloadInitialState());
  const [isRunning, setIsRunning] = useState(false);
  const [isSchedulePaused, setIsSchedulePaused] = useState(false);
  const [runs] = useState<ConnectorRun[]>([]);
  const [watermarks] = useState<EntityWatermark[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedEntityName, setSelectedEntityName] = useState<string | null>(null);

  const updateWizard = useCallback(
    (patch: Partial<WizardState>) => setWizardState((prev) => ({ ...prev, ...patch })),
    [],
  );

  async function loadItem(): Promise<void> {
    if (pageContext.itemObjectId && item && item.id === pageContext.itemObjectId) return;
    setIsLoading(true);
    try {
      const loaded = await getWorkloadItem<AnyConnectorItemDefinition>(
        workloadClient,
        pageContext.itemObjectId ?? "",
      );
      const normalised: ItemWithDefinition<MultiConnectorItemDefinition> = {
        ...loaded,
        definition: loaded.definition ? normalizeToV2(loaded.definition) : undefined,
      };
      setItem(normalised);
    } catch {
      setItem(undefined);
    }
    setIsLoading(false);
  }

  useEffect(() => { loadItem(); }, [pageContext, pathname]);

  useEffect(() => {
    if (!isLoading && item && viewSetterRef.current) {
      const state = item.definition?.state;
      viewSetterRef.current(state === "configured" || state === "paused" ? VIEWS.DASHBOARD : VIEWS.EMPTY);
    }
  }, [isLoading, item]);

  async function handleRunNow(): Promise<void> {
    if (!item) {
      console.warn("[RunNow] item not loaded");
      return;
    }
    setIsRunning(true);
    try {
      const jobType = `${process.env.WORKLOAD_NAME}.Connector.ConnectorIngestionJob`;
      console.log("[RunNow] dispatching job", jobType, "item:", item.id);
      const instance = await workloadClient.itemSchedule.runItemJob({
        itemObjectId: item.id,
        itemJobType: jobType,
        payload: {},
      });
      console.log("[RunNow] dispatched:", instance);
      try {
        await callNotificationOpen(
          workloadClient,
          "Run started",
          "Ingestion job dispatched successfully.",
          NotificationType.Success,
          NotificationToastDuration.Medium,
        );
      } catch (notifErr) {
        console.warn("[RunNow] notification failed:", notifErr);
      }
    } catch (err: any) {
      console.error("[RunNow] failed:", err);
      try {
        await callNotificationOpen(
          workloadClient,
          "Run failed",
          err?.message ?? "Failed to dispatch ingestion job. Check browser console for details.",
          NotificationType.Error,
          NotificationToastDuration.Long,
        );
      } catch (notifErr) {
        console.warn("[RunNow] error notification failed:", notifErr);
      }
    } finally {
      setIsRunning(false);
    }
  }

  async function handlePauseToggle(): Promise<void> {
    setIsSchedulePaused((prev) => !prev);
  }

  /**
   * Builds and saves a MultiConnectorItemDefinition from the current wizard state.
   */
  async function handleActivate(): Promise<void> {
    if (!item) return;
    updateWizard({ isActivating: true });
    try {
      const refreshedConnectors = recomputeConnectorStatuses(wizardState.connectors);

      const definition: MultiConnectorItemDefinition = {
        schemaVersion: "2.0.0",
        state: "configured",
        connectors: refreshedConnectors,
        storage: {
          bronzeLakeHouseName:
            wizardState.storage.bronzeLakeHouseName ?? "Timevision-Bronze",
          schemaEvolutionPolicy: wizardState.storage.schemaEvolutionPolicy ?? "merge",
          useExistingLakehouse: wizardState.storage.useExistingLakehouse ?? false,
        },
        scheduling: {
          scheduleType: wizardState.schedule.scheduleType ?? "cron",
          cronExpression: wizardState.schedule.cronExpression,
          intervalMinutes: wizardState.schedule.intervalMinutes,
          timezone: wizardState.schedule.timezone ?? "UTC",
          enabled: wizardState.schedule.enabled ?? true,
        },
        metadata: {
          activatedAt: new Date().toISOString(),
        },
      };

      await saveItemDefinition(workloadClient, item.id, definition);
      setItem((prev) => (prev ? { ...prev, definition } : prev));
    } catch (err) {
      console.error("Activation failed", err);
      throw err;
    } finally {
      updateWizard({ isActivating: false });
    }
  }

  // ── Context value ─────────────────────────────────────────────

  const ctxValue: ConnectorEditorCtxValue = {
    workloadClient,
    item,
    setItem,
    wizardState,
    updateWizard,
    setWizardState,
    isLoading,
    runs,
    watermarks,
    selectedRunId,
    setSelectedRunId,
    selectedEntityName,
    setSelectedEntityName,
    handleActivate,
  };

  // ── Notifications ─────────────────────────────────────────────

  const notifications: RegisteredNotification[] = [];

  return (
    <ConnectorEditorCtx.Provider value={ctxValue}>
      <ItemEditor
        isLoading={isLoading}
        loadingMessage={t("ConnectorItemEditor_Loading", "Loading connector...")}
        ribbon={(context) => (
          <ConnectorItemRibbon
            workloadClient={workloadClient}
            viewContext={context}
            connectorState={item?.definition?.state ?? "empty"}
            isRunning={isRunning}
            isSchedulePaused={isSchedulePaused}
            onRunNow={handleRunNow}
            onPauseToggle={handlePauseToggle}
            onReconfigure={() => {
              setWizardState(
                item?.definition
                  ? buildWizardStateFromDefinition(item.definition)
                  : buildWorkloadInitialState(),
              );
              viewSetterRef.current?.(VIEWS.WIZARD);
            }}
            onOpenSettings={async () => {
              if (item) {
                const res = await getWorkloadItem(workloadClient, item.id);
                await callOpenSettings(workloadClient, (res as any).item, "About");
              }
            }}
          />
        )}
        messageBar={notifications}
        views={STATIC_VIEWS}
        viewSetter={(fn) => { viewSetterRef.current = fn; }}
      />
    </ConnectorEditorCtx.Provider>
  );
}