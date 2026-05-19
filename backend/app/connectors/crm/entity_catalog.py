"""CRM Phase 1 entity catalog — 5 Dataverse entities."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass(frozen=True)
class EntityCatalogEntry:
    logical_name: str
    plural_name: str
    primary_key: str
    display_name: str
    supports_change_tracking: bool = True
    default_select_columns: List[str] = field(default_factory=list)


CRM_ENTITY_CATALOG: Dict[str, EntityCatalogEntry] = {
    "contact": EntityCatalogEntry(
        logical_name="contact",
        plural_name="contacts",
        primary_key="contactid",
        display_name="Contact",
        default_select_columns=[
            "contactid", "fullname", "firstname", "lastname",
            "emailaddress1", "emailaddress2", "telephone1", "mobilephone",
            "jobtitle", "department", "accountid", "parentcustomerid",
            "statecode", "statuscode",
            "donotbulkemail", "donotemail", "donotphone",
            "gendercode", "birthdate",
            "address1_city", "address1_country",
            "address1_stateorprovince", "address1_postalcode",
            "ownerid", "owningbusinessunit",
            "createdon", "modifiedon", "overriddencreatedon",
        ],
    ),
    "lead": EntityCatalogEntry(
        logical_name="lead",
        plural_name="leads",
        primary_key="leadid",
        display_name="Lead",
        default_select_columns=[
            "leadid", "fullname", "firstname", "lastname",
            "emailaddress1", "telephone1", "mobilephone",
            "jobtitle", "companyname", "subject",
            "leadsourcecode", "industrycode",
            "statecode", "statuscode",
            "estimatedamount", "estimatedclosedate", "qualifyingopportunityid",
            "ownerid", "owningbusinessunit",
            "createdon", "modifiedon", "overriddencreatedon",
        ],
    ),
    "msdynmkt_marketingform": EntityCatalogEntry(
        logical_name="msdynmkt_marketingform",
        plural_name="msdynmkt_marketingforms",
        primary_key="msdynmkt_marketingformid",
        display_name="Marketing Form",
        default_select_columns=[
            "msdynmkt_marketingformid", "msdynmkt_name",
            "msdynmkt_type", "msdynmkt_purpose",
            "statecode", "statuscode",
            "ownerid", "owningbusinessunit",
            "createdon", "modifiedon",
        ],
    ),
    "msdynmkt_marketingemail": EntityCatalogEntry(
        logical_name="msdynmkt_marketingemail",
        plural_name="msdynmkt_marketingemails",
        primary_key="msdynmkt_marketingemailid",
        display_name="Marketing Email",
        default_select_columns=[
            "msdynmkt_marketingemailid", "msdynmkt_name",
            "msdynmkt_subject", "msdynmkt_previewtext",
            "msdynmkt_fromname", "msdynmkt_fromemail", "msdynmkt_replyto",
            "statecode", "statuscode",
            "ownerid", "owningbusinessunit",
            "createdon", "modifiedon",
        ],
    ),
    "msdynmkt_customerjourney": EntityCatalogEntry(
        logical_name="msdynmkt_customerjourney",
        plural_name="msdynmkt_customerjourneys",
        primary_key="msdynmkt_customerjourneyid",
        display_name="Customer Journey",
        default_select_columns=[
            "msdynmkt_customerjourneyid", "msdynmkt_name",
            "msdynmkt_startdatetime", "msdynmkt_enddatetime",
            "msdynmkt_status", "msdynmkt_type",
            "statecode", "statuscode",
            "ownerid", "owningbusinessunit",
            "createdon", "modifiedon",
        ],
    ),
}
