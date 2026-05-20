"""
Workload config: SQL DB Connector
Source: Azure SQL / SQL Server
Entities: user-defined per item — no pre-scoping at workload level
"""
from __future__ import annotations

WORKLOAD_METADATA = {
    "id": "sql-db",
    "display_name": "SQL DB Connector",
    "source": "sql",
    # SQL tables are defined by the user in the wizard, not pre-scoped by the workload
    "entities": [],
}

ALLOWED_ENTITY_NAMES: frozenset[str] = frozenset()
