"""
Workload config: Sales CRM
Source: Dynamics 365 / Dataverse (CRM module)
Entities: sales-pipeline entities — explicitly distinct from Customer Insight Journey
          (CIJ owns: contact, msdynmkt_email, msdynmkt_journey)

Entity field semantics:
  logical_name  — Dataverse entity logical name
  display_name  — human-readable label for the UI
  bronze_table  — Delta table path under the Bronze Lakehouse
"""
from __future__ import annotations

WORKLOAD_METADATA = {
    "id": "sales-crm",
    "display_name": "Sales CRM",
    "source": "crm",
    "entities": [
        {
            "logical_name": "lead",
            "display_name": "Lead",
            "bronze_table": "bronze_crm/lead",
        },
        {
            "logical_name": "opportunity",
            "display_name": "Opportunity",
            "bronze_table": "bronze_crm/opportunity",
        },
        {
            "logical_name": "account",
            "display_name": "Account",
            "bronze_table": "bronze_crm/account",
        },
        {
            "logical_name": "contact",
            "display_name": "Contact",
            "bronze_table": "bronze_crm/contact",
        },
        {
            "logical_name": "quote",
            "display_name": "Quote",
            "bronze_table": "bronze_crm/quote",
        },
        {
            "logical_name": "salesorder",
            "display_name": "Sales Order",
            "bronze_table": "bronze_crm/salesorder",
        },
        {
            "logical_name": "invoice",
            "display_name": "Invoice",
            "bronze_table": "bronze_crm/invoice",
        },
    ],
}

ALLOWED_ENTITY_NAMES: frozenset[str] = frozenset(
    e["logical_name"] for e in WORKLOAD_METADATA["entities"]
)
