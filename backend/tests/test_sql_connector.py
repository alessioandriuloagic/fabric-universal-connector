"""Tests for SQL connector — query building, watermark, table naming."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from app.connectors.sql.sql_connector import _normalize_table_name, SQLAuthContext
from app.connectors.base_connector import Watermark


# ── _normalize_table_name ─────────────────────────────────────────────────────

def test_normalize_table_name_basic():
    assert _normalize_table_name("dbo", "Orders") == "dbo_orders"


def test_normalize_table_name_mixed_case():
    assert _normalize_table_name("Sales", "CustomerOrders") == "sales_customerorders"


def test_normalize_table_name_spaces():
    assert _normalize_table_name("dbo", "Order Details") == "dbo_order_details"


def test_normalize_table_name_already_lower():
    assert _normalize_table_name("hr", "employees") == "hr_employees"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def sql_entity():
    from app.models.connector_item_definition import SqlEntityConfiguration
    return SqlEntityConfiguration.model_validate({
        "schema": "dbo",
        "tableName": "Orders",
        "displayName": "Orders",
        "enabled": True,
    })


@pytest.fixture
def sql_entity_with_watermark():
    from app.models.connector_item_definition import SqlEntityConfiguration
    return SqlEntityConfiguration.model_validate({
        "schema": "dbo",
        "tableName": "Orders",
        "displayName": "Orders",
        "enabled": True,
        "watermarkColumn": "ModifiedAt",
        "watermarkColumnType": "datetime",
    })


@pytest.fixture
def sql_entity_integer_watermark():
    from app.models.connector_item_definition import SqlEntityConfiguration
    return SqlEntityConfiguration.model_validate({
        "schema": "dbo",
        "tableName": "Events",
        "displayName": "Events",
        "enabled": True,
        "watermarkColumn": "EventId",
        "watermarkColumnType": "integer",
    })


@pytest.fixture
def sql_connector_instance():
    from app.connectors.sql.sql_connector import SQLConnector
    from app.models.connector_item_definition import (
        SqlConnectorItemDefinition,
        SqlSourceConfiguration,
        ConnectorState,
    )
    from app.services.auth_service import ResolvedCredentials

    config = SqlConnectorItemDefinition(
        state=ConnectorState.CONFIGURED,
        moduleType="sql",
        source=SqlSourceConfiguration(server="srv.database.windows.net", database="mydb"),
        entities=[],
    )
    return SQLConnector(
        config=config,
        workspace_id="ws1",
        lakehouse_id="lh1",
        connector_id="conn1",
        bearer_token="tok",
        credentials=ResolvedCredentials(tenant_id=None, client_id="user", client_secret="pass"),
    )


# ── _extract_entity: query construction ───────────────────────────────────────

async def test_extract_entity_full_load_no_watermark(sql_connector_instance, sql_entity):
    mock_df = pd.DataFrame({"id": [1, 2], "amount": [100.0, 200.0]})
    captured_queries = []
    captured_params = []

    def capture(conn_str, query, params=None):
        captured_queries.append(query)
        captured_params.append(params)
        return mock_df

    with patch("app.connectors.sql.sql_connector._run_sql_query", side_effect=capture):
        auth = SQLAuthContext(connection_string="mssql+pyodbc://user:pass@srv/db")
        result = await sql_connector_instance._extract_entity(sql_entity, auth, None)

    assert len(captured_queries) == 1
    query = captured_queries[0]
    assert "SELECT *" in query
    assert "[dbo].[Orders]" in query
    assert "WHERE" not in query
    assert captured_params[0] is None
    assert "_operation" in result.columns
    assert result["_operation"].iloc[0] == "insert"


async def test_extract_entity_datetime_watermark(sql_connector_instance, sql_entity_with_watermark):
    mock_df = pd.DataFrame({"id": [3], "ModifiedAt": ["2024-06-01T00:00:00"]})
    captured_queries = []
    captured_params = []

    def capture(conn_str, query, params=None):
        captured_queries.append(query)
        captured_params.append(params)
        return mock_df

    watermark = Watermark(
        watermark_type="datetime",
        watermark_value="2024-01-01T00:00:00",
        watermark_column="ModifiedAt",
    )

    with patch("app.connectors.sql.sql_connector._run_sql_query", side_effect=capture):
        auth = SQLAuthContext(connection_string="mssql+pyodbc://...")
        await sql_connector_instance._extract_entity(sql_entity_with_watermark, auth, watermark)

    query = captured_queries[0]
    params = captured_params[0]
    assert "WHERE" in query
    assert "[ModifiedAt] > :wm_val" in query
    assert "ORDER BY [ModifiedAt] ASC" in query
    assert params == {"wm_val": "2024-01-01T00:00:00"}


async def test_extract_entity_integer_watermark(sql_connector_instance, sql_entity_integer_watermark):
    mock_df = pd.DataFrame({"EventId": [101]})
    captured_queries = []
    captured_params = []

    def capture(conn_str, query, params=None):
        captured_queries.append(query)
        captured_params.append(params)
        return mock_df

    watermark = Watermark(
        watermark_type="integer",
        watermark_value="100",
        watermark_column="EventId",
    )

    with patch("app.connectors.sql.sql_connector._run_sql_query", side_effect=capture):
        auth = SQLAuthContext(connection_string="mssql+pyodbc://...")
        await sql_connector_instance._extract_entity(sql_entity_integer_watermark, auth, watermark)

    query = captured_queries[0]
    params = captured_params[0]
    assert "[EventId] > :wm_val" in query
    assert params == {"wm_val": 100}


async def test_extract_entity_select_columns(sql_connector_instance):
    from app.models.connector_item_definition import SqlEntityConfiguration
    entity = SqlEntityConfiguration.model_validate({
        "schema": "dbo",
        "tableName": "Customers",
        "displayName": "Customers",
        "enabled": True,
        "selectColumns": ["id", "name", "email"],
    })
    captured_queries = []

    def capture(conn_str, query, params=None):
        captured_queries.append(query)
        return pd.DataFrame({"id": [], "name": [], "email": []})

    with patch("app.connectors.sql.sql_connector._run_sql_query", side_effect=capture):
        auth = SQLAuthContext(connection_string="mssql+pyodbc://...")
        await sql_connector_instance._extract_entity(entity, auth, None)

    query = captured_queries[0]
    assert "[id], [name], [email]" in query
    assert "SELECT *" not in query


# ── _get_new_watermark ────────────────────────────────────────────────────────

def test_get_new_watermark_returns_max_value(sql_connector_instance, sql_entity_with_watermark):
    df = pd.DataFrame({"ModifiedAt": ["2024-03-01", "2024-06-15", "2024-01-01"]})
    auth = SQLAuthContext(connection_string="")
    wm = sql_connector_instance._get_new_watermark(sql_entity_with_watermark, auth, df)
    assert wm is not None
    assert wm.watermark_value == "2024-06-15"
    assert wm.watermark_column == "ModifiedAt"


def test_get_new_watermark_empty_df_returns_none(sql_connector_instance, sql_entity_with_watermark):
    auth = SQLAuthContext(connection_string="")
    wm = sql_connector_instance._get_new_watermark(sql_entity_with_watermark, auth, pd.DataFrame())
    assert wm is None


def test_get_new_watermark_no_watermark_column_returns_none(sql_connector_instance, sql_entity):
    df = pd.DataFrame({"id": [1]})
    auth = SQLAuthContext(connection_string="")
    wm = sql_connector_instance._get_new_watermark(sql_entity, auth, df)
    assert wm is None
