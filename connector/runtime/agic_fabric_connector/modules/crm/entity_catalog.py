from typing import List, Dict, Any

CRM_ENTITY_CATALOG: List[Dict[str, Any]] = [
    {
        "key": "contact",
        "logical_name": "contact",
        "display_name": "Contact",
        "extraction_mode": "incremental",
        "watermark_type": "delta_token",
        "select_columns": ["contactid", "fullname", "emailaddress1", "telephone1", "modifiedon"],
    },
    {
        "key": "lead",
        "logical_name": "lead",
        "display_name": "Lead",
        "extraction_mode": "incremental",
        "watermark_type": "delta_token",
        "select_columns": ["leadid", "fullname", "emailaddress1", "subject", "statuscode", "modifiedon"],
    },
    {
        "key": "msdynmkt_marketingform",
        "logical_name": "msdynmkt_marketingform",
        "display_name": "Marketing Form",
        "extraction_mode": "incremental",
        "watermark_type": "delta_token",
        "select_columns": ["msdynmkt_marketingformid", "msdynmkt_name", "statecode", "modifiedon"],
    },
    {
        "key": "msdynmkt_marketingemail",
        "logical_name": "msdynmkt_marketingemail",
        "display_name": "Marketing Email",
        "extraction_mode": "incremental",
        "watermark_type": "delta_token",
        "select_columns": ["msdynmkt_marketingemailid", "msdynmkt_name", "statecode", "modifiedon"],
    },
    {
        "key": "msdynmkt_customerjourney",
        "logical_name": "msdynmkt_customerjourney",
        "display_name": "Customer Journey",
        "extraction_mode": "incremental",
        "watermark_type": "delta_token",
        "select_columns": ["msdynmkt_customerjourneyid", "msdynmkt_name", "statecode", "modifiedon"],
    },
]
