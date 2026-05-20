"""
Workload config: Sales CRM
Source: Dynamics 365 / Dataverse (CRM module)
Entities: sales-specific (opportunity, account, quote, order — TBD)
"""
from __future__ import annotations

WORKLOAD_METADATA = {
    "id": "sales-crm",
    "display_name": "Sales CRM",
    "source": "crm",
    "entities": [
        # TODO: define sales-specific CRM entities once entity catalog is extended
        # Examples: opportunity, account, quote, salesorder, invoice
    ],
}

ALLOWED_ENTITY_NAMES: frozenset[str] = frozenset(
    e["logical_name"] for e in WORKLOAD_METADATA["entities"]
)
