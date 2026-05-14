from __future__ import annotations
from agic_fabric_connector.base.connector_base import BaseConnector
from agic_fabric_connector.base.run_result import RunResult


class CRMConnector(BaseConnector):
    def authenticate(self) -> None:
        raise NotImplementedError("CRMConnector.authenticate — Phase 5 implementation target")

    def extract_entity(self, entity: object) -> object:
        raise NotImplementedError("CRMConnector.extract_entity — Phase 5 implementation target")

    def run(self) -> RunResult:
        raise NotImplementedError("CRMConnector.run — Phase 5 implementation target")
