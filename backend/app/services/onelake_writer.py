"""
OneLake Delta Lake writer.

Uses delta-rs (deltalake Python bindings) + PyArrow to write DataFrames
directly to OneLake via ABFS protocol — no Spark required.

OneLake ABFS endpoint pattern:
  abfss://onelake@onelake.dfs.fabric.microsoft.com/{workspaceId}/{lakeHouseId}.Lakehouse/Tables/{schema}/{table}

Ref: https://learn.microsoft.com/en-us/fabric/onelake/onelake-access-api
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
import pyarrow as pa
from deltalake import write_deltalake, DeltaTable
from deltalake.exceptions import TableNotFoundError

from app.exceptions import BronzeWriteError, SchemaConflictError
from app.models.connector_item_definition import SchemaEvolutionPolicy

log = logging.getLogger(__name__)

ONELAKE_HOST = "onelake.dfs.fabric.microsoft.com"
WHEEL_VERSION = os.getenv("WHEEL_VERSION", "0.1.0")


def _build_abfs_path(
    workspace_id: str,
    lakehouse_id: str,
    schema: str,
    table: str,
) -> str:
    return (
        f"abfss://onelake@{ONELAKE_HOST}"
        f"/{workspace_id}/{lakehouse_id}.Lakehouse/Tables/{schema}/{table}"
    )


def _get_storage_options(bearer_token: str) -> Dict[str, str]:
    """
    ABFS storage options for delta-rs.
    Uses the Fabric bearer token for OneLake access.
    """
    return {
        "bearer_token": bearer_token,
        "use_fabric_endpoint": "true",
    }


def _add_metadata_columns(
    df: pd.DataFrame,
    run_id: str,
    connector_id: str,
    module_type: str,
    entity_name: str,
) -> pd.DataFrame:
    """Appends the 12 ISV metadata columns to the DataFrame."""
    now_utc = datetime.now(timezone.utc)

    df = df.copy()
    df["_run_id"] = run_id
    df["_connector_id"] = connector_id
    df["_module_type"] = module_type
    df["_entity_name"] = entity_name
    df["_operation"] = df.get("_operation", "insert")
    df["_is_current"] = True
    df["_ingestion_utc"] = now_utc
    df["_ingestion_date"] = now_utc.date().isoformat()
    df["_source_modified_utc"] = None
    df["_source_row_version"] = None
    df["_schema_version"] = ""
    df["_wheel_version"] = WHEEL_VERSION

    return df


def _detect_schema_conflicts(
    existing_schema: pa.Schema,
    new_schema: pa.Schema,
) -> List[Dict[str, Any]]:
    """Returns a list of schema change events (column added / removed / type changed)."""
    changes = []
    existing_fields = {f.name: f.type for f in existing_schema}
    new_fields = {f.name: f.type for f in new_schema}

    for name, new_type in new_fields.items():
        if name.startswith("_"):
            continue
        if name not in existing_fields:
            changes.append({"change_type": "column_added", "column": name, "new_type": str(new_type)})
        elif existing_fields[name] != new_type:
            changes.append({
                "change_type": "type_changed",
                "column": name,
                "old_type": str(existing_fields[name]),
                "new_type": str(new_type),
            })

    for name in existing_fields:
        if name.startswith("_"):
            continue
        if name not in new_fields:
            changes.append({"change_type": "column_removed", "column": name})

    return changes


async def write_bronze(
    df: pd.DataFrame,
    *,
    workspace_id: str,
    lakehouse_id: str,
    schema: str,
    table: str,
    run_id: str,
    connector_id: str,
    module_type: str,
    entity_name: str,
    bearer_token: str,
    schema_evolution_policy: SchemaEvolutionPolicy = SchemaEvolutionPolicy.MERGE,
) -> int:
    """
    Writes a pandas DataFrame to a Bronze Delta table on OneLake.

    Returns the number of rows written.
    Raises BronzeWriteError or SchemaConflictError.
    """
    if df.empty:
        log.info("Empty DataFrame for %s.%s — skipping write", schema, table)
        return 0

    df = _add_metadata_columns(df, run_id, connector_id, module_type, entity_name)

    arrow_table = pa.Table.from_pandas(df, preserve_index=False)
    path = _build_abfs_path(workspace_id, lakehouse_id, schema, table)
    storage_opts = _get_storage_options(bearer_token)

    log.info(
        "Writing %d rows to %s.%s (policy=%s)",
        len(df), schema, table, schema_evolution_policy.value
    )

    try:
        existing_dt: Optional[DeltaTable] = None
        try:
            existing_dt = DeltaTable(path, storage_options=storage_opts)
        except TableNotFoundError:
            pass

        if existing_dt is not None:
            conflicts = _detect_schema_conflicts(
                existing_dt.schema().to_pyarrow(), arrow_table.schema
            )
            if conflicts:
                if schema_evolution_policy == SchemaEvolutionPolicy.STRICT:
                    raise SchemaConflictError(
                        f"Schema conflict in {schema}.{table}: {conflicts}"
                    )
                if schema_evolution_policy == SchemaEvolutionPolicy.OVERWRITE:
                    log.warning(
                        "Schema overwrite for %s.%s: %s", schema, table, conflicts
                    )

        write_mode = (
            "overwrite"
            if schema_evolution_policy == SchemaEvolutionPolicy.OVERWRITE and existing_dt
            else "append"
        )
        schema_mode = (
            "merge"
            if schema_evolution_policy == SchemaEvolutionPolicy.MERGE
            else "overwrite"
        )

        write_deltalake(
            path,
            arrow_table,
            mode=write_mode,
            schema_mode=schema_mode,
            partition_by=["_ingestion_date"],
            storage_options=storage_opts,
        )

        rows_written = len(df)
        log.info("Wrote %d rows to %s.%s", rows_written, schema, table)
        return rows_written

    except SchemaConflictError:
        raise
    except Exception as exc:
        raise BronzeWriteError(
            f"Delta write failed for {schema}.{table}: {exc}"
        ) from exc


async def upsert_watermark(
    *,
    workspace_id: str,
    lakehouse_id: str,
    schema: str,
    connector_id: str,
    entity_name: str,
    module_type: str,
    watermark_type: str,
    delta_token: Optional[str],
    watermark_value: Optional[str],
    watermark_column: Optional[str],
    run_id: str,
    records_at_last_run: int,
    bearer_token: str,
) -> None:
    """Upserts a row in _entity_watermarks via delta-rs merge."""
    from deltalake.writer import write_deltalake as _write

    path = _build_abfs_path(workspace_id, lakehouse_id, schema, "_meta/_entity_watermarks")
    storage_opts = _get_storage_options(bearer_token)
    now = datetime.now(timezone.utc).isoformat()

    row = {
        "connector_id": connector_id,
        "entity_name": entity_name,
        "module_type": module_type,
        "watermark_type": watermark_type,
        "delta_token": delta_token,
        "watermark_value": watermark_value,
        "watermark_column": watermark_column,
        "last_run_id": run_id,
        "last_success_utc": now,
        "records_at_last_run": records_at_last_run,
        "records_at_source_est": None,
        "is_initial_load_complete": True,
        "workspace_id": workspace_id,
    }

    df = pd.DataFrame([row])
    arrow_table = pa.Table.from_pandas(df, preserve_index=False)

    try:
        try:
            dt = DeltaTable(path, storage_options=storage_opts)
            (
                dt.merge(
                    source=arrow_table,
                    predicate=(
                        "s.connector_id = t.connector_id "
                        "AND s.entity_name = t.entity_name"
                    ),
                    source_alias="s",
                    target_alias="t",
                )
                .when_matched_update_all()
                .when_not_matched_insert_all()
                .execute()
            )
        except TableNotFoundError:
            _write(path, arrow_table, mode="append", storage_options=storage_opts)

        log.debug("Watermark upserted for %s/%s", connector_id, entity_name)

    except Exception as exc:
        log.warning("Watermark upsert failed for %s: %s", entity_name, exc)


async def write_run_record(
    record: Dict[str, Any],
    *,
    workspace_id: str,
    lakehouse_id: str,
    schema: str,
    bearer_token: str,
    mode: str = "append",
) -> None:
    """Appends or merges a run record into _connector_runs."""
    from deltalake.writer import write_deltalake as _write

    path = _build_abfs_path(workspace_id, lakehouse_id, schema, "_meta/_connector_runs")
    storage_opts = _get_storage_options(bearer_token)
    df = pd.DataFrame([record])
    arrow_table = pa.Table.from_pandas(df, preserve_index=False)

    try:
        try:
            dt = DeltaTable(path, storage_options=storage_opts)
            if mode == "merge":
                (
                    dt.merge(
                        source=arrow_table,
                        predicate="s.run_id = t.run_id",
                        source_alias="s",
                        target_alias="t",
                    )
                    .when_matched_update_all()
                    .when_not_matched_insert_all()
                    .execute()
                )
                return
        except TableNotFoundError:
            pass

        _write(path, arrow_table, mode="append", storage_options=storage_opts)

    except Exception as exc:
        log.warning("Run record write failed: %s", exc)
