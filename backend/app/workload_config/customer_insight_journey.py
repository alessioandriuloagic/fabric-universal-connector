"""
Workload config: Customer Insight Journey
Source: Dynamics 365 / Dataverse (CRM module)
Entities: contact, msdynmkt_email, msdynmkt_journey
"""
from __future__ import annotations

WORKLOAD_METADATA = {
    "id": "customer-insight-journey",
    "display_name": "Customer Insight Journey",
    "source": "crm",
    "entities": [
        {
            "logical_name": "contact",
            "display_name": "Contact",
            "bronze_table": "bronze_crm/contact",
        },
        {
            "logical_name": "msdynmkt_email",
            "display_name": "Marketing Email (Customer Insights Journey)",
            "bronze_table": "bronze_crm/msdynmkt_email",
        },
        {
            "logical_name": "msdynmkt_journey",
            "display_name": "Journey (Customer Insights Journey)",
            "bronze_table": "bronze_crm/msdynmkt_journey",
        },
    ],
}

ALLOWED_ENTITY_NAMES: frozenset[str] = frozenset(
    e["logical_name"] for e in WORKLOAD_METADATA["entities"]
)
