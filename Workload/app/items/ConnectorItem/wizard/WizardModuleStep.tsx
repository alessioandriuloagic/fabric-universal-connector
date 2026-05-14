import React from "react";
import { useTranslation } from "react-i18next";
import { Radio, RadioGroup, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardModuleStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();

  return (
    <div className="connector-wizard">
      <div className="connector-wizard__header">
        <Text size={600} weight="semibold">
          {t("Wizard_Module_Title", "Select data source type")}
        </Text>
        <Text block>
          {t("Wizard_Module_Description", "Choose the source system you want to connect.")}
        </Text>
      </div>

      <RadioGroup
        value={wizardState.moduleType ?? ""}
        onChange={(_, data) => onUpdate({ moduleType: data.value as any, selectedEntities: [] })}
      >
        <Radio value="crm" label={t("Wizard_Module_CRM", "Microsoft Dataverse / Dynamics 365 CRM")} />
        <Radio value="businesscentral" label={t("Wizard_Module_BC", "Microsoft Dynamics 365 Business Central")} />
        <Radio value="sql" label={t("Wizard_Module_SQL", "SQL Server / Azure SQL")} />
      </RadioGroup>

      {validationErrors.moduleType && (
        <Text style={{ color: "var(--colorPaletteRedForeground1)" }}>
          {validationErrors.moduleType}
        </Text>
      )}
    </div>
  );
}
