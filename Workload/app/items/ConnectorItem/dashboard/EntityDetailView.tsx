import React from "react";
import { useTranslation } from "react-i18next";
import { Text } from "@fluentui/react-components";
import { EntityWatermark } from "../ConnectorItemDefinition";

interface EntityDetailViewProps {
  watermarks: EntityWatermark[];
  entityName: string | null;
}

export function EntityDetailView({ watermarks, entityName }: EntityDetailViewProps) {
  const { t } = useTranslation();
  const watermark = watermarks.find((w) => w.entityName === entityName);

  if (!watermark) return <Text>{t("EntityDetail_NotFound", "Entity not found.")}</Text>;

  return (
    <div style={{ padding: 16 }}>
      <Text size={600} weight="semibold" block>
        {watermark.entityName}
      </Text>
      <Text block>{t("EntityDetail_LastSuccess", "Last Success")}: {new Date(watermark.lastSuccessUtc).toLocaleString()}</Text>
      <Text block>{t("EntityDetail_Records", "Records (last run)")}: {watermark.recordsAtLastRun.toLocaleString()}</Text>
      <Text block>{t("EntityDetail_WatermarkType", "Watermark Type")}: {watermark.watermarkType}</Text>
      <Text block>{t("EntityDetail_InitialLoad", "Initial Load Complete")}: {watermark.isInitialLoadComplete ? "Yes" : "No"}</Text>
    </div>
  );
}
