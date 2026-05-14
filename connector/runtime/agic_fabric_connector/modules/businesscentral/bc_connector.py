from __future__ import annotations
from agic_fabric_connector.base.connector_base import BaseConnector
from agic_fabric_connector.base.run_result import RunResult


class BusinessCentralConnector(BaseConnector):
    def authenticate(self) -> None:
        raise NotImplementedError("BusinessCentralConnector.authenticate — Phase 5 implementation target")

    def extract_entity(self, entity: object) -> object:
        raise NotImplementedError("BusinessCentralConnector.extract_entity — Phase 5 implementation target")

    def run(self) -> RunResult:
        raise NotImplementedError("BusinessCentralConnector.run — Phase 5 implementation target")
