/**
 * @deprecated
 * WizardSourceStep is superseded by the inline source panels inside
 * ConnectorConfigPanel.  This component is retained only for reference;
 * it is no longer rendered in the wizard flow.
 */
import React from "react";
import { useTranslation } from "react-i18next";
import { Field, Input, Text } from "@fluentui/react-components";
import { ConnectorEntry } from "../ConnectorItemDefinition";
import { WizardStepProps } from "./wizardState";

export function WizardSourceStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();

  // Derive the first enabled connector entry
  const enabledEntry: ConnectorEntry | undefined = wizardState.connectors.find((c) => c.enabled);
  const moduleType = enabledEntry?.connectorType;
  const source = (enabledEntry?.source ?? {}) as Record<string, string>;

  const updateSource = (patch: Record<string, unknown>) => {
    if (!enabledEntry) return;
    const updated = wizardState.connectors.map((c) =>
      c.connectorType === enabledEntry.connectorType
        ? { ...c, source: { ...c.source, ...patch } }
        : c,
    );
    onUpdate({ connectors: updated as typeof wizardState.connectors });
  };

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Source_Title", "Configure source")}
      </Text>

      {moduleType === "crm" && (
        <>
          <Field
            label={t("Wizard_Source_CRM_Url", "CRM Organisation URL")}
            validationMessage={validationErrors["crm.environmentUrl"]}
            required
          >
            <Input
              value={source.environmentUrl ?? ""}
              placeholder="https://yourorg.crm4.dynamics.com"
              onChange={(_, d) => updateSource({ environmentUrl: d.value })}
            />
          </Field>
          <Field
            label={t("Wizard_Source_TenantId", "Azure AD Tenant ID")}
            validationMessage={validationErrors["crm.tenantId"]}
            required
          >
            <Input
              value={source.tenantId ?? ""}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              onChange={(_, d) => updateSource({ tenantId: d.value })}
            />
          </Field>
        </>
      )}

      {moduleType === "businesscentral" && (
        <>
          <Field
            label={t("Wizard_Source_TenantId", "Tenant ID")}
            validationMessage={validationErrors["bc.tenantId"]}
            required
          >
            <Input
              value={source.tenantId ?? ""}
              onChange={(_, d) => updateSource({ tenantId: d.value })}
            />
          </Field>
          <Field
            label={t("Wizard_Source_BC_Environment", "Environment")}
            validationMessage={validationErrors["bc.environment"]}
            required
          >
            <Input
              value={source.environment ?? ""}
              placeholder="Production"
              onChange={(_, d) => updateSource({ environment: d.value })}
            />
          </Field>
          <Field label={t("Wizard_Source_BC_CompanyId", "Company ID (optional)")}>
            <Input
              value={source.companyId ?? ""}
              onChange={(_, d) => updateSource({ companyId: d.value })}
            />
          </Field>
        </>
      )}

      {moduleType === "sql" && (
        <>
          <Field
            label={t("Wizard_Source_SQL_Server", "Server")}
            validationMessage={validationErrors["sql.server"]}
            required
          >
            <Input
              value={source.server ?? ""}
              placeholder="server.database.windows.net"
              onChange={(_, d) => updateSource({ server: d.value })}
            />
          </Field>
          <Field
            label={t("Wizard_Source_SQL_Database", "Database")}
            validationMessage={validationErrors["sql.database"]}
            required
          >
            <Input
              value={source.database ?? ""}
              onChange={(_, d) => updateSource({ database: d.value })}
            />
          </Field>
        </>
      )}
    </div>
  );
}