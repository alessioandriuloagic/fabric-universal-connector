import React from "react";
import { useTranslation } from "react-i18next";
import { Checkbox, Text } from "@fluentui/react-components";
import { CrmEntityConfiguration } from "../ConnectorItemDefinition";
import { WizardStepProps } from "./wizardState";

interface CrmCatalogEntry {
  key: string;
  label: string;
  logicalName: string;
  displayName: string;
  extractionMode: "incremental" | "full";
  selectColumns: string[];
}

export const CRM_CATALOG: CrmCatalogEntry[] = [
  {
    key: "contact",
    logicalName: "contact",
    label: "Contact",
    displayName: "Contact",
    extractionMode: "incremental",
    selectColumns: [
      "contactid", "firstname", "lastname", "fullname",
      "emailaddress1", "telephone1", "mobilephone",
      "statecode", "createdon", "modifiedon",
    ],
  },
  {
    key: "msdynmkt_email",
    logicalName: "msdynmkt_email",
    label: "Marketing Email (Customer Insights Journey)",
    displayName: "Marketing Email (Customer Insights Journey)",
    extractionMode: "incremental",
    selectColumns: [
      "msdynmkt_emailid", "msdynmkt_name", "msdynmkt_subject",
      "msdynmkt_fromname", "msdynmkt_fromemail",
      "statecode", "statuscode", "createdon", "modifiedon",
    ],
  },
  {
    key: "msdynmkt_journey",
    logicalName: "msdynmkt_journey",
    label: "Journey (Customer Insights Journey)",
    displayName: "Journey (Customer Insights Journey)",
    extractionMode: "incremental",
    selectColumns: [
      "msdynmkt_journeyid", "msdynmkt_name",
      "msdynmkt_journeytype", "msdynmkt_start", "msdynmkt_end",
      "statecode", "statuscode", "createdon", "modifiedon",
    ],
  },
];

export function expandCrmEntities(selectedKeys: string[]): CrmEntityConfiguration[] {
  return selectedKeys
    .map((key) => CRM_CATALOG.find((e) => e.key === key))
    .filter((e): e is CrmCatalogEntry => e !== undefined)
    .map((e) => ({
      logicalName: e.logicalName,
      displayName: e.displayName,
      enabled: true,
      extractionMode: e.extractionMode,
      selectColumns: e.selectColumns,
    }));
}

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
