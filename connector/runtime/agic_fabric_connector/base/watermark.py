from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from enum import Enum


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
    def __init__(self, config: object, spark: object) -> None:
        self.config = config
        self.spark = spark

    def get(self, entity_name: str) -> Optional[Watermark]:
        raise NotImplementedError

    def upsert(self, entity: object, watermark: Watermark) -> None:
        raise NotImplementedError

    def reset(self, entity_name: str) -> None:
        raise NotImplementedError
