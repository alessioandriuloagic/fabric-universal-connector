from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agic_fabric_connector.base.exceptions import BronzeWriteError

if TYPE_CHECKING:
    import pandas as pd
    from pyspark.sql import SparkSession

WHEEL_VERSION = "1.0.0"

logger = logging.getLogger(__name__)


class BronzeWriter:
    def __init__(self, config: object, spark: "SparkSession") -> None:
        self.config = config
        self.spark = spark

    def write(self, df: "pd.DataFrame", entity: dict) -> int:
        """Write a pandas DataFrame to the Bronze Delta Lake table.

        Returns the number of records written.
        """
        if df is None or len(df) == 0:
            return 0

        storage = self.config.storage
        table_name = entity["logical_name"]
        schema_policy = getattr(storage, "schema_evolution_policy", "merge") or "merge"
        lakehouse_id = getattr(storage, "bronze_lake_house_id", None)

        try:
            spark_df = self.spark.createDataFrame(df)

            writer = spark_df.write.format("delta")

            if schema_policy == "merge":
                writer = writer.option("mergeSchema", "true")
            elif schema_policy == "overwrite":
                writer = writer.option("overwriteSchema", "true")

            if lakehouse_id:
                workspace_id = self._get_workspace_id()
                if workspace_id:
                    path = (
                        f"abfss://{workspace_id}@onelake.dfs.fabric.microsoft.com"
                        f"/{lakehouse_id}/Tables/{table_name}"
                    )
                    writer.mode("append").save(path)
                    logger.info("Written %d rows to %s (abfss path)", len(df), path)
                else:
                    writer.mode("append").saveAsTable(table_name)
                    logger.info("Written %d rows to table %s (default lakehouse)", len(df), table_name)
            else:
                writer.mode("append").saveAsTable(table_name)
                logger.info("Written %d rows to table %s (default lakehouse)", len(df), table_name)

            return len(df)

        except Exception as exc:
            raise BronzeWriteError(
                f"Failed to write entity '{table_name}' to Delta Lake: {exc}"
            ) from exc

    def _get_workspace_id(self) -> str:
        try:
            from notebookutils import mssparkutils  # type: ignore[import]

            return mssparkutils.runtime.context.get("workspaceId", "")
        except Exception:
            return ""
