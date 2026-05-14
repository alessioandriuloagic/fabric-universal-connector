from __future__ import annotations
from agic_fabric_connector.config.config_models import ConnectorItemDefinition
from agic_fabric_connector.base.exceptions import ConfigLoadError


class ConfigLoader:
    @staticmethod
    def from_item_definition(
        item_id: str,
        workspace_id: str,
        spark: object,
    ) -> ConnectorItemDefinition:
        # Phase 1 placeholder — actual implementation in Phase 5
        # Will: 1) call mssparkutils.credentials.getToken() for Fabric API
        #        2) GET /v1/workspaces/{workspaceId}/items/{itemId}/definition
        #        3) decode base64 payload, parse JSON into ConnectorItemDefinition
        raise ConfigLoadError(
            f"ConfigLoader.from_item_definition not yet implemented — item_id={item_id}"
        )
