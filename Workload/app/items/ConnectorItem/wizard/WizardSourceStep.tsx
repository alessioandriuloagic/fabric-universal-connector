import React from "react";
import { useTranslation } from "react-i18next";
import { Field, Input, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardSourceStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();
  const { moduleType, source } = wizardState;

  const updateSource = (patch: Record<string, unknown>) =>
    onUpdate({ source: { ...source, ...patch } });

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Source_Title", "Configure source")}
      </Text>

      {moduleType === "crm" && (
        <>
          <Field label={t("Wizard_Source_CRM_Url", "Environment URL")}
                 validationMessage={validationErrors.environmentUrl} required>
            <Input
              value={(source as any).environmentUrl ?? ""}
              placeholder="https://org.crm4.dynamics.com"
              onChange={(_, d) => updateSource({ environmentUrl: d.value })}
            />
          </Field>
          <Field label={t("Wizard_Source_TenantId", "Tenant ID")}
                 validationMessage={validationErrors.tenantId} required>
            <Input
              value={(source as any).tenantId ?? ""}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              onChange={(_, d) => updateSource({ tenantId: d.value })}
            />
          </Field>
        </>
      )}

      {moduleType === "businesscentral" && (
        <>
          <Field label={t("Wizard_Source_TenantId", "Tenant ID")}
                 validationMessage={validationErrors.tenantId} required>
            <Input value={(source as any).tenantId ?? ""}
                   onChange={(_, d) => updateSource({ tenantId: d.value })} />
          </Field>
          <Field label={t("Wizard_Source_BC_Environment", "Environment")}
                 validationMessage={validationErrors.environment} required>
            <Input value={(source as any).environment ?? ""}
                   placeholder="Production"
                   onChange={(_, d) => updateSource({ environment: d.value })} />
          </Field>
          <Field label={t("Wizard_Source_BC_CompanyId", "Company ID (optional)")}>
            <Input value={(source as any).companyId ?? ""}
                   onChange={(_, d) => updateSource({ companyId: d.value })} />
          </Field>
        </>
      )}

      {moduleType === "sql" && (
        <>
          <Field label={t("Wizard_Source_SQL_Server", "Server")}
                 validationMessage={validationErrors.server} required>
            <Input value={(source as any).server ?? ""}
                   placeholder="server.database.windows.net"
                   onChange={(_, d) => updateSource({ server: d.value })} />
          </Field>
          <Field label={t("Wizard_Source_SQL_Database", "Database")}
                 validationMessage={validationErrors.database} required>
            <Input value={(source as any).database ?? ""}
                   onChange={(_, d) => updateSource({ database: d.value })} />
          </Field>
        </>
      )}
    </div>
  );
}
