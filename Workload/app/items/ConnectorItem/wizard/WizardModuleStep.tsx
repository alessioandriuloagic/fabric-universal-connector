/**
 * @deprecated
 * WizardModuleStep is superseded by WizardConnectorStep which renders
 * multi-select toggle cards.  This component is retained only for reference;
 * it is no longer rendered in the wizard flow.
 */
import React from "react";
import { useTranslation } from "react-i18next";
import { Radio, RadioGroup, Text } from "@fluentui/react-components";
import { ModuleType } from "../ConnectorItemDefinition";
import { WizardStepProps } from "./wizardState";

export function WizardModuleStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();

  // Derive a single "selected" module from whichever connector is enabled.
  // In the v2 model there may be multiple enabled connectors; this legacy
  // component only reflects the first one.
  const selectedModule =
    (wizardState.connectors.find((c) => c.enabled)?.connectorType as ModuleType) ?? null;

  const handleChange = (value: ModuleType) => {
    // Toggle: disable all others, enable the chosen one
    const updated = wizardState.connectors.map((c) => ({
      ...c,
      enabled: c.connectorType === value,
    }));
    onUpdate({ connectors: updated as typeof wizardState.connectors });
  };

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
        value={selectedModule ?? ""}
        onChange={(_, data) => handleChange(data.value as ModuleType)}
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
