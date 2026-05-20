/**
 * ConnectorConfigPanel.tsx
 *
 * Renders the full configuration UI for a single connector entry:
 * source connection fields, authentication method, and entity selection.
 *
 * Each section is rendered conditionally based on `entry.connectorType`,
 * keeping the logic co-located with the connector rather than spread across
 * separate wizard steps.  The panel is displayed inside an Accordion so that
 * multiple enabled connectors can be shown simultaneously in WizardConfigStep
 * without overwhelming the user.
 *
 * Per-connector status badge: the badge in the accordion header reflects the
 * current validation state (unconfigured / valid / error) so users can see at
 * a glance which connectors still need attention.
 */
import React from "react";
import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionHeader,
  AccordionItem,
  AccordionPanel,
  Badge,
  Checkbox,
  Field,
  Input,
  Radio,
  RadioGroup,
  Text,
} from "@fluentui/react-components";
import {
  AuthConfiguration,
  ConnectorEntry,
  CrmConnectorEntry,
  BusinessCentralConnectorEntry,
  SqlConnectorEntry,
} from "../ConnectorItemDefinition";
import { ConnectorDefinition } from "./connectorRegistry";
import { CRM_CATALOG, expandCrmEntities } from "./crmCatalog";
import { WORKLOAD_CONFIG } from "../workloadConfig";

// ── Props ────────────────────────────────────────────────────────

interface ConnectorConfigPanelProps {
  entry: ConnectorEntry;
  definition: ConnectorDefinition;
  /** Flat error map from the shared wizard validation state. */
  validationErrors: Record<string, string>;
  onChange: (updated: ConnectorEntry) => void;
}

// ── Per-connector source sub-panels ─────────────────────────────

function CrmSourcePanel({
  entry,
  onChange,
  errors,
}: {
  entry: CrmConnectorEntry;
  onChange: (e: CrmConnectorEntry) => void;
  errors: Record<string, string>;
}) {
  const { t } = useTranslation();
  const upd = (patch: Partial<CrmConnectorEntry["source"]>) =>
    onChange({ ...entry, source: { ...entry.source, ...patch } });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Field
        label={t("Wizard_Source_CRM_Url", "CRM Organisation URL")}
        hint={t(
          "Wizard_Source_CRM_Url_Hint",
          "The Dataverse environment URL for your Dynamics 365 / Customer Insights organisation.",
        )}
        validationMessage={errors["crm.environmentUrl"]}
        required
      >
        <Input
          value={entry.source.environmentUrl ?? ""}
          placeholder="https://yourorg.crm4.dynamics.com"
          onChange={(_, d) => upd({ environmentUrl: d.value })}
        />
      </Field>

      <Field
        label={t("Wizard_Source_TenantId", "Azure AD Tenant ID")}
        hint={t(
          "Wizard_Source_TenantId_Hint",
          "The Azure Active Directory tenant that owns the Dynamics 365 organisation.",
        )}
        validationMessage={errors["crm.tenantId"]}
        required
      >
        <Input
          value={entry.source.tenantId ?? ""}
          placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          onChange={(_, d) => upd({ tenantId: d.value })}
        />
      </Field>
    </div>
  );
}

function BcSourcePanel({
  entry,
  onChange,
  errors,
}: {
  entry: BusinessCentralConnectorEntry;
  onChange: (e: BusinessCentralConnectorEntry) => void;
  errors: Record<string, string>;
}) {
  const { t } = useTranslation();
  const upd = (patch: Partial<BusinessCentralConnectorEntry["source"]>) =>
    onChange({ ...entry, source: { ...entry.source, ...patch } });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Field
        label={t("Wizard_Source_TenantId", "Tenant ID")}
        validationMessage={errors["bc.tenantId"]}
        required
      >
        <Input
          value={entry.source.tenantId ?? ""}
          placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
          onChange={(_, d) => upd({ tenantId: d.value })}
        />
      </Field>

      <Field
        label={t("Wizard_Source_BC_Environment", "Environment")}
        validationMessage={errors["bc.environment"]}
        required
      >
        <Input
          value={entry.source.environment ?? ""}
          placeholder="Production"
          onChange={(_, d) => upd({ environment: d.value })}
        />
      </Field>

      <Field label={t("Wizard_Source_BC_CompanyId", "Company ID (optional)")}>
        <Input
          value={entry.source.companyId ?? ""}
          onChange={(_, d) => upd({ companyId: d.value })}
        />
      </Field>
    </div>
  );
}

