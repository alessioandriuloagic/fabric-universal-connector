import React from "react";
import { useTranslation } from "react-i18next";
import { Text, Badge } from "@fluentui/react-components";
import { EntityWatermark } from "../ConnectorItemDefinition";
import "../ConnectorItem.scss";

interface EntityStatusListProps {
  configuredEntities: { name: string; displayName: string }[];
  watermarks: EntityWatermark[];
  onEntityClick: (entityName: string) => void;
}

export function EntityStatusList({ configuredEntities, watermarks, onEntityClick }: EntityStatusListProps) {
  const { t } = useTranslation();

  if (configuredEntities.length === 0) {
    return (
      <Text size={200} style={{ padding: 8 }}>
        {t("EntityList_Empty", "No entities configured.")}
      </Text>
    );
  }

  return (
    <div className="entity-status-list">
      {configuredEntities.map((entity) => {
        const watermark = watermarks.find((w) => w.entityName === entity.name);
        const badgeColor = watermark
          ? watermark.isInitialLoadComplete ? "success" : "informative"
          : "subtle";
        return (
          <div
            key={entity.name}
            className="entity-status-item"
            onClick={() => onEntityClick(entity.name)}
          >
            <Badge color={badgeColor} appearance="filled" size="small" />
            <Text size={300}>{entity.displayName || entity.name}</Text>
          </div>
        );
      })}
    </div>
  );
}
