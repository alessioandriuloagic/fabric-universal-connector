from __future__ import annotations
from agic_fabric_connector.base.run_result import EntityResult
from agic_fabric_connector.base.metadata_models import ConnectorRunRecord


class MetadataWriter:
    def __init__(self, config: object, spark: object) -> None:
        self.config = config
        self.spark = spark

    def start_run(self) -> ConnectorRunRecord:
        raise NotImplementedError

    def complete_run(self, run: ConnectorRunRecord, results: list[EntityResult]) -> ConnectorRunRecord:
        raise NotImplementedError

    def fail_run(self, run: ConnectorRunRecord, message: str, code: str) -> None:
        raise NotImplementedError

    def log_error(self, entity: object, error: Exception) -> None:
        raise NotImplementedError
