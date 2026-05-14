import React from "react";
import { useTranslation } from "react-i18next";
import { Checkbox, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

const CRM_CATALOG = [
  { key: "contact",                    label: "Contact" },
  { key: "lead",                       label: "Lead" },
  { key: "msdynmkt_marketingform",     label: "Marketing Form" },
  { key: "msdynmkt_marketingemail",    label: "Marketing Email" },
  { key: "msdynmkt_customerjourney",   label: "Customer Journey" },
];

export function WizardEntityStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();
  const { moduleType, selectedEntities } = wizardState;

  const toggle = (key: string) => {
    const next = selectedEntities.includes(key)
      ? selectedEntities.filter((e) => e !== key)
      : [...selectedEntities, key];
    onUpdate({ selectedEntities: next });
  };

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Entities_Title", "Select entities to ingest")}
      </Text>

      {moduleType === "crm" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {CRM_CATALOG.map(({ key, label }) => (
            <Checkbox
              key={key}
              label={label}
              checked={selectedEntities.includes(key)}
              onChange={() => toggle(key)}
            />
          ))}
        </div>
      )}

      {(moduleType === "businesscentral" || moduleType === "sql") && (
        <Text>
          {t("Wizard_Entities_ManualNote",
            "Entity configuration for this module is set during the review step.")}
        </Text>
      )}

      {validationErrors.entities && (
        <Text style={{ color: "var(--colorPaletteRedForeground1)" }}>
          {validationErrors.entities}
        </Text>
      )}
    </div>
  );
}
