from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from agic_fabric_connector.base.run_result import RunResult, EntityResult

if TYPE_CHECKING:
    from pyspark.sql import SparkSession


class BaseConnector(ABC):
    def __init__(self, config: object, spark: "SparkSession") -> None:
        self.config = config
        self.spark = spark

    def run(self) -> RunResult:
        raise NotImplementedError("BaseConnector.run — implemented by subclasses")

    @abstractmethod
    def extract_entity(self, entity: object) -> "object":
        raise NotImplementedError

    @abstractmethod
    def authenticate(self) -> None:
        raise NotImplementedError
