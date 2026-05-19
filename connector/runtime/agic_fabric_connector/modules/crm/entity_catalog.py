from typing import List, Dict, Any

CRM_ENTITY_CATALOG: List[Dict[str, Any]] = [
    {
        "key": "contact",
        "logical_name": "contact",
        "entity_set_name": "contacts",
        "display_name": "Contact",
        "extraction_mode": "incremental",
        "watermark_type": "delta_token",
        "select_columns": [
            "contactid", "firstname", "lastname", "fullname",
            "emailaddress1", "telephone1", "mobilephone",
            "statecode", "createdon", "modifiedon",
        ],
    },
    {
        "key": "msdynmkt_email",
        "logical_name": "msdynmkt_email",
        "entity_set_name": "msdynmkt_emails",
        "display_name": "Marketing Email (Customer Insights Journey)",
        "extraction_mode": "incremental",
        "watermark_type": "delta_token",
        "select_columns": [
            "msdynmkt_emailid", "msdynmkt_name", "msdynmkt_subject",
            "msdynmkt_fromname", "msdynmkt_fromemail",
            "statecode", "statuscode", "createdon", "modifiedon",
        ],
    },
    {
        "key": "msdynmkt_journey",
        "logical_name": "msdynmkt_journey",
        "entity_set_name": "msdynmkt_journeys",
        "display_name": "Journey (Customer Insights Journey)",
        "extraction_mode": "incremental",
        "watermark_type": "delta_token",
        "select_columns": [
            "msdynmkt_journeyid", "msdynmkt_name",
            "msdynmkt_journeytype", "msdynmkt_start", "msdynmkt_end",
            "statecode", "statuscode", "createdon", "modifiedon",
        ],
    },
]

ENTITY_CATALOG_BY_KEY: Dict[str, Dict[str, Any]] = {
    e["key"]: e for e in CRM_ENTITY_CATALOG
}
