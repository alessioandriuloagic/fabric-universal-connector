/**
 * WizardConfigStep.tsx  (Step 2 of 5)
 *
 * Per-connector configuration step.
 * Renders one `ConnectorConfigPanel` for each enabled connector, stacked
 * vertically.  Panels are individually collapsible (Accordion) so the user
 * can focus on one connector at a time while keeping the others visible.
 *
 * Extensibility: panels are rendered from `connectors.filter(enabled)` —
 * adding a new connector type requires no change here.
 */
import React from "react";
import { useTranslation } from "react-i18next";
import { Text } from "@fluentui/react-components";
import { ConnectorEntry } from "../ConnectorItemDefinition";
import { CONNECTOR_REGISTRY } from "./connectorRegistry";
import { ConnectorConfigPanel } from "./ConnectorConfigPanel";
import { WizardStepProps } from "./wizardState";

export function WizardConfigStep({
  wizardState,
  onUpdate,
  validationErrors,
}: WizardStepProps) {
  const { t } = useTranslation();
  const { connectors } = wizardState;

  const enabledConnectors = connectors.filter((c) => c.enabled);

  const handleConnectorChange = (updated: ConnectorEntry) => {
    const next = connectors.map((c) =>
      c.connectorType === updated.connectorType ? updated : c,
    );
    onUpdate({ connectors: next as typeof connectors });
  };

  return (
    <div className="connector-wizard">
      <div className="connector-wizard__header">
        <Text size={600} weight="semibold">
          {t("Wizard_Config_Title", "Configure connectors")}
        </Text>
        <Text block>
          {t(
            "Wizard_Config_Description",
            "Fill in the connection details for each enabled connector. All required fields must be completed before activation.",
          )}
        </Text>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 16, marginTop: 16 }}>
        {enabledConnectors.map((entry) => {
          const def = CONNECTOR_REGISTRY.find((d) => d.type === entry.connectorType);
          if (!def) return null;
          return (
            <ConnectorConfigPanel
              key={entry.connectorType}
              entry={entry}
              definition={def}
              validationErrors={validationErrors}
              onChange={handleConnectorChange}
            />
          );
        })}
      </div>
    </div>
  );
}
