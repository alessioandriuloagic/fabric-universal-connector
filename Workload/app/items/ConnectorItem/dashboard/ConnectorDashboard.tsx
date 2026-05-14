import React from "react";
import { useTranslation } from "react-i18next";
import { Text, Spinner } from "@fluentui/react-components";
import { ItemEditorDefaultView } from "../../../components/ItemEditor";
import { ConnectorRun, EntityWatermark } from "../ConnectorItemDefinition";
import { RunHistoryTable } from "./RunHistoryTable";
import { EntityStatusList } from "./EntityStatusList";
import "../ConnectorItem.scss";

interface ConnectorDashboardProps {
  runs: ConnectorRun[];
  watermarks: EntityWatermark[];
  isLoading: boolean;
  onRunClick: (runId: string) => void;
  onEntityClick: (entityName: string) => void;
}

export function ConnectorDashboard({
  runs,
  watermarks,
  isLoading,
  onRunClick,
  onEntityClick,
}: ConnectorDashboardProps) {
  const { t } = useTranslation();
  const lastRun = runs[0] ?? null;

  return (
    <ItemEditorDefaultView
      left={{
        title: t("Dashboard_Entities_Title", "Entities"),
        width: 260,
        collapsible: true,
        content: (
          <EntityStatusList
            watermarks={watermarks}
            onEntityClick={onEntityClick}
          />
        ),
      }}
      center={{
        content: isLoading ? (
          <Spinner label={t("Dashboard_Loading", "Loading run history...")} />
        ) : (
          <div className="connector-dashboard">
            <div className="connector-dashboard__summary-cards">
              <div className="connector-dashboard__summary-card">
                <Text size={200}>{t("Dashboard_LastRun", "Last Run")}</Text>
                <Text size={500} weight="semibold" block>
                  {lastRun?.status ?? t("Dashboard_NoRuns", "Never")}
                </Text>
              </div>
              <div className="connector-dashboard__summary-card">
                <Text size={200}>{t("Dashboard_RecordsIngested", "Records (last run)")}</Text>
                <Text size={500} weight="semibold" block>
                  {lastRun?.recordsIngested?.toLocaleString() ?? "—"}
                </Text>
              </div>
            </div>
            <RunHistoryTable runs={runs} onRunClick={onRunClick} />
          </div>
        ),
      }}
    />
  );
}
