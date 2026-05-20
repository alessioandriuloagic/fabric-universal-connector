/**
 * crmCatalog.ts
 *
 * Catalog of pre-defined Dataverse / Dynamics 365 CRM entities available for
 * selection in the connector configuration UI.
 *
 * Extracted from WizardEntityStep so it can be shared by both the legacy
 * WizardEntityStep (backward compat) and the new ConnectorConfigPanel.
 */
import { CrmEntityConfiguration } from "../ConnectorItemDefinition";

export interface CrmCatalogEntry {
  /** Unique key used as the selection identifier in the UI. */
  key: string;
  /** Human-readable label shown in the entity selection list. */
  label: string;
  /** Dataverse logical entity name sent to the API. */
  logicalName: string;
  /** Display name stored in the entity configuration. */
  displayName: string;
  extractionMode: "incremental" | "full";
  /** Default $select columns; users can override in advanced settings. */
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

/**
 * Expands a list of catalog keys into full `CrmEntityConfiguration` objects
 * ready to be stored in the item definition.
 */
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
