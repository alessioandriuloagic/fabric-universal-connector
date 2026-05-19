"""Tests for onelake_writer — schema detection, metadata columns, path building."""
import pytest
import pandas as pd
import pyarrow as pa

from app.services.onelake_writer import (
    _build_abfs_path,
    _add_metadata_columns,
    _detect_schema_conflicts,
)


# ── _build_abfs_path ──────────────────────────────────────────────────────────

def test_build_abfs_path_correct_format():
    path = _build_abfs_path("ws-001", "lh-001", "bronze_crm", "contact")
    assert path == (
        "abfss://onelake@onelake.dfs.fabric.microsoft.com"
        "/ws-001/lh-001.Lakehouse/Tables/bronze_crm/contact"
    )


def test_build_abfs_path_meta_table():
    path = _build_abfs_path("ws-1", "lh-1", "bronze_crm", "_meta/_entity_watermarks")
    assert "_meta/_entity_watermarks" in path
    assert "lh-1.Lakehouse" in path


# ── _add_metadata_columns ─────────────────────────────────────────────────────

EXPECTED_META_COLS = [
    "_run_id", "_connector_id", "_module_type", "_entity_name",
    "_operation", "_is_current", "_ingestion_utc", "_ingestion_date",
    "_source_modified_utc", "_source_row_version", "_schema_version", "_wheel_version",
]


def test_add_metadata_columns_adds_all_12():
    df = pd.DataFrame({"id": [1, 2], "name": ["Alice", "Bob"]})
    result = _add_metadata_columns(df, "run1", "conn1", "crm", "contact")
    for col in EXPECTED_META_COLS:
        assert col in result.columns, f"Missing metadata column: {col}"


def test_add_metadata_columns_values_correct():
    df = pd.DataFrame({"id": [1]})
    result = _add_metadata_columns(df, "run-xyz", "conn-abc", "crm", "lead")
    assert result["_run_id"].iloc[0] == "run-xyz"
    assert result["_connector_id"].iloc[0] == "conn-abc"
    assert result["_module_type"].iloc[0] == "crm"
    assert result["_entity_name"].iloc[0] == "lead"
    assert result["_is_current"].iloc[0] is True


def test_add_metadata_columns_preserves_existing_operation():
    df = pd.DataFrame({"id": [1], "_operation": ["delete"]})
    result = _add_metadata_columns(df, "r", "c", "crm", "entity")
    assert result["_operation"].iloc[0] == "delete"


def test_add_metadata_columns_defaults_operation_to_insert():
    df = pd.DataFrame({"id": [1]})
    result = _add_metadata_columns(df, "r", "c", "crm", "entity")
    assert result["_operation"].iloc[0] == "insert"


def test_add_metadata_columns_does_not_modify_original():
    df = pd.DataFrame({"id": [1, 2]})
    original_cols = list(df.columns)
    _add_metadata_columns(df, "r", "c", "crm", "entity")
    assert list(df.columns) == original_cols


# ── _detect_schema_conflicts ──────────────────────────────────────────────────

def test_detect_schema_conflicts_no_changes():
    schema = pa.schema([pa.field("id", pa.int64()), pa.field("name", pa.string())])
    conflicts = _detect_schema_conflicts(schema, schema)
    assert conflicts == []


def test_detect_schema_conflicts_column_added():
    old = pa.schema([pa.field("id", pa.int64())])
    new = pa.schema([pa.field("id", pa.int64()), pa.field("email", pa.string())])
    conflicts = _detect_schema_conflicts(old, new)
    assert len(conflicts) == 1
    assert conflicts[0]["change_type"] == "column_added"
    assert conflicts[0]["column"] == "email"


def test_detect_schema_conflicts_column_removed():
    old = pa.schema([pa.field("id", pa.int64()), pa.field("email", pa.string())])
    new = pa.schema([pa.field("id", pa.int64())])
    conflicts = _detect_schema_conflicts(old, new)
    assert len(conflicts) == 1
    assert conflicts[0]["change_type"] == "column_removed"
    assert conflicts[0]["column"] == "email"


def test_detect_schema_conflicts_type_changed():
    old = pa.schema([pa.field("amount", pa.int64())])
    new = pa.schema([pa.field("amount", pa.float64())])
    conflicts = _detect_schema_conflicts(old, new)
    assert len(conflicts) == 1
    assert conflicts[0]["change_type"] == "type_changed"
    assert conflicts[0]["column"] == "amount"


def test_detect_schema_conflicts_multiple_changes():
    old = pa.schema([pa.field("id", pa.int64()), pa.field("old_col", pa.string())])
    new = pa.schema([pa.field("id", pa.int64()), pa.field("new_col", pa.string())])
    conflicts = _detect_schema_conflicts(old, new)
    change_types = {c["change_type"] for c in conflicts}
    assert "column_added" in change_types
    assert "column_removed" in change_types


def test_detect_schema_conflicts_ignores_metadata_columns():
    old = pa.schema([pa.field("_run_id", pa.string())])
    new = pa.schema([pa.field("_run_id", pa.int64())])  # type changed but ISV metadata
    conflicts = _detect_schema_conflicts(old, new)
    assert conflicts == []


# ── write_bronze: empty DataFrame guard ───────────────────────────────────────

async def test_write_bronze_skips_empty_df():
    from unittest.mock import patch, MagicMock
    from app.services.onelake_writer import write_bronze

    with patch("app.services.onelake_writer.write_deltalake") as mock_write:
        rows = await write_bronze(
            pd.DataFrame(),
            workspace_id="ws1", lakehouse_id="lh1",
            schema="bronze_crm", table="contact",
            run_id="r1", connector_id="c1",
            module_type="crm", entity_name="contact",
            bearer_token="tok",
        )
    assert rows == 0
    mock_write.assert_not_called()
