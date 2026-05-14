from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass
class CrmSourceConfiguration:
    environment_url: str
    tenant_id: str
    api_version: Optional[str] = None
    enable_change_tracking: bool = True
    page_size: int = 5000


@dataclass
class BusinessCentralSourceConfiguration:
    tenant_id: str
    environment: str
    company_id: Optional[str] = None
    api_version: Optional[str] = None
    page_size: int = 1000


@dataclass
class SqlSourceConfiguration:
    server: str
    database: str
    port: int = 1433
    driver: str = "sqlserver"
    encrypt: bool = True
    trust_server_certificate: bool = False


@dataclass
class FabricConnectionAuth:
    mode: str = "fabric_connection"
    fabric_connection_id: str = ""


@dataclass
class KeyVaultReferenceAuth:
    mode: str = "keyvault_reference"
    key_vault_uri: str = ""
    client_id_secret_name: Optional[str] = None
    client_secret_name: str = ""
    tenant_id_secret_name: Optional[str] = None


@dataclass
class ServicePrincipalAuth:
    mode: str = "service_principal"
    tenant_id: str = ""
    client_id: str = ""
    secret_ref: Union[FabricConnectionAuth, KeyVaultReferenceAuth] = field(
        default_factory=FabricConnectionAuth
    )


AuthConfiguration = Union[FabricConnectionAuth, KeyVaultReferenceAuth, ServicePrincipalAuth]


@dataclass
class StorageConfiguration:
    bronze_lake_house_name: str
    bronze_lake_house_id: Optional[str] = None
    schema_evolution_policy: str = "merge"
    retention_days: Optional[int] = None
    use_existing_lakehouse: bool = False


@dataclass
class SchedulingConfiguration:
    schedule_type: str = "cron"
    cron_expression: Optional[str] = "0 2 * * *"
    interval_minutes: Optional[int] = None
    timezone: str = "UTC"
    enabled: bool = True
    start_date: Optional[str] = None


@dataclass
class RuntimeConfiguration:
    notebook_item_id: Optional[str] = None
    bronze_lake_house_id: Optional[str] = None
    deployed_at: Optional[str] = None
    wheel_version: Optional[str] = None
    config_schema_version: Optional[str] = None
    job_schedule_id: Optional[str] = None


@dataclass
class ConnectorItemDefinition:
    schema_version: str
    state: str
    module_type: str
    source: Union[CrmSourceConfiguration, BusinessCentralSourceConfiguration, SqlSourceConfiguration]
    entities: list
    authentication: Optional[AuthConfiguration] = None
    storage: Optional[StorageConfiguration] = None
    scheduling: Optional[SchedulingConfiguration] = None
    runtime: Optional[RuntimeConfiguration] = None
