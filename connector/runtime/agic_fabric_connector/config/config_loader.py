from __future__ import annotations

import base64
import json
import logging
from typing import Optional

import requests

from agic_fabric_connector.base.exceptions import ConfigLoadError
from agic_fabric_connector.config.config_models import (
    BusinessCentralSourceConfiguration,
    ConnectorItemDefinition,
    CrmSourceConfiguration,
    FabricConnectionAuth,
    KeyVaultReferenceAuth,
    RuntimeConfiguration,
    SchedulingConfiguration,
    ServicePrincipalAuth,
    StorageConfiguration,
)

logger = logging.getLogger(__name__)

_FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"


class ConfigLoader:
    @staticmethod
    def from_item_definition(
        item_id: str,
        workspace_id: str,
        spark: object,
    ) -> ConnectorItemDefinition:
        """Load a ConnectorItemDefinition from the Fabric item definition API.

        Requires mssparkutils to obtain a Fabric bearer token.
        """
        token = ConfigLoader._get_fabric_token()

        url = (
            f"{_FABRIC_API_BASE}/workspaces/{workspace_id}"
            f"/items/{item_id}/definition"
        )
        resp = requests.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        if resp.status_code != 200:
            raise ConfigLoadError(
                f"Failed to fetch item definition (HTTP {resp.status_code}): {resp.text[:500]}"
            )

        parts = resp.json().get("definition", {}).get("parts", [])
        payload_json: Optional[dict] = None

        for part in parts:
            if part.get("path") == "payload.json":
                try:
                    raw = base64.b64decode(part["payload"]).decode("utf-8")
                    payload_json = json.loads(raw)
                except Exception as exc:
                    raise ConfigLoadError(
                        f"Failed to decode payload.json: {exc}"
                    ) from exc
                break

        if payload_json is None:
            raise ConfigLoadError(
                "payload.json part not found in item definition"
            )

        logger.info("Loaded item definition for item=%s workspace=%s", item_id, workspace_id)
        return ConfigLoader._parse(payload_json)

    @staticmethod
    def _get_fabric_token() -> str:
        try:
            from notebookutils import mssparkutils  # type: ignore[import]

            return mssparkutils.credentials.getToken("https://api.fabric.microsoft.com")
        except Exception as exc:
            raise ConfigLoadError(
                f"Failed to obtain Fabric access token via mssparkutils: {exc}"
            ) from exc

    # ── Parsing helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _parse(payload: dict) -> ConnectorItemDefinition:
        module_type = payload.get("moduleType", "")
        source_raw = payload.get("source", {})

        if module_type == "crm":
            source = CrmSourceConfiguration(
                environment_url=source_raw.get("environmentUrl", ""),
                tenant_id=source_raw.get("tenantId", ""),
                api_version=source_raw.get("apiVersion"),
                enable_change_tracking=source_raw.get("enableChangeTracking", True),
                page_size=source_raw.get("pageSize", 5000),
            )
        elif module_type == "businesscentral":
            source = BusinessCentralSourceConfiguration(
                tenant_id=source_raw.get("tenantId", ""),
                environment=source_raw.get("environment", ""),
                company_id=source_raw.get("companyId"),
                api_version=source_raw.get("apiVersion"),
                page_size=source_raw.get("pageSize", 1000),
            )
        else:
            raise ConfigLoadError(f"Unsupported module type: '{module_type}'")

        storage = None
        if storage_raw := payload.get("storage"):
            storage = StorageConfiguration(
                bronze_lake_house_name=storage_raw.get("bronzeLakeHouseName", ""),
                bronze_lake_house_id=storage_raw.get("bronzeLakeHouseId"),
                schema_evolution_policy=storage_raw.get("schemaEvolutionPolicy", "merge"),
                retention_days=storage_raw.get("retentionDays"),
                use_existing_lakehouse=storage_raw.get("useExistingLakehouse", False),
            )

        scheduling = None
        if sched_raw := payload.get("scheduling"):
            scheduling = SchedulingConfiguration(
                schedule_type=sched_raw.get("scheduleType", "cron"),
                cron_expression=sched_raw.get("cronExpression"),
                interval_minutes=sched_raw.get("intervalMinutes"),
                timezone=sched_raw.get("timezone", "UTC"),
                enabled=sched_raw.get("enabled", True),
                start_date=sched_raw.get("startDate"),
            )

        runtime = None
        if runtime_raw := payload.get("runtime"):
            runtime = RuntimeConfiguration(
                notebook_item_id=runtime_raw.get("notebookItemId"),
                bronze_lake_house_id=runtime_raw.get("bronzeLakeHouseId"),
                deployed_at=runtime_raw.get("deployedAt"),
                wheel_version=runtime_raw.get("wheelVersion"),
                config_schema_version=runtime_raw.get("configSchemaVersion"),
                job_schedule_id=runtime_raw.get("jobScheduleId"),
            )

        # entities: saved as CrmEntityConfiguration objects (dicts with camelCase keys)
        # CRMConnector._resolve_entities() maps them against the Python catalog.
        entities = payload.get("entities", [])

        return ConnectorItemDefinition(
            schema_version=payload.get("schemaVersion", "1.0.0"),
            state=payload.get("state", "configured"),
            module_type=module_type,
            source=source,
            entities=entities,
            authentication=ConfigLoader._parse_auth(payload.get("authentication")),
            storage=storage,
            scheduling=scheduling,
            runtime=runtime,
        )

    @staticmethod
    def _parse_auth(auth_raw: Optional[dict]):
        if not auth_raw:
            return None

        mode = auth_raw.get("mode", "")

        if mode == "service_principal":
            secret_ref_raw = auth_raw.get("secretRef", {})
            secret_ref_mode = secret_ref_raw.get("mode", "")

            if secret_ref_mode == "fabric_connection":
                secret_ref = FabricConnectionAuth(
                    mode="fabric_connection",
                    fabric_connection_id=secret_ref_raw.get("fabricConnectionId", ""),
                )
            else:
                secret_ref = KeyVaultReferenceAuth(
                    mode="keyvault_reference",
                    key_vault_uri=secret_ref_raw.get("keyVaultUri", ""),
                    client_id_secret_name=secret_ref_raw.get("clientIdSecretName"),
                    client_secret_name=secret_ref_raw.get("clientSecretName", ""),
                    tenant_id_secret_name=secret_ref_raw.get("tenantIdSecretName"),
                )

            return ServicePrincipalAuth(
                mode="service_principal",
                tenant_id=auth_raw.get("tenantId", ""),
                client_id=auth_raw.get("clientId", ""),
                secret_ref=secret_ref,
            )

        if mode == "fabric_connection":
            return FabricConnectionAuth(
                mode="fabric_connection",
                fabric_connection_id=auth_raw.get("fabricConnectionId", ""),
            )

        if mode == "keyvault_reference":
            return KeyVaultReferenceAuth(
                mode="keyvault_reference",
                key_vault_uri=auth_raw.get("keyVaultUri", ""),
                client_id_secret_name=auth_raw.get("clientIdSecretName"),
                client_secret_name=auth_raw.get("clientSecretName", ""),
                tenant_id_secret_name=auth_raw.get("tenantIdSecretName"),
            )

        logger.warning("Unknown auth mode '%s' — returning None", mode)
        return None
