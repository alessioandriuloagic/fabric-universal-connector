import React from "react";
import { useTranslation } from "react-i18next";
import { Text, Badge, Divider, Button, Spinner } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardReviewStep({ wizardState, onActivate }: WizardStepProps) {
  const { t } = useTranslation();
  const { moduleType, source, auth, selectedEntities, storage, schedule, isActivating } = wizardState;

  const row = (label: string, value: string) => (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0" }}>
      <Text weight="semibold">{label}</Text>
      <Text>{value || "—"}</Text>
    </div>
  );

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Review_Title", "Review & Activate")}
      </Text>
      <Text block>
        {t("Wizard_Review_Description",
          "Review your configuration. Click Activate to deploy the connector and start the first ingestion run.")}
      </Text>

      <Divider>{t("Wizard_Review_Module", "Module")}</Divider>
      {row("Type", moduleType ?? "")}

      <Divider>{t("Wizard_Review_Source", "Source")}</Divider>
      {Object.entries(source).map(([k, v]) => row(k, String(v ?? "")))}

      <Divider>{t("Wizard_Review_Auth", "Authentication")}</Divider>
      {row("Mode", auth.mode ?? "")}

      <Divider>{t("Wizard_Review_Entities", "Entities")}</Divider>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
        {selectedEntities.map((e) => <Badge key={e} appearance="filled">{e}</Badge>)}
      </div>

      <Divider>{t("Wizard_Review_Storage", "Storage")}</Divider>
      {row("Lakehouse", storage.bronzeLakeHouseName ?? "")}
      {row("Schema Policy", storage.schemaEvolutionPolicy ?? "merge")}

      <Divider>{t("Wizard_Review_Schedule", "Schedule")}</Divider>
      {row("Type", schedule.scheduleType ?? "")}
      {schedule.scheduleType === "cron" && row("Expression", schedule.cronExpression ?? "")}
      {schedule.scheduleType === "interval" && row("Every (min)", String(schedule.intervalMinutes ?? ""))}
      {row("Timezone", schedule.timezone ?? "UTC")}

      {/* Activate button — shown on the last step in place of the normal Next button */}
      {onActivate && (
        <div style={{ marginTop: 8 }}>
          <Button
            appearance="primary"
            disabled={isActivating}
            onClick={onActivate}
            icon={isActivating ? <Spinner size="tiny" /> : undefined}
          >
            {isActivating
              ? t("Wizard_Review_Activating", "Activating...")
              : t("Wizard_Review_Activate", "Activate")}
          </Button>
        </div>
      )}
    </div>
  );
}
