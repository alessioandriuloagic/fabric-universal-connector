import React from "react";
import { useTranslation } from "react-i18next";
import {
  Badge,
  Button,
  Divider,
  Spinner,
  Text,
} from "@fluentui/react-components";
import { ConnectorEntry } from "../ConnectorItemDefinition";
import { CONNECTOR_REGISTRY } from "./connectorRegistry";
import { WizardStepProps } from "./wizardState";

function row(label: string, value: string) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0" }}>
      <Text weight="semibold">{label}</Text>
      <Text>{value || "—"}</Text>
    </div>
  );
}

/** Summary block rendered for one enabled connector. */
function ConnectorSummary({ entry }: { entry: ConnectorEntry }) {
  const def = CONNECTOR_REGISTRY.find((d) => d.type === entry.connectorType);
  const src = entry.source as Record<string, unknown>;
  const auth = entry.auth as Record<string, unknown> | undefined;

  return (
    <div
      style={{
        borderLeft: `4px solid ${def?.accentColor ?? "var(--colorNeutralStroke1)"}`,
        paddingLeft: 12,
        marginBottom: 12,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
        <Text weight="semibold">{def?.label ?? entry.connectorType}</Text>
        {entry.status === "valid" ? (
          <Badge appearance="filled" color="success">Configured</Badge>
        ) : (
          <Badge appearance="filled" color="danger">Incomplete</Badge>
        )}
      </div>

      {Object.entries(src)
        .filter(([, v]) => v !== undefined && v !== "")
        .map(([k, v]) => row(k, String(v)))}

      {auth && row("Auth mode", auth.mode as string ?? "")}

      {entry.connectorType === "crm" && entry.entities.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 4 }}>
          {entry.entities.map((e) => (
            <Badge key={(e as any).logicalName} appearance="outline">
              {(e as any).displayName ?? (e as any).logicalName}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

export function WizardReviewStep({ wizardState, onActivate }: WizardStepProps) {
  const { t } = useTranslation();
  const { connectors, storage, schedule, isActivating } = wizardState;
  const enabledConnectors = connectors.filter((c) => c.enabled);

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Review_Title", "Review & Activate")}
      </Text>
      <Text block>
        {t(
          "Wizard_Review_Description",
          "Review your configuration. Click Activate to deploy the connectors and start the first ingestion run.",
        )}
      </Text>

      {/* ── Connectors ─────────────────────────────────────── */}
      <Divider style={{ margin: "12px 0 8px" }}>
        {t("Wizard_Review_Connectors", "Connectors")} ({enabledConnectors.length})
      </Divider>
      {enabledConnectors.map((entry) => (
        <ConnectorSummary key={entry.connectorType} entry={entry} />
      ))}

      {/* ── Storage ────────────────────────────────────────── */}
      <Divider style={{ margin: "12px 0 8px" }}>
        {t("Wizard_Review_Storage", "Storage")}
      </Divider>
      {row("Lakehouse", storage.bronzeLakeHouseName ?? "")}
      {row("Schema Policy", storage.schemaEvolutionPolicy ?? "merge")}

      {/* ── Schedule ───────────────────────────────────────── */}
      <Divider style={{ margin: "12px 0 8px" }}>
        {t("Wizard_Review_Schedule", "Schedule")}
      </Divider>
      {row("Type", schedule.scheduleType ?? "")}
      {schedule.scheduleType === "cron" && row("Expression", schedule.cronExpression ?? "")}
      {schedule.scheduleType === "interval" &&
        row("Every (min)", String(schedule.intervalMinutes ?? ""))}
      {row("Timezone", schedule.timezone ?? "UTC")}

      {/* ── Activate button ────────────────────────────────── */}
      {onActivate && (
        <div style={{ marginTop: 16 }}>
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

