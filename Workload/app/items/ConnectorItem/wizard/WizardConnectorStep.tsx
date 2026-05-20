/**
 * WizardConnectorStep.tsx  (Step 1 of 5)
 *
 * Multi-select connector selection screen.
 * Replaces the single-select radio-button WizardModuleStep.
 *
 * Each registered connector is shown as a toggle card with a Switch.
 * The accent color on the card border changes when the connector is enabled,
 * giving clear visual feedback about which connectors are active.
 *
 * Extensibility: connector cards are rendered from CONNECTOR_REGISTRY — adding
 * a new connector requires only a new registry entry, not a change here.
 */
import React from "react";
import { useTranslation } from "react-i18next";
import {
  Card,
  CardHeader,
  Switch,
  Text,
  Badge,
} from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";
import { CONNECTOR_REGISTRY } from "./connectorRegistry";

export function WizardConnectorStep({
  wizardState,
  onUpdate,
  validationErrors,
}: WizardStepProps) {
  const { t } = useTranslation();
  const { connectors } = wizardState;

  const toggleConnector = (type: string, enabled: boolean) => {
    const updated = connectors.map((c) =>
      c.connectorType === type ? { ...c, enabled } : c,
    );
    onUpdate({ connectors: updated as typeof connectors });
  };

  return (
    <div className="connector-wizard">
      <div className="connector-wizard__header">
        <Text size={600} weight="semibold">
          {t("Wizard_Connectors_Title", "Select data sources")}
        </Text>
        <Text block>
          {t(
            "Wizard_Connectors_Description",
            "Enable one or more connectors. Each enabled connector gets its own configuration section in the next step.",
          )}
        </Text>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 16 }}>
        {CONNECTOR_REGISTRY.map((def) => {
          const entry = connectors.find((c) => c.connectorType === def.type);
          const isEnabled = entry?.enabled ?? false;

          return (
            <Card
              key={def.type}
              style={{
                borderLeft: `4px solid ${isEnabled ? def.accentColor : "var(--colorNeutralStroke1)"}`,
                opacity: isEnabled ? 1 : 0.8,
                transition: "border-color 0.15s ease, opacity 0.15s ease",
              }}
            >
              <CardHeader
                header={
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      width: "100%",
                    }}
                  >
                    {/* Colored dot matching the connector accent */}
                    <div
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: "50%",
                        backgroundColor: def.accentColor,
                        flexShrink: 0,
                      }}
                    />

                    <div style={{ flex: 1 }}>
                      <Text weight="semibold">{def.label}</Text>
                      <Text
                        size={200}
                        style={{
                          display: "block",
                          color: "var(--colorNeutralForeground3)",
                        }}
                      >
                        {def.description}
                      </Text>
                    </div>

                    {isEnabled && (
                      <Badge
                        appearance="filled"
                        style={{ backgroundColor: def.accentColor, color: "#fff" }}
                      >
                        {t("Wizard_Connectors_Enabled", "Enabled")}
                      </Badge>
                    )}

                    <Switch
                      checked={isEnabled}
                      onChange={(_, d) => toggleConnector(def.type, d.checked)}
                      aria-label={t(
                        "Wizard_Connectors_Toggle",
                        "Enable {{label}}",
                        { label: def.label },
                      )}
                    />
                  </div>
                }
              />
            </Card>
          );
        })}
      </div>

      {validationErrors.connectors && (
        <Text
          style={{
            color: "var(--colorPaletteRedForeground1)",
            marginTop: 8,
            display: "block",
          }}
        >
          {validationErrors.connectors}
        </Text>
      )}
    </div>
  );
}
