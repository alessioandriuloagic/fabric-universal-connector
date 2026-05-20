import React, { useEffect, useState } from "react";
import { useParams, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "@fluentui/react-components";
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
} from "../../components/ItemEditor";
import { JobSchedulerClient } from "../../clients/JobSchedulerClient";
import {
  ConnectorItemDefinition,
  ConnectorRun,
  CrmConnectorItemDefinition,
  EntityWatermark,
} from "./ConnectorItemDefinition";
import { ConnectorItemEmptyView } from "./ConnectorItemEmptyView";
import { ConnectorItemRibbon } from "./ribbon/ConnectorItemRibbon";
import { WizardModuleStep } from "./wizard/WizardModuleStep";
import { WizardSourceStep } from "./wizard/WizardSourceStep";
import { WizardAuthStep } from "./wizard/WizardAuthStep";
import { WizardEntityStep, expandCrmEntities } from "./wizard/WizardEntityStep";
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
  WIZARD_STEP_ORDER,
  getNextStep,
  getPrevStep,
} from "./wizard/wizardState";
import "./ConnectorItem.scss";

export const VIEWS = {
  EMPTY:         "empty",
  WIZARD:        "wizard",
  DASHBOARD:     "dashboard",
  RUN_DETAIL:    "run-detail",
  ENTITY_DETAIL: "entity-detail",
} as const;

