"""
Workload config: Business Central
Source: Dynamics 365 Business Central OData v4
Entities: all current BC entities (to be enumerated from bc_connector catalog)
"""
from __future__ import annotations

WORKLOAD_METADATA = {
    "id": "business-central",
    "display_name": "Business Central",
    "source": "businesscentral",
    "entities": [
        # TODO: populate from bc_connector entity catalog
        # BC entities use api_endpoint rather than logical_name
    ],
}

ALLOWED_ENTITY_NAMES: frozenset[str] = frozenset(
    e.get("api_endpoint", e.get("logical_name", ""))
    for e in WORKLOAD_METADATA["entities"]
)
