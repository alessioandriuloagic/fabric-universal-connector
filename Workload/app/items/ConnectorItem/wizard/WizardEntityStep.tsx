import React from "react";
import { useTranslation } from "react-i18next";
import { Checkbox, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

// Re-export from crmCatalog so existing import sites keep working.
export { CRM_CATALOG, expandCrmEntities } from "./crmCatalog";
import { CRM_CATALOG } from "./crmCatalog";

/**
 * @deprecated
 * WizardEntityStep is superseded by ConnectorConfigPanel which renders
 * entity selection inline per connector.  This component is retained only
 * for reference; it is no longer rendered in the wizard flow.
 */
export function WizardEntityStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();
  // connectors array replaces the old selectedEntities + moduleType fields
  const crmEntry = wizardState.connectors.find((c) => c.connectorType === "crm");
  const selectedEntities = crmEntry?.entities.map((e) => (e as any).logicalName ?? "") ?? [];

  const toggle = (key: string) => {
    if (!crmEntry) return;
    const isSelected = selectedEntities.includes(key);
    const next = wizardState.connectors.map((c) => {
      if (c.connectorType !== "crm") return c;
      return {
        ...c,
        entities: isSelected
          ? c.entities.filter((e) => (e as any).logicalName !== key)
          : [...c.entities],
      };
    });
    onUpdate({ connectors: next as typeof wizardState.connectors });
  };

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Entities_Title", "Select entities to ingest")}
      </Text>

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

      {validationErrors.entities && (
        <Text style={{ color: "var(--colorPaletteRedForeground1)" }}>
          {validationErrors.entities}
        </Text>
      )}
    </div>
  );
}
