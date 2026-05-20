/**
 * @deprecated
 * WizardAuthStep is superseded by the inline auth panel inside
 * ConnectorConfigPanel.  This component is retained only for reference;
 * it is no longer rendered in the wizard flow.
 */
import React from "react";
import { useTranslation } from "react-i18next";
import { Radio, RadioGroup, Field, Input, Text } from "@fluentui/react-components";
import { AuthConfiguration } from "../ConnectorItemDefinition";
import { WizardStepProps } from "./wizardState";

export function WizardAuthStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();

  // Derive auth from the first enabled connector entry
  const enabledEntry = wizardState.connectors.find((c) => c.enabled);
  const auth = (enabledEntry?.auth ?? { mode: null }) as AuthConfiguration & { mode: string | null };

  const updateAuth = (patch: Partial<AuthConfiguration>) => {
    if (!enabledEntry) return;
    const updated = wizardState.connectors.map((c) =>
      c.connectorType === enabledEntry.connectorType
        ? { ...c, auth: { ...c.auth, ...patch } as AuthConfiguration }
        : c,
    );
    onUpdate({ connectors: updated as typeof wizardState.connectors });
  };

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Auth_Title", "Configure authentication")}
      </Text>

      <RadioGroup
        value={auth.mode ?? ""}
        onChange={(_, d) => updateAuth({ mode: d.value as any })}
      >
        <Radio
          value="fabric_connection"
          label={t("Wizard_Auth_FabricConnection", "Fabric Connection (Recommended)")}
        />
        <Radio
          value="keyvault_reference"
          label={t("Wizard_Auth_KeyVault", "Azure Key Vault Reference")}
        />
        <Radio
          value="service_principal"
          label={t("Wizard_Auth_ServicePrincipal", "Service Principal")}
        />
      </RadioGroup>

      {auth.mode === "fabric_connection" && (
        <Field
          label={t("Wizard_Auth_ConnectionId", "Fabric Connection ID")}
          validationMessage={validationErrors.fabricConnectionId}
          required
        >
          <Input
            value={(auth as any).fabricConnectionId ?? ""}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            onChange={(_, d) => updateAuth({ mode: "fabric_connection", fabricConnectionId: d.value } as any)}
          />
        </Field>
      )}

      {auth.mode === "keyvault_reference" && (
        <>
          <Field
            label={t("Wizard_Auth_KV_Uri", "Key Vault URI")}
            validationMessage={validationErrors.keyVaultUri}
            required
          >
            <Input
              value={(auth as any).keyVaultUri ?? ""}
              placeholder="https://myvault.vault.azure.net/"
              onChange={(_, d) => updateAuth({ mode: "keyvault_reference", keyVaultUri: d.value } as any)}
            />
          </Field>
          <Field
            label={t("Wizard_Auth_KV_SecretName", "Client Secret Name")}
            validationMessage={validationErrors.clientSecretName}
            required
          >
            <Input
              value={(auth as any).clientSecretName ?? ""}
              onChange={(_, d) => updateAuth({ mode: "keyvault_reference", clientSecretName: d.value } as any)}
            />
          </Field>
        </>
      )}

      {auth.mode === "service_principal" && (
        <>
          <Field
            label={t("Wizard_Auth_SP_TenantId", "Tenant ID")}
            validationMessage={validationErrors.tenantId}
            required
          >
            <Input
              value={(auth as any).tenantId ?? ""}
              onChange={(_, d) => updateAuth({ mode: "service_principal", tenantId: d.value } as any)}
            />
          </Field>
          <Field
            label={t("Wizard_Auth_SP_ClientId", "Client ID")}
            validationMessage={validationErrors.clientId}
            required
          >
            <Input
              value={(auth as any).clientId ?? ""}
              onChange={(_, d) => updateAuth({ mode: "service_principal", clientId: d.value } as any)}
            />
          </Field>
          <Text size={300}>
            {t(
              "Wizard_Auth_SP_SecretHint",
              "Client secret must be stored in a Fabric Connection or Key Vault — not entered here.",
            )}
          </Text>
        </>
      )}
    </div>
  );
}
