"""
Workload identity resolution for multi-workload backend routing.

Each workload frontend injects an X-Workload-Id header on every request.
The backend uses this header to scope which entities are available and to
route job execution to the correct workload configuration.

Fallback: if the header is absent (legacy Universal Connector callers),
WorkloadId.UNIVERSAL is used — no entity restriction is applied.
"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Any, Dict

from fastapi import Header, HTTPException, status


class WorkloadId(str, Enum):
    CUSTOMER_INSIGHT_JOURNEY = "customer-insight-journey"
    SALES_CRM = "sales-crm"
    BUSINESS_CENTRAL = "business-central"
    SQL_DB = "sql-db"
    UNIVERSAL = "universal"


async def get_workload_id(
    x_workload_id: str = Header(default=WorkloadId.UNIVERSAL.value, alias="X-Workload-Id"),
) -> WorkloadId:
    try:
        return WorkloadId(x_workload_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid X-Workload-Id: '{x_workload_id}'. "
                f"Valid values: {[w.value for w in WorkloadId]}"
            ),
        )


@lru_cache(maxsize=8)
def load_workload_config(workload_id: WorkloadId) -> Dict[str, Any]:
    """Return the workload metadata dict for the given workload ID."""
    if workload_id == WorkloadId.CUSTOMER_INSIGHT_JOURNEY:
        from app.workload_config.customer_insight_journey import WORKLOAD_METADATA
        return WORKLOAD_METADATA
    if workload_id == WorkloadId.SALES_CRM:
        from app.workload_config.sales_crm import WORKLOAD_METADATA
        return WORKLOAD_METADATA
    if workload_id == WorkloadId.BUSINESS_CENTRAL:
        from app.workload_config.business_central import WORKLOAD_METADATA
        return WORKLOAD_METADATA
    if workload_id == WorkloadId.SQL_DB:
        from app.workload_config.sql_db import WORKLOAD_METADATA
        return WORKLOAD_METADATA
    # UNIVERSAL — no entity restriction
    return {"id": "universal", "display_name": "Universal Connector", "source": None, "entities": None}