export function ConnectorItemEditor({ workloadClient }: PageProps) {
  const pageContext = useParams<ContextProps>();
  const { pathname } = useLocation();
  const { t } = useTranslation();

  const [isLoading, setIsLoading] = useState(true);
  const [item, setItem] = useState<ItemWithDefinition<ConnectorItemDefinition>>();
  const [viewSetter, setViewSetter] = useState<((view: string) => void) | null>(null);
  const [wizardState, setWizardState] = useState<WizardState>(INITIAL_WIZARD_STATE);
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
        pageContext.itemObjectId ?? ''
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

  async function handleActivate(): Promise<void> {
    if (!item) return;
    updateWizard({ isActivating: true });
    try {
      const { moduleType, source, auth, selectedEntities, storage, schedule } = wizardState;

      let definition: ConnectorItemDefinition;

      if (moduleType === "crm") {
        const crmDef: CrmConnectorItemDefinition = {
          schemaVersion: "1.0.0",
          state: "configured",
          moduleType: "crm",
          source: {
            environmentUrl: (source as any).environmentUrl ?? "",
            tenantId: (source as any).tenantId ?? "",
            enableChangeTracking: true,
            pageSize: 5000,
          },
          entities: expandCrmEntities(selectedEntities),
          authentication: auth.mode === "service_principal" ? {
            mode: "service_principal",
            tenantId: auth.tenantId ?? "",
            clientId: auth.clientId ?? "",
            secretRef: auth.fabricConnectionId
              ? { mode: "fabric_connection", fabricConnectionId: auth.fabricConnectionId }
              : { mode: "keyvault_reference", keyVaultUri: auth.keyVaultUri ?? "", clientSecretName: auth.clientSecretName ?? "" },
          } : auth.mode === "fabric_connection" ? {
            mode: "fabric_connection",
            fabricConnectionId: auth.fabricConnectionId ?? "",
          } : {
            mode: "keyvault_reference",
            keyVaultUri: auth.keyVaultUri ?? "",
            clientSecretName: auth.clientSecretName ?? "",
          },
          storage: {
            bronzeLakeHouseName: storage.bronzeLakeHouseName ?? "FabricUniversalConnector-Bronze",
            schemaEvolutionPolicy: storage.schemaEvolutionPolicy ?? "merge",
            useExistingLakehouse: storage.useExistingLakehouse ?? false,
          },
          scheduling: {
            scheduleType: schedule.scheduleType ?? "cron",
            cronExpression: schedule.cronExpression,
            intervalMinutes: schedule.intervalMinutes,
            timezone: schedule.timezone ?? "UTC",
            enabled: schedule.enabled ?? true,
          },
          metadata: {
            activatedAt: new Date().toISOString(),
          },
        };
        definition = crmDef;
      } else {
        return;
      }

      await saveItemDefinition(workloadClient, item.id, definition);
      setItem((prev) => prev ? { ...prev, definition } : prev);
    } catch (err) {
      console.error("Activation failed", err);
      throw err;
    } finally {
      updateWizard({ isActivating: false });
    }
  }

  // ── Inner view components ─────────────────────────────────────

  const EmptyViewWrapper = () => {
    const { setCurrentView } = useViewNavigation();
    return (
      <ConnectorItemEmptyView
        workloadClient={workloadClient}
        item={item}
        onConfigure={() => {
          setWizardState(INITIAL_WIZARD_STATE);
          setCurrentView(VIEWS.WIZARD);
        }}
      />
    );
  };

  const WizardView = () => {
    const { setCurrentView } = useViewNavigation();

    const commonProps = {
      wizardState,
      onUpdate: updateWizard,
      validationErrors: wizardState.validationErrors,
    };

    const isFirstStep = wizardState.step === WIZARD_STEPS.MODULE;
    const isReviewStep = wizardState.step === WIZARD_STEPS.REVIEW;

    const handleNext = () => {
      const next = getNextStep(wizardState.step);
      if (next) updateWizard({ step: next });
    };

    const handlePrev = () => {
      const prev = getPrevStep(wizardState.step);
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

    const stepIndex = WIZARD_STEP_ORDER.indexOf(wizardState.step);
    const totalSteps = WIZARD_STEP_ORDER.length;

    const renderStep = () => {
      switch (wizardState.step) {
        case WIZARD_STEPS.MODULE:   return <WizardModuleStep   {...commonProps} />;
        case WIZARD_STEPS.SOURCE:   return <WizardSourceStep   {...commonProps} />;
        case WIZARD_STEPS.AUTH:     return <WizardAuthStep     {...commonProps} />;
        case WIZARD_STEPS.ENTITIES: return <WizardEntityStep   {...commonProps} />;
        case WIZARD_STEPS.STORAGE:  return <WizardStorageStep  {...commonProps} />;
        case WIZARD_STEPS.SCHEDULE: return <WizardScheduleStep {...commonProps} />;
        case WIZARD_STEPS.REVIEW:   return (
          <WizardReviewStep {...commonProps} onActivate={handleActivateAndNavigate} />
        );
        default: return null;
      }
    };

    return (
      <div style={{ display: "flex", flexDirection: "column", minHeight: "100%" }}>
        {/* Step counter */}
        <div style={{ padding: "8px 24px", color: "var(--colorNeutralForeground3)", fontSize: 12 }}>
          {t("Wizard_StepCounter", "Step {{current}} of {{total}}", { current: stepIndex + 1, total: totalSteps })}
        </div>

        {/* Step content */}
        <div style={{ flex: 1 }}>
          {renderStep()}
        </div>

        {/* Navigation footer */}
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          padding: "16px 24px",
          borderTop: "1px solid var(--colorNeutralStroke1)",
          marginTop: 16,
        }}>
          <Button appearance="secondary" onClick={handlePrev}>
            {isFirstStep
              ? t("Wizard_Nav_Cancel", "Cancel")
              : t("Wizard_Nav_Previous", "Previous")}
          </Button>

          {!isReviewStep && (
            <Button
              appearance="primary"
              onClick={handleNext}
              disabled={isFirstStep && !wizardState.moduleType}
            >
              {t("Wizard_Nav_Next", "Next")}
            </Button>
          )}
        </div>
      </div>
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

  // ── View registration ─────────────────────────────────────────

  const views = [
    { name: VIEWS.EMPTY,    component: <EmptyViewWrapper /> },
    { name: VIEWS.WIZARD,   component: <WizardView /> },
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

  const notifications: RegisteredNotification[] = [];

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
            viewSetter?.(VIEWS.WIZARD);
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
