import os
import pandas as pd
import json
import asyncio
from datetime import datetime
from typing import List
from connectors.base import ChangeEvent
from storage import storage

# Local landing zone folder for development
LOCAL_LANDING = os.path.join(os.getcwd(), "local_landing_zone")
os.makedirs(LOCAL_LANDING, exist_ok=True)

# Import onelake bridge helper to build OneLakeManager instances
from onelake_bridge import get_onelake_manager


async def write_events(events: List[ChangeEvent]):
    """Write events using OneLakeManager when available, fall back to local CSV.

    For each tenant/item/entity group, this function:
    - converts the list of ChangeEvent into a pandas.DataFrame with __rowMarker__
    - obtains a OneLakeManager configured for the item via onelake_bridge.get_onelake_manager
    - calls manager.upload(df, namespace, entity)

    The manager.upload method in backend_2 is synchronous; to avoid blocking the
    async event loop it is executed in a thread via asyncio.to_thread().

    If OneLakeManager cannot be constructed (missing backend_2 or Key Vault), the
    writer falls back to writing CSV files locally in local_landing_zone for
    development and testing.
    """
    if not events:
        return True

    # Group by item_id and entity_type to process per table
    grouped = {}
    for ev in events:
        key = (ev.tenant_id, ev.item_id, ev.entity_type)
        grouped.setdefault(key, []).append(ev)

    for (tenant_id, item_id, entity), evs in grouped.items():
        # Convert events list into rows
        rows = []
        for ev in evs:
            row = ev.payload.copy() if ev.payload else {}
            marker = 0
            if ev.change_type.name.lower() == "insert":
                marker = 0
            elif ev.change_type.name.lower() == "update":
                marker = 1
            elif ev.change_type.name.lower() == "delete":
                marker = 2
            row["__rowMarker__"] = marker
            rows.append(row)

        df = pd.DataFrame(rows)

        # Determine namespace (source-specific). Prefer payload 'company' for BC, else tenant_id
        namespace = None
        if not df.empty:
            # common patterns: BC uses 'Company' or 'company', CRM may use 'namespace'
            for col in ("Company", "company", "namespace"):
                if col in df.columns:
                    namespace = df[col].iloc[0]
                    break
        if not namespace:
            namespace = tenant_id

        # Try to build OneLakeManager for this item and upload
        item = {"tenant_id": tenant_id, "item_id": item_id}
        try:
            manager = get_onelake_manager(item)
            # run blocking upload in thread
            await asyncio.to_thread(manager.upload, df, namespace, entity)
        except Exception as e:
            # Fall back to local CSV writer with verbose logging
            print(f"[WARN] OneLake upload failed for {tenant_id}/{item_id}/{entity}: {e}")
            target_dir = os.path.join(LOCAL_LANDING, tenant_id, item_id, entity)
            os.makedirs(target_dir, exist_ok=True)
            seq = storage.get_next_sequence(item_id, entity)
            filename = f"{seq:020d}.csv"
            path = os.path.join(target_dir, filename)
            df.to_csv(path, index=False, encoding="utf-8", quoting=1, line_terminator="\r\n")
            storage.increment_sequence(item_id, entity)

    return True
