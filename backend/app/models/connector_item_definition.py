"""
Pydantic v2 mirror of ConnectorItemDefinition.ts.
Single source of truth for deserialising the Fabric item definition payload.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional, List, Literal, Union, Annotated
from pydantic import BaseModel, Field, field_validator


# ── Enums ──────────────────────────────────────────────────────────────────────

class ConnectorState(str, Enum):
    EMPTY = "empty"
    CONFIGURED = "configured"
    ERROR = "error"
    PAUSED = "paused"


class SchemaEvolutionPolicy(str, Enum):
    MERGE = "merge"
    STRICT = "strict"
    OVERWRITE = "overwrite"


class ExtractionMode(str, Enum):
    INCREMENTAL = "incremental"
    FULL = "full"


# ── Authentication models ──────────────────────────────────────────────────────

class FabricConnectionAuth(BaseModel):
    mode: Literal["fabric_connection"]
    fabric_connection_id: str = Field(alias="fabricConnectionId")

    model_config = {"populate_by_name": True}


class KeyVaultReferenceAuth(BaseModel):
    mode: Literal["keyvault_reference"]
    key_vault_uri: str = Field(alias="keyVaultUri")
    client_id_secret_name: Optional[str] = Field(default=None, alias="clientIdSecretName")
    client_secret_name: str = Field(alias="clientSecretName")
    tenant_id_secret_name: Optional[str] = Field(default=None, alias="tenantIdSecretName")

    model_config = {"populate_by_name": True}


class ServicePrincipalAuth(BaseModel):
    mode: Literal["service_principal"]
    tenant_id: str = Field(alias="tenantId")
    client_id: str = Field(alias="clientId")
    secret_ref: Annotated[
        Union[FabricConnectionAuth, KeyVaultReferenceAuth],
        Field(discriminator="mode")
    ] = Field(alias="secretRef")

    model_config = {"populate_by_name": True}


AuthConfiguration = Annotated[
    Union[FabricConnectionAuth, KeyVaultReferenceAuth, ServicePrincipalAuth],
    Field(discriminator="mode")
]


# ── Source configurations ──────────────────────────────────────────────────────

class CrmSourceConfiguration(BaseModel):
    environment_url: str = Field(alias="environmentUrl")
    tenant_id: str = Field(alias="tenantId")
    api_version: str = Field(default="v9.2", alias="apiVersion")
    enable_change_tracking: bool = Field(default=True, alias="enableChangeTracking")
    page_size: int = Field(default=5000, alias="pageSize")

    model_config = {"populate_by_name": True}


class BusinessCentralSourceConfiguration(BaseModel):
    tenant_id: str = Field(alias="tenantId")
    environment: str
    company_id: Optional[str] = Field(default=None, alias="companyId")
    api_version: str = Field(default="2.0", alias="apiVersion")
    page_size: int = Field(default=500, alias="pageSize")

    model_config = {"populate_by_name": True}


class SqlSourceConfiguration(BaseModel):
    server: str
    database: str
    port: int = 1433
    driver: str = "sqlserver"
    encrypt: bool = True
    trust_server_certificate: bool = Field(default=False, alias="trustServerCertificate")

    model_config = {"populate_by_name": True}


# ── Entity configurations ──────────────────────────────────────────────────────

class CrmEntityConfiguration(BaseModel):
    logical_name: str = Field(alias="logicalName")
    display_name: str = Field(alias="displayName")
    enabled: bool = True
    extraction_mode: ExtractionMode = Field(
        default=ExtractionMode.INCREMENTAL, alias="extractionMode"
    )
    select_columns: Optional[List[str]] = Field(default=None, alias="selectColumns")
    expand_relationships: Optional[List[str]] = Field(
        default=None, alias="expandRelationships"
    )
    filter_expression: Optional[str] = Field(default=None, alias="filterExpression")
    batch_size: int = Field(default=5000, alias="batchSize")

    model_config = {"populate_by_name": True}


class BusinessCentralEntityConfiguration(BaseModel):
    api_endpoint: str = Field(alias="apiEndpoint")
    display_name: str = Field(alias="displayName")
    enabled: bool = True
    extraction_mode: ExtractionMode = Field(
        default=ExtractionMode.INCREMENTAL, alias="extractionMode"
    )
    watermark_column: str = Field(default="lastModifiedDateTime", alias="watermarkColumn")
    select_columns: Optional[List[str]] = Field(default=None, alias="selectColumns")
    filter_expression: Optional[str] = Field(default=None, alias="filterExpression")
    batch_size: int = Field(default=500, alias="batchSize")

    model_config = {"populate_by_name": True}


class SqlEntityConfiguration(BaseModel):
    schema_name: str = Field(alias="schema")
    table_name: str = Field(alias="tableName")
    display_name: str = Field(alias="displayName")
    enabled: bool = True
    extraction_mode: ExtractionMode = Field(
        default=ExtractionMode.INCREMENTAL, alias="extractionMode"
    )
    watermark_column: Optional[str] = Field(default=None, alias="watermarkColumn")
    watermark_column_type: Optional[str] = Field(
        default=None, alias="watermarkColumnType"
    )
    select_columns: Optional[List[str]] = Field(default=None, alias="selectColumns")
    where_clause: Optional[str] = Field(default=None, alias="whereClause")
    primary_keys: Optional[List[str]] = Field(default=None, alias="primaryKeys")
    fetch_size: int = Field(default=10000, alias="fetchSize")

    model_config = {"populate_by_name": True}


# ── Storage / Schedule / Features / Runtime ────────────────────────────────────

class StorageConfiguration(BaseModel):
    bronze_lake_house_id: Optional[str] = Field(default=None, alias="bronzeLakeHouseId")
    bronze_lake_house_name: str = Field(alias="bronzeLakeHouseName")
    schema_evolution_policy: SchemaEvolutionPolicy = Field(
        default=SchemaEvolutionPolicy.MERGE, alias="schemaEvolutionPolicy"
    )
    retention_days: Optional[int] = Field(default=None, alias="retentionDays")
    use_existing_lakehouse: bool = Field(default=False, alias="useExistingLakehouse")

    model_config = {"populate_by_name": True}


class SchedulingConfiguration(BaseModel):
    schedule_type: str = Field(default="cron", alias="scheduleType")
    cron_expression: Optional[str] = Field(default=None, alias="cronExpression")
    interval_minutes: Optional[int] = Field(default=None, alias="intervalMinutes")
    timezone: str = Field(default="UTC")
    enabled: bool = True
    start_date: Optional[str] = Field(default=None, alias="startDate")

    model_config = {"populate_by_name": True}


class FeaturesConfiguration(BaseModel):
    schema_evolution_handling: SchemaEvolutionPolicy = Field(
        default=SchemaEvolutionPolicy.MERGE, alias="schemaEvolutionHandling"
    )
    error_threshold_percent: float = Field(default=50.0, alias="errorThresholdPercent")
    enable_partial_run: bool = Field(default=True, alias="enablePartialRun")
    enable_telemetry: bool = Field(default=False, alias="enableTelemetry")
    max_records_per_entity_per_run: Optional[int] = Field(
        default=None, alias="maxRecordsPerEntityPerRun"
    )

    model_config = {"populate_by_name": True}


class RuntimeConfiguration(BaseModel):
    notebook_item_id: Optional[str] = Field(default=None, alias="notebookItemId")
    bronze_lake_house_id: Optional[str] = Field(default=None, alias="bronzeLakeHouseId")
    deployed_at: Optional[str] = Field(default=None, alias="deployedAt")
    wheel_version: Optional[str] = Field(default=None, alias="wheelVersion")
    config_schema_version: str = Field(default="1.0.0", alias="configSchemaVersion")
    job_schedule_id: Optional[str] = Field(default=None, alias="jobScheduleId")

    model_config = {"populate_by_name": True}


# ── Top-level discriminated definitions ────────────────────────────────────────

class ConnectorItemDefinitionBase(BaseModel):
    schema_version: str = Field(default="1.0.0", alias="schemaVersion")
    state: ConnectorState
    authentication: Optional[AuthConfiguration] = None
    storage: Optional[StorageConfiguration] = None
    scheduling: Optional[SchedulingConfiguration] = None
    features: FeaturesConfiguration = Field(default_factory=FeaturesConfiguration)
    runtime: Optional[RuntimeConfiguration] = None

    model_config = {"populate_by_name": True}

    @field_validator("state")
    @classmethod
    def must_be_configured(cls, v: ConnectorState) -> ConnectorState:
        return v


class CrmConnectorItemDefinition(ConnectorItemDefinitionBase):
    module_type: Literal["crm"] = Field(alias="moduleType")
    source: CrmSourceConfiguration
    entities: List[CrmEntityConfiguration]

    model_config = {"populate_by_name": True}

    def enabled_entities(self) -> List[CrmEntityConfiguration]:
        return [e for e in self.entities if e.enabled]


class BusinessCentralConnectorItemDefinition(ConnectorItemDefinitionBase):
    module_type: Literal["businesscentral"] = Field(alias="moduleType")
    source: BusinessCentralSourceConfiguration
    entities: List[BusinessCentralEntityConfiguration]

    model_config = {"populate_by_name": True}

    def enabled_entities(self) -> List[BusinessCentralEntityConfiguration]:
        return [e for e in self.entities if e.enabled]


class SqlConnectorItemDefinition(ConnectorItemDefinitionBase):
    module_type: Literal["sql"] = Field(alias="moduleType")
    source: SqlSourceConfiguration
    entities: List[SqlEntityConfiguration]

    model_config = {"populate_by_name": True}

    def enabled_entities(self) -> List[SqlEntityConfiguration]:
        return [e for e in self.entities if e.enabled]


ConnectorItemDefinition = Annotated[
    Union[
        CrmConnectorItemDefinition,
        BusinessCentralConnectorItemDefinition,
        SqlConnectorItemDefinition,
    ],
    Field(discriminator="module_type"),
]
