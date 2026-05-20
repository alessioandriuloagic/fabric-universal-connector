import React from "react";
import { useTranslation } from "react-i18next";
import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { ItemWithDefinition } from "../../controller/ItemCRUDController";
import { ItemEditorEmptyView, EmptyStateTask } from "../../components/ItemEditor";
import { AnyConnectorItemDefinition } from "./ConnectorItemDefinition";
import "./ConnectorItem.scss";

interface ConnectorItemEmptyViewProps {
  workloadClient: WorkloadClientAPI;
  item?: ItemWithDefinition<AnyConnectorItemDefinition>;
  onConfigure: () => void;
}

export function ConnectorItemEmptyView({
  item,
  onConfigure,
}: ConnectorItemEmptyViewProps) {
  const { t } = useTranslation();

  const tasks: EmptyStateTask[] = [
    {
      id: "configure",
      label: t("ConnectorItemEmptyView_ConfigureButton", "Configure Connector"),
      icon: undefined,
      description: t(
        "ConnectorItemEmptyView_ConfigureButton_Description",
        "Follow the setup wizard to connect your data sources."
      ),
      onClick: onConfigure,
    },
  ];

  return (
    <ItemEditorEmptyView
      title={t("ConnectorItemEmptyView_Title", "Connect your data source")}
      description={t(
        "ConnectorItemEmptyView_Description",
        "Configure your connector to start ingesting data from Dataverse, Business Central, or SQL Server into your Fabric Bronze Lakehouse."
      )}
      imageSrc="/assets/items/ConnectorItem/EditorEmpty.svg"
      imageAlt="Connector empty state"
      tasks={tasks}
    />
  );
}