function SqlSourcePanel({
  entry,
  onChange,
  errors,
}: {
  entry: SqlConnectorEntry;
  onChange: (e: SqlConnectorEntry) => void;
  errors: Record<string, string>;
}) {
  const { t } = useTranslation();
  const upd = (patch: Partial<SqlConnectorEntry["source"]>) =>
    onChange({ ...entry, source: { ...entry.source, ...patch } });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <Field
        label={t("Wizard_Source_SQL_Server", "Server")}
        validationMessage={errors["sql.server"]}
        required
      >
        <Input
          value={entry.source.server ?? ""}
          placeholder="server.database.windows.net"
          onChange={(_, d) => upd({ server: d.value })}
        />
      </Field>

      <Field
        label={t("Wizard_Source_SQL_Database", "Database")}
        validationMessage={errors["sql.database"]}
        required
      >
        <Input
          value={entry.source.database ?? ""}
          onChange={(_, d) => upd({ database: d.value })}
        />
      </Field>
    </div>
  );
}

// ── Auth sub-panel (shared across all connector types) ───────────

function AuthPanel({
  auth,
  prefix,
  errors,
  onChange,
}: {
  auth: AuthConfiguration | undefined;
  /** Key prefix used for error lookup, e.g. "crm" → errors["crm.auth"] */
  prefix: string;
  errors: Record<string, string>;
  onChange: (a: AuthConfiguration | undefined) => void;
}) {
  const { t } = useTranslation();
  const mode = auth?.mode ?? null;

  // Merge a mode change with any existing fields so the user doesn't lose
  // partially entered data when switching auth method.
  const setMode = (newMode: string) => {
    onChange({ mode: newMode } as AuthConfiguration);
  };

  const mergeAuth = (patch: Record<string, unknown>) => {
    onChange({ ...auth, ...patch } as AuthConfiguration);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <RadioGroup value={mode ?? ""} onChange={(_, d) => setMode(d.value)}>
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

      {mode === "fabric_connection" && (
        <Field
          label={t("Wizard_Auth_ConnectionId", "Fabric Connection ID")}
          validationMessage={errors[`${prefix}.fabricConnectionId`]}
          required
        >
          <Input
            value={(auth as any)?.fabricConnectionId ?? ""}
            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            onChange={(_, d) =>
              mergeAuth({ mode: "fabric_connection", fabricConnectionId: d.value })
            }
          />
        </Field>
      )}

      {mode === "keyvault_reference" && (
        <>
          <Field
            label={t("Wizard_Auth_KV_Uri", "Key Vault URI")}
            validationMessage={errors[`${prefix}.keyVaultUri`]}
            required
          >
            <Input
              value={(auth as any)?.keyVaultUri ?? ""}
              placeholder="https://myvault.vault.azure.net/"
              onChange={(_, d) =>
                mergeAuth({ mode: "keyvault_reference", keyVaultUri: d.value })
              }
            />
          </Field>
          <Field
            label={t("Wizard_Auth_KV_SecretName", "Client Secret Name")}
            validationMessage={errors[`${prefix}.clientSecretName`]}
            required
          >
            <Input
              value={(auth as any)?.clientSecretName ?? ""}
              onChange={(_, d) =>
                mergeAuth({ mode: "keyvault_reference", clientSecretName: d.value })
              }
            />
          </Field>
        </>
      )}

      {mode === "service_principal" && (
        <>
          <Field
            label={t("Wizard_Auth_SP_TenantId", "Tenant ID")}
            validationMessage={errors[`${prefix}.sp.tenantId`]}
            required
          >
            <Input
              value={(auth as any)?.tenantId ?? ""}
              onChange={(_, d) =>
                mergeAuth({ mode: "service_principal", tenantId: d.value })
              }
            />
          </Field>
          <Field
            label={t("Wizard_Auth_SP_ClientId", "Client ID")}
            validationMessage={errors[`${prefix}.sp.clientId`]}
            required
          >
            <Input
              value={(auth as any)?.clientId ?? ""}
              onChange={(_, d) =>
                mergeAuth({ mode: "service_principal", clientId: d.value })
              }
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

      {errors[`${prefix}.auth`] && (
        <Text style={{ color: "var(--colorPaletteRedForeground1)" }}>
          {errors[`${prefix}.auth`]}
        </Text>
      )}
    </div>
  );
}

// ── CRM entity selection sub-panel ───────────────────────────────

function CrmEntitiesPanel({
  entry,
  onChange,
}: {
  entry: CrmConnectorEntry;
  onChange: (e: CrmConnectorEntry) => void;
}) {
  const { t } = useTranslation();

  // Scoped workload: entities are locked — show read-only list, no checkboxes.
  if (WORKLOAD_CONFIG.isScoped) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {WORKLOAD_CONFIG.lockedEntityLabels?.map((label) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Text size={300} style={{ color: "var(--colorBrandForeground1)" }}>✓</Text>
            <Text size={300}>{label}</Text>
          </div>
        ))}
        <Text
          size={200}
          style={{ color: "var(--colorNeutralForeground3)", marginTop: 4 }}
        >
          {t("ConnectorConfig_EntitiesLocked", "These entities are fixed for this workload.")}
        </Text>
      </div>
    );
  }

  // Universal Connector: user selects entities via checkboxes.
  const selectedKeys = entry.entities.map((e) => e.logicalName);

  const toggle = (key: string) => {
    const next = selectedKeys.includes(key)
      ? entry.entities.filter((e) => e.logicalName !== key)
      : [...entry.entities, ...expandCrmEntities([key])];
    onChange({ ...entry, entities: next });
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {CRM_CATALOG.map(({ key, label }) => (
        <Checkbox
          key={key}
          label={label}
          checked={selectedKeys.includes(key)}
          onChange={() => toggle(key)}
        />
      ))}
    </div>
  );
}

