import React from "react";
import { useTranslation } from "react-i18next";
import { Text, Badge } from "@fluentui/react-components";
import { EntityWatermark } from "../ConnectorItemDefinition";
import "../ConnectorItem.scss";

interface EntityStatusListProps {
  watermarks: EntityWatermark[];
  onEntityClick: (entityName: string) => void;
}

export function EntityStatusList({ watermarks, onEntityClick }: EntityStatusListProps) {
  const { t } = useTranslation();

  if (watermarks.length === 0) {
    return (
      <Text size={200} style={{ padding: 8 }}>
        {t("EntityList_Empty", "No entities configured.")}
      </Text>
    );
  }

  return (
    <div className="entity-status-list">
      {watermarks.map((w) => (
        <div
          key={w.entityName}
          className="entity-status-item"
          onClick={() => onEntityClick(w.entityName)}
        >
          <Badge
            color={w.isInitialLoadComplete ? "success" : "informative"}
            appearance="filled"
            size="small"
          />
          <Text size={300}>{w.entityName}</Text>
        </div>
      ))}
    </div>
  );
}
