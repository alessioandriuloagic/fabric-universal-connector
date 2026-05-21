/**
 * crmCatalog.ts
 *
 * Catalog of pre-defined Dataverse / Dynamics 365 CRM entities available for
 * selection in the connector configuration UI.
 *
 * Extracted from WizardEntityStep so it can be shared by both the legacy
 * WizardEntityStep (backward compat) and the new ConnectorConfigPanel.
 *
 * Entity grouping:
 *   - Customer Insight Journey (CIJ): contact, msdynmkt_email, msdynmkt_journey
 *   - Sales CRM: lead, opportunity, account, quote, salesorder, invoice
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
  // ── Customer Insight Journey entities ──────────────────────────
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

  // ── Sales CRM entities ──────────────────────────────────────────
  {
    key: "lead",
    logicalName: "lead",
    label: "Lead",
    displayName: "Lead",
    extractionMode: "incremental",
    selectColumns: [
      "leadid", "fullname", "firstname", "lastname",
      "emailaddress1", "telephone1", "mobilephone",
      "jobtitle", "companyname", "subject",
      "leadsourcecode", "industrycode",
      "statecode", "statuscode",
      "estimatedamount", "estimatedclosedate",
      "ownerid", "createdon", "modifiedon",
    ],
  },
  {
    key: "opportunity",
    logicalName: "opportunity",
    label: "Opportunity",
    displayName: "Opportunity",
    extractionMode: "incremental",
    selectColumns: [
      "opportunityid", "name", "description",
      "estimatedvalue", "estimatedclosedate", "actualvalue", "actualclosedate",
      "closeprobability", "salesstage", "stepname",
      "statecode", "statuscode",
      "customerid", "ownerid", "parentaccountid",
      "createdon", "modifiedon",
    ],
  },
  {
    key: "account",
    logicalName: "account",
    label: "Account",
    displayName: "Account",
    extractionMode: "incremental",
    selectColumns: [
      "accountid", "name", "accountnumber",
      "emailaddress1", "telephone1", "websiteurl",
      "address1_city", "address1_country", "address1_postalcode",
      "industrycode", "numberofemployees", "revenue",
      "statecode", "statuscode",
      "ownerid", "createdon", "modifiedon",
    ],
  },
  {
    key: "quote",
    logicalName: "quote",
    label: "Quote",
    displayName: "Quote",
    extractionMode: "incremental",
    selectColumns: [
      "quoteid", "name", "quotenumber",
      "totallineitemamount", "totaltax", "totalamount", "discountamount",
      "effectivefrom", "effectiveto", "statecode", "statuscode",
      "customerid", "ownerid", "opportunityid",
      "createdon", "modifiedon",
    ],
  },
  {
    key: "salesorder",
    logicalName: "salesorder",
    label: "Sales Order",
    displayName: "Sales Order",
    extractionMode: "incremental",
    selectColumns: [
      "salesorderid", "name", "ordernumber",
      "totallineitemamount", "totaltax", "totalamount", "discountamount",
      "datefulfilled", "statecode", "statuscode",
      "customerid", "ownerid", "quoteid",
      "createdon", "modifiedon",
    ],
  },
  {
    key: "invoice",
    logicalName: "invoice",
    label: "Invoice",
    displayName: "Invoice",
    extractionMode: "incremental",
    selectColumns: [
      "invoiceid", "name", "invoicenumber",
      "totallineitemamount", "totaltax", "totalamount", "discountamount",
      "duedate", "statecode", "statuscode",
      "customerid", "ownerid", "salesorderid",
      "createdon", "modifiedon",
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
