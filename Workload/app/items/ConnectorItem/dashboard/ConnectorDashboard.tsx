import React from "react";
import { useTranslation } from "react-i18next";
import { Text, Spinner } from "@fluentui/react-components";
import { ItemEditorDefaultView } from "../../../components/ItemEditor";
import { ConnectorRun, EntityWatermark, MultiConnectorItemDefinition } from "../ConnectorItemDefinition";
import { ItemWithDefinition } from "../../../controller/ItemCRUDController";
import { RunHistoryTable } from "./RunHistoryTable";
import { EntityStatusList } from "./EntityStatusList";
import "../ConnectorItem.scss";

interface ConnectorDashboardProps {
  item: ItemWithDefinition<MultiConnectorItemDefinition> | undefined;
  runs: ConnectorRun[];
  watermarks: EntityWatermark[];
  isLoading: boolean;
  onRunClick: (runId: string) => void;
  onEntityClick: (entityName: string) => void;
}

/** Extracts a flat list of { name, displayName } for all enabled entities across all enabled connectors. */
function getConfiguredEntities(item: ItemWithDefinition<MultiConnectorItemDefinition> | undefined): { name: string; displayName: string }[] {
  const connectors = item?.definition?.connectors ?? [];
  const result: { name: string; displayName: string }[] = [];
  for (const c of connectors) {
    if (!c.enabled) continue;
    switch (c.connectorType) {
      case "crm":
        for (const e of c.entities) {
          if (e.enabled) result.push({ name: e.logicalName, displayName: e.displayName });
        }
        break;
      case "businesscentral":
        for (const e of c.entities) {
          if (e.enabled) result.push({ name: e.apiEndpoint, displayName: e.displayName });
        }
        break;
      case "sql":
        for (const e of c.entities) {
          if (e.enabled) result.push({ name: e.tableName, displayName: e.displayName });
        }
        break;
    }
  }
  return result;
}

export function ConnectorDashboard({
  item,
  runs,
  watermarks,
  isLoading,
  onRunClick,
  onEntityClick,
}: ConnectorDashboardProps) {
  const { t } = useTranslation();
  const lastRun = runs[0] ?? null;
  const configuredEntities = getConfiguredEntities(item);

  return (
    <ItemEditorDefaultView
      left={{
        title: t("Dashboard_Entities_Title", "Entities"),
        width: 260,
        collapsible: true,
        content: (
          <EntityStatusList
            configuredEntities={configuredEntities}
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