// ── Status badge ─────────────────────────────────────────────────

function ConnectorStatusBadge({ status }: { status: ConnectorEntry["status"] }) {
  if (status === "valid") {
    return (
      <Badge appearance="filled" color="success">
        Configured
      </Badge>
    );
  }
  if (status === "error") {
    return (
      <Badge appearance="filled" color="danger">
        Incomplete
      </Badge>
    );
  }
  return (
    <Badge appearance="outline" color="informative">
      Not configured
    </Badge>
  );
}

// ── Main panel component ─────────────────────────────────────────

export function ConnectorConfigPanel({
  entry,
  definition,
  validationErrors,
  onChange,
}: ConnectorConfigPanelProps) {
  const { t } = useTranslation();

  const handleAuthChange = (auth: AuthConfiguration | undefined) =>
    onChange({ ...entry, auth } as ConnectorEntry);

  return (
    <Accordion
      collapsible
      defaultOpenItems={[entry.connectorType]}
      style={{
        border: `1px solid var(--colorNeutralStroke1)`,
        borderLeft: `4px solid ${definition.accentColor}`,
        borderRadius: "var(--borderRadiusMedium)",
      }}
    >
      <AccordionItem value={entry.connectorType}>
        <AccordionHeader>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                backgroundColor: definition.accentColor,
              }}
            />
            <Text weight="semibold">{definition.label}</Text>
            <ConnectorStatusBadge status={entry.status} />
          </div>
        </AccordionHeader>

        <AccordionPanel>
          <div
            style={{ display: "flex", flexDirection: "column", gap: 20, padding: "8px 4px 12px" }}
          >
            {/* ── Connection details ─────────────────────── */}
            <section>
              <Text
                size={400}
                weight="semibold"
                block
                style={{ marginBottom: 10, color: "var(--colorNeutralForeground1)" }}
              >
                {t("ConnectorConfig_Source", "Connection")}
              </Text>

              {entry.connectorType === "crm" && (
                <CrmSourcePanel
                  entry={entry}
                  onChange={onChange as (e: CrmConnectorEntry) => void}
                  errors={validationErrors}
                />
              )}
              {entry.connectorType === "businesscentral" && (
                <BcSourcePanel
                  entry={entry}
                  onChange={onChange as (e: BusinessCentralConnectorEntry) => void}
                  errors={validationErrors}
                />
              )}
              {entry.connectorType === "sql" && (
                <SqlSourcePanel
                  entry={entry}
                  onChange={onChange as (e: SqlConnectorEntry) => void}
                  errors={validationErrors}
                />
              )}
            </section>

            {/* ── Authentication ─────────────────────────── */}
            <section>
              <Text
                size={400}
                weight="semibold"
                block
                style={{ marginBottom: 10, color: "var(--colorNeutralForeground1)" }}
              >
                {t("ConnectorConfig_Auth", "Authentication")}
              </Text>
              <AuthPanel
                auth={entry.auth}
                prefix={entry.connectorType}
                errors={validationErrors}
                onChange={handleAuthChange}
              />
            </section>

            {/* ── Entity / table selection ───────────────── */}
            {entry.connectorType === "crm" && (
              <section>
                <Text
                  size={400}
                  weight="semibold"
                  block
                  style={{ marginBottom: 10, color: "var(--colorNeutralForeground1)" }}
                >
                  {t("ConnectorConfig_Entities", "Entities to ingest")}
                </Text>
                <CrmEntitiesPanel
                  entry={entry}
                  onChange={onChange as (e: CrmConnectorEntry) => void}
                />
              </section>
            )}

            {(entry.connectorType === "businesscentral" ||
              entry.connectorType === "sql") && (
              <Text size={300} style={{ color: "var(--colorNeutralForeground3)" }}>
                {t(
                  "ConnectorConfig_EntitiesNote",
                  "Entity / table selection is managed via the connector settings after activation.",
                )}
              </Text>
            )}
          </div>
        </AccordionPanel>
      </AccordionItem>
    </Accordion>
  );
}
