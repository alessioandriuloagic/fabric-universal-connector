"""Tests for BaseConnector error threshold logic."""
import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock, patch

from app.connectors.base_connector import BaseConnector, Watermark, EntityResult
from app.exceptions import ConnectorFatalError
from app.models.connector_item_definition import (
    SqlConnectorItemDefinition,
    SqlSourceConfiguration,
    ConnectorState,
    FeaturesConfiguration,
)


# ── Minimal concrete connector for testing ────────────────────────────────────

class _StubConnector(BaseConnector):
    BRONZE_SCHEMA = "bronze_stub"
    MODULE_TYPE = "stub"

    def __init__(self, entities, fail_indices=None, error_threshold=50.0):
        from app.models.connector_item_definition import (
            SqlConnectorItemDefinition, SqlSourceConfiguration, ConnectorState
        )
        config = SqlConnectorItemDefinition(
            state=ConnectorState.CONFIGURED,
            moduleType="sql",
            source=SqlSourceConfiguration(server="srv", database="db"),
            entities=[],
            features=FeaturesConfiguration(error_threshold_percent=error_threshold),
        )
        super().__init__(
            config=config,
            workspace_id="ws1",
            lakehouse_id="lh1",
            connector_id="conn1",
            bearer_token="tok",
        )
        self._entities = entities
        self._fail_indices = set(fail_indices or [])

    async def _authenticate(self):
        return MagicMock()

    async def _extract_entity(self, entity, auth, watermark):
        idx = self._entities.index(entity)
        if idx in self._fail_indices:
            raise RuntimeError(f"Simulated failure for entity {entity}")
        return pd.DataFrame({"id": [1, 2]})

    def _get_new_watermark(self, entity, auth, df):
        return None

    def _get_enabled_entities(self):
        return self._entities

    def _entity_name(self, entity):
        return str(entity)


# ── Helper: suppress onelake_writer and watermark I/O ─────────────────────────

def _patch_io():
    return [
        patch("app.connectors.base_connector.BaseConnector._load_watermark", AsyncMock(return_value=None)),
        patch("app.connectors.base_connector.BaseConnector._save_watermark", AsyncMock()),
        patch("app.services.onelake_writer.write_bronze", AsyncMock(return_value=2)),
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_all_entities_succeed():
    connector = _StubConnector(entities=["e1", "e2", "e3"])
    with patch("app.connectors.base_connector.BaseConnector._load_watermark", AsyncMock(return_value=None)), \
         patch("app.connectors.base_connector.BaseConnector._save_watermark", AsyncMock()), \
         patch("app.services.onelake_writer.write_bronze", AsyncMock(return_value=2)):
        result = await connector.run()

    assert result.status == "success"
    assert result.total_entities_failed == 0
    assert result.total_records_ingested == 6  # 3 entities × 2 rows


async def test_partial_failure_below_threshold():
    # 1/3 entities fail (33%) < 50% threshold → partial_success (not aborted)
    connector = _StubConnector(entities=["e1", "e2", "e3"], fail_indices=[1])
    with patch("app.connectors.base_connector.BaseConnector._load_watermark", AsyncMock(return_value=None)), \
         patch("app.connectors.base_connector.BaseConnector._save_watermark", AsyncMock()), \
         patch("app.services.onelake_writer.write_bronze", AsyncMock(return_value=2)):
        result = await connector.run()

    assert result.status == "partial_success"
    assert result.total_entities_failed == 1


async def test_error_threshold_exceeded_aborts_run():
    # 2/3 entities fail (67%) > 50% threshold → ConnectorFatalError raised
    connector = _StubConnector(entities=["e1", "e2", "e3"], fail_indices=[0, 1])
    with patch("app.connectors.base_connector.BaseConnector._load_watermark", AsyncMock(return_value=None)), \
         patch("app.connectors.base_connector.BaseConnector._save_watermark", AsyncMock()), \
         patch("app.services.onelake_writer.write_bronze", AsyncMock(return_value=2)):
        with pytest.raises(ConnectorFatalError) as exc_info:
            await connector.run()

    assert exc_info.value.error_code == "ERROR_THRESHOLD_EXCEEDED"


async def test_error_threshold_100_never_aborts():
    # threshold=100% → even all entities failing doesn't abort (threshold never exceeded)
    connector = _StubConnector(
        entities=["e1", "e2", "e3"],
        fail_indices=[0, 1, 2],
        error_threshold=100.0,
    )
    with patch("app.connectors.base_connector.BaseConnector._load_watermark", AsyncMock(return_value=None)), \
         patch("app.connectors.base_connector.BaseConnector._save_watermark", AsyncMock()), \
         patch("app.services.onelake_writer.write_bronze", AsyncMock(return_value=0)):
        result = await connector.run()

    assert result.status == "failed"
    assert result.total_entities_failed == 3


async def test_error_threshold_0_aborts_on_first_failure():
    # threshold=0% → any single failure immediately exceeds threshold
    connector = _StubConnector(
        entities=["e1", "e2", "e3"],
        fail_indices=[0],
        error_threshold=0.0,
    )
    with patch("app.connectors.base_connector.BaseConnector._load_watermark", AsyncMock(return_value=None)), \
         patch("app.connectors.base_connector.BaseConnector._save_watermark", AsyncMock()), \
         patch("app.services.onelake_writer.write_bronze", AsyncMock(return_value=2)):
        with pytest.raises(ConnectorFatalError) as exc_info:
            await connector.run()

    assert exc_info.value.error_code == "ERROR_THRESHOLD_EXCEEDED"


async def test_single_entity_all_fail_status_is_failed():
    connector = _StubConnector(entities=["e1"], fail_indices=[0])
    with patch("app.connectors.base_connector.BaseConnector._load_watermark", AsyncMock(return_value=None)), \
         patch("app.connectors.base_connector.BaseConnector._save_watermark", AsyncMock()), \
         patch("app.services.onelake_writer.write_bronze", AsyncMock(return_value=0)):
        result = await connector.run()

    assert result.status == "failed"
    assert result.total_entities_failed == 1
