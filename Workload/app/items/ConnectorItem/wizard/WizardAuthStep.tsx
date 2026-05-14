import React from "react";
import { useTranslation } from "react-i18next";
import { Radio, RadioGroup, Field, Input, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardAuthStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();
  const { auth } = wizardState;

  const updateAuth = (patch: Partial<typeof auth>) =>
    onUpdate({ auth: { ...auth, ...patch } });

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Auth_Title", "Configure authentication")}
      </Text>

      <RadioGroup
        value={auth.mode ?? ""}
        onChange={(_, d) => updateAuth({ mode: d.value as any })}
      >
        <Radio value="fabric_connection"
               label={t("Wizard_Auth_FabricConnection", "Fabric Connection (Recommended)")} />
        <Radio value="keyvault_reference"
               label={t("Wizard_Auth_KeyVault", "Azure Key Vault Reference")} />
        <Radio value="service_principal"
               label={t("Wizard_Auth_ServicePrincipal", "Service Principal")} />
      </RadioGroup>

      {auth.mode === "fabric_connection" && (
        <Field label={t("Wizard_Auth_ConnectionId", "Fabric Connection ID")}
               validationMessage={validationErrors.fabricConnectionId} required>
          <Input value={auth.fabricConnectionId ?? ""}
                 placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                 onChange={(_, d) => updateAuth({ fabricConnectionId: d.value })} />
        </Field>
      )}

      {auth.mode === "keyvault_reference" && (
        <>
          <Field label={t("Wizard_Auth_KV_Uri", "Key Vault URI")}
                 validationMessage={validationErrors.keyVaultUri} required>
            <Input value={auth.keyVaultUri ?? ""}
                   placeholder="https://myvault.vault.azure.net/"
                   onChange={(_, d) => updateAuth({ keyVaultUri: d.value })} />
          </Field>
          <Field label={t("Wizard_Auth_KV_SecretName", "Client Secret Name")}
                 validationMessage={validationErrors.clientSecretName} required>
            <Input value={auth.clientSecretName ?? ""}
                   onChange={(_, d) => updateAuth({ clientSecretName: d.value })} />
          </Field>
        </>
      )}

      {auth.mode === "service_principal" && (
        <>
          <Field label={t("Wizard_Auth_SP_TenantId", "Tenant ID")}
                 validationMessage={validationErrors.tenantId} required>
            <Input value={auth.tenantId ?? ""}
                   onChange={(_, d) => updateAuth({ tenantId: d.value })} />
          </Field>
          <Field label={t("Wizard_Auth_SP_ClientId", "Client ID")}
                 validationMessage={validationErrors.clientId} required>
            <Input value={auth.clientId ?? ""}
                   onChange={(_, d) => updateAuth({ clientId: d.value })} />
          </Field>
          <Text size={300}>
            {t("Wizard_Auth_SP_SecretHint", "Client secret must be stored in a Fabric Connection or Key Vault — not entered here.")}
          </Text>
        </>
      )}
    </div>
  );
}
