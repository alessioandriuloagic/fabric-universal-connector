from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd
    from pyspark.sql import SparkSession

WHEEL_VERSION = "1.0.0"


class BronzeWriter:
    def __init__(self, config: object, spark: "SparkSession") -> None:
        self.config = config
        self.spark = spark

    def write(self, df: "pd.DataFrame", entity: object) -> int:
        raise NotImplementedError("BronzeWriter.write — Phase 5 implementation target")
