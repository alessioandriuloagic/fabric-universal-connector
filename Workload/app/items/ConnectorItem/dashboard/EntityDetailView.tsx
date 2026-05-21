import React from "react";
import { useTranslation } from "react-i18next";
import { Badge, Text } from "@fluentui/react-components";
import { EntityWatermark } from "../ConnectorItemDefinition";

interface EntityDetailViewProps {
  configuredEntities: { name: string; displayName: string }[];
  watermarks: EntityWatermark[];
  entityName: string | null;
}

export function EntityDetailView({ configuredEntities, watermarks, entityName }: EntityDetailViewProps) {
  const { t } = useTranslation();
  const watermark = watermarks.find((w) => w.entityName === entityName);
  const configured = configuredEntities.find((e) => e.name === entityName);

  if (!configured && !watermark) {
    return <Text>{t("EntityDetail_NotFound", "Entity not found.")}</Text>;
  }

  const displayName = configured?.displayName || entityName || "";

  return (
    <div style={{ padding: 16 }}>
      <Text size={600} weight="semibold" block>
        {displayName}
      </Text>
      {entityName !== displayName && (
        <Text size={200} style={{ color: "var(--colorNeutralForeground3)" }} block>
          {entityName}
        </Text>
      )}

      {watermark ? (
        <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Badge
              color={watermark.isInitialLoadComplete ? "success" : "informative"}
              appearance="filled"
              size="small"
            />
            <Text>
              {watermark.isInitialLoadComplete
                ? t("EntityDetail_Status_Synced", "Fully synced")
                : t("EntityDetail_Status_InProgress", "Initial load in progress")}
            </Text>
          </div>
          <Text block>{t("EntityDetail_LastSuccess", "Last Success")}: {new Date(watermark.lastSuccessUtc).toLocaleString()}</Text>
          <Text block>{t("EntityDetail_Records", "Records (last run)")}: {watermark.recordsAtLastRun.toLocaleString()}</Text>
          <Text block>{t("EntityDetail_WatermarkType", "Watermark Type")}: {watermark.watermarkType}</Text>
          <Text block>{t("EntityDetail_InitialLoad", "Initial Load Complete")}: {watermark.isInitialLoadComplete ? "Yes" : "No"}</Text>
        </div>
      ) : (
        <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <Badge color="subtle" appearance="filled" size="small" />
          <Text>{t("EntityDetail_Status_Pending", "Never synced — waiting for first run")}</Text>
        </div>
      )}
    </div>
  );
}
