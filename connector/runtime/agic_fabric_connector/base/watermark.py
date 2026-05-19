from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class WatermarkType(str, Enum):
    DELTA_TOKEN = "delta_token"
    TIMESTAMP   = "timestamp"
    ROWVERSION  = "rowversion"


@dataclass
class Watermark:
    watermark_type: WatermarkType
    delta_token: Optional[str]
    watermark_value: Optional[str]
    watermark_column: Optional[str]

    def is_initial_load(self) -> bool:
        return self.delta_token is None and self.watermark_value is None


class WatermarkStore:
    """Persists extraction watermarks as a Delta table in the Bronze lakehouse."""

    TABLE_NAME = "_connector_watermarks"

    def __init__(self, config: object, spark: object) -> None:
        self.config = config
        self.spark = spark
        self._initialized = False

    # ── Internal helpers ────────────────────────────────────────────────────

    def _table_path(self) -> str:
        lakehouse_id = getattr(getattr(self.config, "storage", None), "bronze_lake_house_id", None)
        if lakehouse_id:
            workspace_id = self._get_workspace_id()
            if workspace_id:
                return (
                    f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com"
                    f"/{lakehouse_id}/Tables/{self.TABLE_NAME}"
                )
        return f"Tables/{self.TABLE_NAME}"

    def _get_workspace_id(self) -> str:
        try:
            from notebookutils import mssparkutils  # type: ignore[import]

            return mssparkutils.runtime.context.get("workspaceId", "")
        except Exception:
            return ""

    def _ensure_table(self) -> None:
        if self._initialized:
            return

        path = self._table_path()
        try:
            self.spark.read.format("delta").load(path)
        except Exception:
            from pyspark.sql.types import (  # type: ignore[import]
                StringType,
                StructField,
                StructType,
                TimestampType,
            )

            schema = StructType([
                StructField("entity_name", StringType(), nullable=False),
                StructField("watermark_type", StringType(), nullable=False),
                StructField("delta_token", StringType(), nullable=True),
                StructField("watermark_value", StringType(), nullable=True),
                StructField("watermark_column", StringType(), nullable=True),
                StructField("updated_at", TimestampType(), nullable=False),
            ])
            empty_df = self.spark.createDataFrame([], schema)
            empty_df.write.format("delta").save(path)
            logger.info("Created watermarks table at %s", path)

        self._initialized = True

    # ── Public API ──────────────────────────────────────────────────────────

    def get(self, entity_name: str) -> Optional[Watermark]:
        self._ensure_table()
        path = self._table_path()
        try:
            df = (
                self.spark.read.format("delta").load(path)
                .filter(f"entity_name = '{entity_name}'")
                .orderBy("updated_at", ascending=False)
            )
            row = df.first()
            if row is None:
                return None
            return Watermark(
                watermark_type=WatermarkType(row.watermark_type),
                delta_token=row.delta_token,
                watermark_value=row.watermark_value,
                watermark_column=row.watermark_column,
            )
        except Exception as exc:
            logger.warning("Failed to read watermark for %s: %s", entity_name, exc)
            return None

    def upsert(self, entity_name: str, watermark: Watermark) -> None:
        self._ensure_table()
        path = self._table_path()
        try:
            from delta.tables import DeltaTable  # type: ignore[import]

            new_row = self.spark.createDataFrame(
                [(
                    entity_name,
                    watermark.watermark_type.value,
                    watermark.delta_token,
                    watermark.watermark_value,
                    watermark.watermark_column,
                    datetime.utcnow(),
                )],
                ["entity_name", "watermark_type", "delta_token",
                 "watermark_value", "watermark_column", "updated_at"],
            )

            DeltaTable.forPath(self.spark, path).alias("t").merge(
                new_row.alias("s"),
                "t.entity_name = s.entity_name",
            ).whenMatchedUpdateAll().whenNotMatchedInsertAll().execute()

            logger.debug("Upserted watermark for %s: delta_token=%s", entity_name, watermark.delta_token)
        except Exception as exc:
            logger.warning("Failed to upsert watermark for %s: %s — appending instead", entity_name, exc)
            new_row = self.spark.createDataFrame(
                [(
                    entity_name,
                    watermark.watermark_type.value,
                    watermark.delta_token,
                    watermark.watermark_value,
                    watermark.watermark_column,
                    datetime.utcnow(),
                )],
                ["entity_name", "watermark_type", "delta_token",
                 "watermark_value", "watermark_column", "updated_at"],
            )
            new_row.write.format("delta").mode("append").save(path)

    def reset(self, entity_name: str) -> None:
        self._ensure_table()
        path = self._table_path()
        try:
            from delta.tables import DeltaTable  # type: ignore[import]

            DeltaTable.forPath(self.spark, path).delete(
                f"entity_name = '{entity_name}'"
            )
            self._initialized = False  # force re-check on next access
            logger.info("Reset watermark for %s", entity_name)
        except Exception as exc:
            logger.warning("Failed to reset watermark for %s: %s", entity_name, exc)
