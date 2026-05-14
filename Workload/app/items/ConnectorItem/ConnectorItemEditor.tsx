import React, { useEffect, useState } from "react";
import { useParams, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageProps, ContextProps } from "../../App";
import {
  ItemWithDefinition,
  getWorkloadItem,
} from "../../controller/ItemCRUDController";
import { callOpenSettings } from "../../controller/SettingsController";
import {
  ItemEditor,
  useViewNavigation,
  RegisteredNotification,
} from "../../components/ItemEditor";
import { JobSchedulerClient } from "../../clients/JobSchedulerClient";
import {
  ConnectorItemDefinition,
  ConnectorRun,
  EntityWatermark,
} from "./ConnectorItemDefinition";
import { ConnectorItemEmptyView } from "./ConnectorItemEmptyView";
import { ConnectorItemRibbon } from "./ribbon/ConnectorItemRibbon";
import { WizardModuleStep } from "./wizard/WizardModuleStep";
import { WizardSourceStep } from "./wizard/WizardSourceStep";
import { WizardAuthStep } from "./wizard/WizardAuthStep";
import { WizardEntityStep } from "./wizard/WizardEntityStep";
import { WizardStorageStep } from "./wizard/WizardStorageStep";
import { WizardScheduleStep } from "./wizard/WizardScheduleStep";
import { WizardReviewStep } from "./wizard/WizardReviewStep";
import { ConnectorDashboard } from "./dashboard/ConnectorDashboard";
import { RunDetailView } from "./dashboard/RunDetailView";
import { EntityDetailView } from "./dashboard/EntityDetailView";
import {
  WizardState,
  INITIAL_WIZARD_STATE,
  WIZARD_STEPS,
} from "./wizard/wizardState";
import "./ConnectorItem.scss";

export const VIEWS = {
  EMPTY:            "empty",
  WIZARD_MODULE:    WIZARD_STEPS.MODULE,
  WIZARD_SOURCE:    WIZARD_STEPS.SOURCE,
  WIZARD_AUTH:      WIZARD_STEPS.AUTH,
  WIZARD_ENTITIES:  WIZARD_STEPS.ENTITIES,
  WIZARD_STORAGE:   WIZARD_STEPS.STORAGE,
  WIZARD_SCHEDULE:  WIZARD_STEPS.SCHEDULE,
  WIZARD_REVIEW:    WIZARD_STEPS.REVIEW,
  DASHBOARD:        "dashboard",
  RUN_DETAIL:       "run-detail",
  ENTITY_DETAIL:    "entity-detail",
} as const;

export function ConnectorItemEditor({ workloadClient }: PageProps) {
  const pageContext = useParams<ContextProps>();
  const { pathname } = useLocation();
  const { t } = useTranslation();

  const [isLoading, setIsLoading] = useState(true);
  const [item, setItem] = useState<ItemWithDefinition<ConnectorItemDefinition>>();
  const [viewSetter, setViewSetter] = useState<((view: string) => void) | null>(null);
  const [wizardState, setWizardState] = useState<WizardState>(INITIAL_WIZARD_STATE);
  const [activationSuccess] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isSchedulePaused, setIsSchedulePaused] = useState(false);
  const [runs] = useState<ConnectorRun[]>([]);
  const [watermarks] = useState<EntityWatermark[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedEntityName, setSelectedEntityName] = useState<string | null>(null);

  async function loadItem(): Promise<void> {
    if (pageContext.itemObjectId && item && item.id === pageContext.itemObjectId) return;
    setIsLoading(true);
    try {
      const loaded = await getWorkloadItem<ConnectorItemDefinition>(
        workloadClient,
        pageContext.itemObjectId
      );
      setItem(loaded);
    } catch {
      setItem(undefined);
    }
    setIsLoading(false);
  }

  useEffect(() => { loadItem(); }, [pageContext, pathname]);

  useEffect(() => {
    if (!isLoading && item && viewSetter) {
      const state = (item.definition as any)?.state;
      viewSetter(state === "configured" || state === "paused" ? VIEWS.DASHBOARD : VIEWS.EMPTY);
    }
  }, [isLoading, item, viewSetter]);

  const updateWizard = (patch: Partial<WizardState>) =>
    setWizardState((prev) => ({ ...prev, ...patch }));

  async function handleRunNow(): Promise<void> {
    if (!item) return;
    setIsRunning(true);
    try {
      const scheduler = new JobSchedulerClient(workloadClient);
      await scheduler.runOnDemandItemJob(item.workspaceId, item.id, "ConnectorIngestionJob");
    } finally {
      setIsRunning(false);
    }
  }

  async function handlePauseToggle(): Promise<void> {
    setIsSchedulePaused((prev) => !prev);
  }

  // ── Wrapper components for views that need useViewNavigation ──

  const EmptyViewWrapper = () => {
    const { setCurrentView } = useViewNavigation();
    return (
      <ConnectorItemEmptyView
        workloadClient={workloadClient}
        item={item}
        onConfigure={() => {
          setWizardState(INITIAL_WIZARD_STATE);
          setCurrentView(VIEWS.WIZARD_MODULE);
        }}
      />
    );
  };

  const DashboardWrapper = () => {
    const { setCurrentView } = useViewNavigation();
    return (
      <ConnectorDashboard
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

  // ── Static view array ─────────────────────────────────────────

  const views = [
    { name: VIEWS.EMPTY, component: <EmptyViewWrapper /> },

    {
      name: VIEWS.WIZARD_MODULE,
      component: <WizardModuleStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_SOURCE,
      component: <WizardSourceStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_AUTH,
      component: <WizardAuthStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_ENTITIES,
      component: <WizardEntityStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_STORAGE,
      component: <WizardStorageStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_SCHEDULE,
      component: <WizardScheduleStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_REVIEW,
      component: <WizardReviewStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },

    { name: VIEWS.DASHBOARD, component: <DashboardWrapper /> },

    {
      name: VIEWS.RUN_DETAIL,
      component: <RunDetailView runs={runs} runId={selectedRunId} />,
      isDetailView: true,
    },
    {
      name: VIEWS.ENTITY_DETAIL,
      component: <EntityDetailView watermarks={watermarks} entityName={selectedEntityName} />,
      isDetailView: true,
    },
  ];

  // ── Notifications ─────────────────────────────────────────────

  const notifications: RegisteredNotification[] = [
    {
      name: "activation-success",
      showInViews: [VIEWS.DASHBOARD],
      component: activationSuccess ? (
        <div>{t("ConnectorItem_ActivationSuccess", "Connector activated. First run starting...")}</div>
      ) : null,
    },
  ];

  return (
    <ItemEditor
      isLoading={isLoading}
      loadingMessage={t("ConnectorItemEditor_Loading", "Loading connector...")}
      ribbon={(context) => (
        <ConnectorItemRibbon
          workloadClient={workloadClient}
          viewContext={context}
          connectorState={(item?.definition as any)?.state ?? "empty"}
          isRunning={isRunning}
          isSchedulePaused={isSchedulePaused}
          onRunNow={handleRunNow}
          onPauseToggle={handlePauseToggle}
          onReconfigure={() => {
            setWizardState(INITIAL_WIZARD_STATE);
            viewSetter?.(VIEWS.WIZARD_MODULE);
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
      views={views}
      viewSetter={(fn) => { if (!viewSetter) setViewSetter(() => fn); }}
    />
  );
}
