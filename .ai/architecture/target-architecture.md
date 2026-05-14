# PHASE 2 — TARGET ARCHITECTURE

**Project:** Fabric Universal Connector  
**Author:** Principal Architect Review  
**Date:** 2026-05-14  
**Input:** `.ai/analysis/repository-analysis.md`  
**Status:** COMPLETE — Awaiting Phase 3 instruction

---

## TABLE OF CONTENTS

1. Architecture Principles
2. System Architecture Overview
3. Hosting and Execution Model
4. Module Boundaries and Responsibilities
5. ConnectorItem — UI Architecture
6. Ingestion Architecture — Notebook Runtime Model
7. Data Flow — End to End
8. Bronze Layer Architecture
9. Security Architecture
10. Deployment Architecture
11. Repository Structure Evolution
12. Integration Points and API Surface
13. Scalability Model
14. Evolution Path (Phase 1 → Phase 3)

---

## 1. ARCHITECTURE PRINCIPLES

Every decision in this document is governed by the following non-negotiable principles, derived from `.ai/AGENTS.md` and the Phase 1 analysis:

| Principle | Constraint it imposes |
|---|---|
| **Config-driven** | All behavior controlled by JSON configuration stored in item definition. No hardcoded entity lists, schedules, or mappings. |
| **Module isolation** | CRM, BC, and SQL are independent modules. Adding or removing a module must not affect others. |
| **Bronze immutability** | Raw source data is never modified or deleted once written. All CDC operations append rows. |
| **Zero trust for secrets** | Credentials never stored in item definitions, git, or notebook code. Always resolved at runtime via Fabric Connections or Key Vault references. |
| **Fabric-native storage** | All customer data lands in the customer's own OneLake. ISV never holds customer data. |
| **SDK convention compliance** | All frontend code follows `.ai/commands/item/createItem.md` without exception. |
| **Extensibility over completeness** | Each layer must be designed to support additional modules, entities, and ingestion modes without architectural rework. |

---

## 2. SYSTEM ARCHITECTURE OVERVIEW

### Logical Architecture Diagram

```
═══════════════════════════════════════════════════════════════════════
  CUSTOMER MICROSOFT FABRIC TENANT
═══════════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────────────┐
  │  FABRIC PORTAL (Browser)                                         │
  │                                                                   │
  │  ┌─────────────────────────────────────────────────────────┐    │
  │  │  FABRIC UNIVERSAL CONNECTOR UI  (FERemote iframe)        │    │
  │  │  Hosted by ISV — connector.agic.technology               │    │
  │  │                                                           │    │
  │  │  ConnectorItem Editor                                     │    │
  │  │  ├── Onboarding Wizard (7-step configuration)            │    │
  │  │  ├── Monitoring Dashboard (run history, entity status)   │    │
  │  │  └── Detail Views (run detail, entity detail)            │    │
  │  │                                                           │    │
  │  │  HelloWorldItem Editor (reference — retained)            │    │
  │  └─────────────────────────────────────────────────────────┘    │
  │                          │ Fabric SDK (postMessage bridge)        │
  │  ════════════════════════╪════════════════════════════════════   │
  │                          │                                        │
  │  ┌──────────────────┐    │    ┌────────────────────────────┐    │
  │  │  ITEM DEFINITION  │◄───┤    │  FABRIC JOB SCHEDULER      │    │
  │  │  (payload.json)   │    │    │  • Schedule management      │    │
  │  │                   │    └───►│  • On-demand trigger        │    │
  │  │  ConnectorConfig  │         │  • Job instance tracking    │    │
  │  │  JSON (Base64)    │         └──────────────┬─────────────┘    │
  │  └──────────────────┘                         │ triggers          │
  │                                               ▼                   │
  │  ┌────────────────────────────────────────────────────────────┐  │
  │  │  INGESTION RUNTIME LAYER (Customer's Fabric Spark Compute)  │  │
  │  │                                                              │  │
  │  │  Fabric Notebook: connector_runtime_{module}.ipynb          │  │
  │  │  (deployed to customer workspace during onboarding)         │  │
  │  │                                                              │  │
  │  │  Imports: agic-fabric-connector=={version} (Python wheel)  │  │
  │  │                                                              │  │
  │  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │  │
  │  │  │ CRM Module │  │ BC Module  │  │   SQL Module        │   │  │
  │  │  │ (Dataverse)│  │ (OData v4) │  │  (JDBC/Mirror)     │   │  │
  │  │  └─────┬──────┘  └─────┬──────┘  └─────────┬──────────┘   │  │
  │  │        │               │                    │               │  │
  │  │  ┌─────▼───────────────▼────────────────────▼────────────┐ │  │
  │  │  │              BaseConnector (shared)                     │ │  │
  │  │  │  • Config loading from item definition                  │ │  │
  │  │  │  • Authentication (Fabric Connection / Key Vault)       │ │  │
  │  │  │  • Retry + backoff policy                               │ │  │
  │  │  │  • Bronze writer (Delta Lake append)                    │ │  │
  │  │  │  • Metadata writer (_connector_runs, _watermarks)       │ │  │
  │  │  │  • Schema evolution handler                             │ │  │
  │  │  └────────────────────────────────────────────────────────┘ │  │
  │  └────────────────────────────────────────────────────────────┘  │
  │                          │                                        │
  │  ┌───────────────────────▼────────────────────────────────────┐  │
  │  │  BRONZE LAKEHOUSE (OneLake / Delta Lake)                     │  │
  │  │                                                               │  │
  │  │  bronze_crm/        bronze_bc/        bronze_sql/            │  │
  │  │  ├── contact         ├── customers      ├── {table}          │  │
  │  │  ├── lead            └── _meta/         └── _meta/           │  │
  │  │  ├── msdynmkt_*                                              │  │
  │  │  └── _meta/                                                  │  │
  │  │       ├── _connector_runs                                    │  │
  │  │       ├── _entity_watermarks                                 │  │
  │  │       ├── _schema_evolution_log                              │  │
  │  │       └── _error_log                                         │  │
  │  └────────────────────────────────────────────────────────────┘  │
  │                                                                    │
  │  ┌─────────────────────────────────────────────────────────────┐  │
  │  │  SOURCE SYSTEMS (authenticated per connector config)         │  │
  │  │  • Dataverse / Dynamics 365 (OData / Change Tracking API)   │  │
  │  │  • Business Central (OData v4 API)                          │  │
  │  │  • SQL Server / Azure SQL (JDBC / Fabric Connection)        │  │
  │  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════
  ISV INFRASTRUCTURE (Agic Technology srl)
═══════════════════════════════════════════════════════════════════════

  ┌──────────────────────────────────────────────────────────────────┐
  │  Azure Static Web Apps                                            │
  │  connector.agic.technology                                        │
  │  └── Serves React frontend (FERemote iframe content)             │
  │                                                                    │
  │  Azure Artifacts Feed (or PyPI)                                   │
  │  └── agic-fabric-connector Python wheel (versioned)              │
  │                                                                    │
  │  NuGet Feed                                                        │
  │  └── ManifestPackage.nupkg (versioned per release)               │
  │                                                                    │
  │  Azure Application Insights                                        │
  │  └── Opt-in anonymous telemetry aggregation                      │
  └──────────────────────────────────────────────────────────────────┘
```

---

## 3. HOSTING AND EXECUTION MODEL

### Frontend: FERemote (Retained)

The workload maintains `HostingType="FERemote"`. This is the correct choice for Phase 1:
- No ISV backend required for UI serving
- Authentication handled entirely by Fabric SDK
- React app serves configuration, monitoring, and wizard UX
- Fabric Job Scheduler manages execution triggers
- `SwitchToRemoteHosting.ps1` preserves the migration path if a backend becomes necessary

**Decision rationale:** FERemote eliminates the ISV's need to operate a backend service for ingestion orchestration. The customer's Fabric capacity provides all compute. The ISV only operates a static web application host.

### Ingestion Execution: Fabric Notebook + Python Wheel

Data ingestion executes entirely within the customer's Fabric capacity. The execution model:

```
1. ONBOARDING (one-time per ConnectorItem activation)
   UI calls Fabric Items API → creates Notebook item in customer workspace
   Notebook content = parameterized template referencing ISV Python wheel
   Notebook ID stored in ConnectorItemDefinition

2. SCHEDULING (recurring)
   UI calls JobSchedulerClient.createItemSchedule(...)
   Schedule stored in Fabric Job Scheduler per ConnectorItem
   Fabric triggers notebook on schedule

3. EXECUTION (per run)
   Fabric Job Scheduler starts notebook run
   Notebook reads ConnectorItem definition via Fabric Items API (Fabric token)
   Notebook deserializes config JSON
   Notebook authenticates to source via Fabric Connection
   Notebook executes module-specific extraction
   Notebook writes Bronze Delta tables to OneLake
   Notebook writes run metadata (_connector_runs, _entity_watermarks)
   Run status available via JobSchedulerClient

4. MONITORING (continuous)
   UI reads _connector_runs metadata table via Fabric SQL analytics endpoint
   UI reads job instance status via JobSchedulerClient
   Dashboard displays run history, entity health, next scheduled run
```

### Why Not an ISV Backend Service (Phase 1)

| Consideration | Notebook Model | ISV Backend |
|---|---|---|
| ISV infrastructure cost | None (customer pays) | Azure Container Apps / Functions |
| Data residency | Customer tenant only | Data transits ISV infrastructure |
| Scalability | Linear with customer count | ISV must scale |
| Setup complexity | Moderate (notebook deploy) | High (backend + managed identity) |
| IP protection | Wheel package (partial) | Full (code not visible) |
| Update mechanism | Wheel version upgrade | Backend deployment |
| Phase 1 feasibility | High | Low |

The ISV backend is the correct Phase 2+ evolution for real-time ingestion (webhooks), advanced transformations, and full IP protection.

---

## 4. MODULE BOUNDARIES AND RESPONSIBILITIES

### Module Taxonomy

The platform supports three independent ingestion modules. Each module is a complete, self-contained ingestion unit:

```
┌─────────────────────────────────────────────────────────────┐
│  MODULE BOUNDARY DEFINITION                                   │
│                                                               │
│  A module owns:                                               │
│  ├── Source-specific authentication handler                   │
│  ├── Entity catalog (extractable entity definitions)         │
│  ├── Extraction engine (API client + pagination)             │
│  ├── Change tracking strategy (delta token / watermark)      │
│  ├── Schema normalization rules                              │
│  ├── Bronze schema namespace (bronze_{module})               │
│  └── Module-specific retry and throttling policies           │
│                                                               │
│  A module does NOT own:                                       │
│  ├── Bronze write mechanics (shared BaseConnector)           │
│  ├── Run tracking (shared metadata schema)                   │
│  ├── Configuration deserialization (shared)                  │
│  └── UI wizard framework (shared ConnectorItem)              │
└─────────────────────────────────────────────────────────────┘
```

### Module: CRM / Dataverse

| Property | Value |
|---|---|
| Source | Microsoft Dataverse / Dynamics 365 |
| API | Dataverse Web API (OData v4) |
| Ingestion mode | Incremental via Change Tracking (delta token) |
| Auth modes | Service Principal (Phase 1), Fabric Connection (Phase 2) |
| Bronze schema | `bronze_crm` |
| Phase 1 entities | 5 marketing entities (see §CRM MVP Plan) |
| Config key | `"moduleType": "crm"` |
| Notebook name | `connector_runtime_crm.ipynb` |

### Module: Business Central

| Property | Value |
|---|---|
| Source | Dynamics 365 Business Central |
| API | BC REST API v2.0 (OData v4) |
| Ingestion mode | Incremental via timestamp watermark (`lastModifiedDateTime`) |
| Auth modes | OAuth 2.0 client credentials |
| Bronze schema | `bronze_bc` |
| Phase 1 entities | `customers` |
| Config key | `"moduleType": "businesscentral"` |
| Notebook name | `connector_runtime_bc.ipynb` |

### Module: SQL / Azure SQL

| Property | Value |
|---|---|
| Source | SQL Server on-premises or Azure SQL |
| API | JDBC (Spark native) or Fabric Connection |
| Ingestion mode | Watermark-based incremental (configurable column) or Full extract |
| Auth modes | SQL Authentication (via Fabric Connection), Managed Identity (Azure SQL) |
| Bronze schema | `bronze_sql` |
| Phase 1 entities | Customer-selected tables (generic schema discovery) |
| Config key | `"moduleType": "sql"` |
| Notebook name | `connector_runtime_sql.ipynb` |

### Shared Runtime Components

All modules share these components via the `agic-fabric-connector` Python wheel:

```
agic_fabric_connector/
├── base/
│   ├── connector_base.py         # Abstract BaseConnector class
│   ├── bronze_writer.py          # Delta table writer with metadata columns
│   ├── metadata_writer.py        # Run + watermark tracking
│   ├── schema_evolution.py       # Schema change detection and handling
│   └── retry_policy.py           # Exponential backoff, circuit breaker
├── config/
│   ├── config_loader.py          # Item definition deserialization
│   ├── config_validator.py       # Schema validation
│   └── config_models.py          # Dataclass definitions for config types
├── auth/
│   ├── fabric_auth.py            # Fabric token acquisition (notebook context)
│   ├── connection_resolver.py    # Fabric Connection secret resolution
│   └── keyvault_resolver.py      # Azure Key Vault secret resolution
├── modules/
│   ├── crm/
│   │   ├── crm_connector.py      # CRM module implementation
│   │   ├── dataverse_client.py   # Dataverse API client
│   │   ├── change_tracking.py    # Delta token management
│   │   └── entity_catalog.py     # CRM entity definitions
│   ├── businesscentral/
│   │   ├── bc_connector.py       # BC module implementation
│   │   ├── bc_client.py          # BC REST API client
│   │   └── entity_catalog.py     # BC entity definitions
│   └── sql/
│       ├── sql_connector.py      # SQL module implementation
│       ├── schema_discovery.py   # JDBC schema introspection
│       └── watermark_manager.py  # Watermark tracking
└── utils/
    ├── logger.py                  # Structured logging to Bronze
    ├── telemetry.py               # Anonymous opt-in telemetry
    └── fabric_api.py              # Fabric REST API helpers
```

---

## 5. CONNECTORITEM — UI ARCHITECTURE

### Item Identity

| Property | Value |
|---|---|
| Item type name | `Connector` |
| Manifest name | `Connector` (matches `ITEM_NAMES=HelloWorld,Connector`) |
| Editor path | `/ConnectorItem-editor` |
| Route | `/ConnectorItem-editor/:itemObjectId` |
| TypeName (XML) | `{{WORKLOAD_NAME}}.Connector` |

### View Registry

All views registered as a static array in `ConnectorItemEditor.tsx`:

```
┌─────────────────────────────────────────────────────────────────┐
│  VIEW NAME          │ TYPE          │ TRIGGER                     │
├─────────────────────┼───────────────┼─────────────────────────────┤
│  empty              │ standard      │ item.definition.state = null │
│  wizard-module      │ standard      │ user clicks "Configure"      │
│  wizard-source      │ standard      │ module selected              │
│  wizard-auth        │ standard      │ source configured            │
│  wizard-entities    │ standard      │ auth configured              │
│  wizard-storage     │ standard      │ entities selected            │
│  wizard-schedule    │ standard      │ storage selected             │
│  wizard-review      │ standard      │ schedule configured          │
│  dashboard          │ standard      │ item.definition.state = configured │
│  run-detail         │ isDetailView  │ user clicks a run row        │
│  entity-detail      │ isDetailView  │ user clicks an entity        │
└─────────────────────┴───────────────┴─────────────────────────────┘
```

### View-to-Component Mapping

```typescript
// ConnectorItemEditor.tsx — view registration
const views: RegisteredView[] = [
  // ─── Initial state ─────────────────────────────────────
  { name: VIEWS.EMPTY,           component: <ConnectorItemEmptyView ... /> },

  // ─── Wizard steps ──────────────────────────────────────
  { name: VIEWS.WIZARD_MODULE,   component: <WizardModuleStep ... /> },
  { name: VIEWS.WIZARD_SOURCE,   component: <WizardSourceStep ... /> },
  { name: VIEWS.WIZARD_AUTH,     component: <WizardAuthStep ... /> },
  { name: VIEWS.WIZARD_ENTITIES, component: <WizardEntityStep ... /> },
  { name: VIEWS.WIZARD_STORAGE,  component: <WizardStorageStep ... /> },
  { name: VIEWS.WIZARD_SCHEDULE, component: <WizardScheduleStep ... /> },
  { name: VIEWS.WIZARD_REVIEW,   component: <WizardReviewStep ... /> },

  // ─── Post-configuration main view ──────────────────────
  { name: VIEWS.DASHBOARD,       component: <ConnectorDashboard ... /> },

  // ─── Detail drill-down views (auto back navigation) ────
  { name: VIEWS.RUN_DETAIL,      component: <RunDetailView ... />,    isDetailView: true },
  { name: VIEWS.ENTITY_DETAIL,   component: <EntityDetailView ... />, isDetailView: true },
];
```

### Ribbon Architecture per View

The ribbon adapts dynamically to the current view via the function pattern `ribbon={(context) => ...}`:

```
empty view:          [Configure →]
wizard-* views:      [← Back] [Next →] [Cancel]
wizard-review:       [← Back] [Activate ▶]
dashboard view:      [Run Now ▶] [Pause ⏸] [Reconfigure ✏] [Settings ⚙]
run-detail:          (inherited via isDetailView back-nav) [Cancel Run ✕]
entity-detail:       (inherited via isDetailView back-nav) [Reset Watermark ↺]
```

### Wizard State Machine

The wizard state is held in `ConnectorItemEditor` state, not in item definition, until the final "Activate" step saves the complete configuration:

```
State: wizardData = {
  step: WizardStep (enum: MODULE | SOURCE | AUTH | ENTITIES | STORAGE | SCHEDULE | REVIEW)
  moduleType: "crm" | "businesscentral" | "sql" | null
  source: Partial<SourceConfiguration>
  auth: Partial<AuthConfiguration>
  selectedEntities: string[]
  storage: Partial<StorageConfiguration>
  schedule: Partial<SchedulingConfiguration>
  validationErrors: Record<string, string>
  isActivating: boolean
}
```

**Why not save between steps:** Partial configurations are invalid. Saving an incomplete wizard state to the item definition would produce a broken connector record. The configuration is only persisted on Activate (wizard-review step → successful Activate).

**Step validation:** Each step validates its own slice of `wizardData` before enabling the "Next" button. Validation is synchronous (form rules) + async (format validation only — not live API calls in Phase 1).

### Connectivity Test Decision (Phase 1)

Phase 1 does **not** include real-time connectivity testing during the wizard. The wizard accepts and validates the configuration format only. The first notebook run validates connectivity. Connectivity errors are surfaced via the dashboard's error log view.

**Rationale:** Real-time testing would require:
- A Spark Livy session (slow startup, requires Fabric capacity)
- OR an ISV backend service (not in Phase 1 scope)

Phase 2 adds a "Test Connection" button that triggers a lightweight Spark job via `SparkLivyClient`.

### Dashboard Architecture (ItemEditorDefaultView)

```typescript
<ItemEditorDefaultView
  left={{
    title: "Entities",
    width: 260,
    collapsible: true,
    content: <EntityStatusList
      entities={entityStatuses}
      onEntityClick={(name) => setCurrentView(VIEWS.ENTITY_DETAIL, { entityName: name })}
    />
  }}
  center={{
    content: <DashboardContent
      lastRun={lastRun}
      nextRun={nextRun}
      runHistory={runHistory}
      onRunClick={(runId) => setCurrentView(VIEWS.RUN_DETAIL, { runId })}
    />
  }}
/>
```

Dashboard data sources:
- **Run history:** `_connector_runs` Delta table, read via Fabric SQL analytics endpoint (JDBC from Spark) OR via item definition runtime metadata (lightweight alternative for Phase 1)
- **Job status:** `JobSchedulerClient.listItemJobInstances()`
- **Entity watermarks:** `_entity_watermarks` Delta table

### Notification System

The `ConnectorItemEditor` registers contextual notifications:

```typescript
const notifications: RegisteredNotification[] = [
  {
    name: 'activation-success',
    showInViews: [VIEWS.DASHBOARD],
    component: activationSuccess ? (
      <MessageBar intent="success">Connector activated. First run starting...</MessageBar>
    ) : null
  },
  {
    name: 'last-run-failed',
    showInViews: [VIEWS.DASHBOARD],
    component: lastRunFailed ? (
      <MessageBar intent="error">
        Last run failed. <Link onClick={() => setCurrentView(VIEWS.RUN_DETAIL, { runId: lastRunId })}>
          View details
        </Link>
      </MessageBar>
    ) : null
  },
  {
    name: 'wizard-validation-error',
    showInViews: WIZARD_VIEWS,
    component: validationError ? (
      <MessageBar intent="warning">{validationError}</MessageBar>
    ) : null
  }
];
```

---

## 6. INGESTION ARCHITECTURE — NOTEBOOK RUNTIME MODEL

### Notebook Template Structure

Each module has a dedicated notebook template deployed to the customer workspace:

```python
# connector_runtime_crm.ipynb — template structure
# This notebook is parameterized by Fabric Job Scheduler

# Cell 1: Package installation
%pip install agic-fabric-connector=={WHEEL_VERSION}

# Cell 2: Configuration loading
from agic_fabric_connector.config.config_loader import ConfigLoader
from agic_fabric_connector.modules.crm import CRMConnector

config = ConfigLoader.from_item_definition(
    item_id="{CONNECTOR_ITEM_ID}",    # injected at deploy time
    workspace_id="{WORKSPACE_ID}"     # injected at deploy time
)

# Cell 3: Execution
connector = CRMConnector(config, spark)
connector.run()
```

**Key design decisions:**
- `CONNECTOR_ITEM_ID` and `WORKSPACE_ID` are baked into the notebook at deploy time (not passed as parameters), because Fabric Job Scheduler does not natively support notebook parameters in the current SDK version
- The notebook template version is pinned to the wheel version — they are always released together
- No secrets appear in the notebook; all auth is resolved at runtime via `ConfigLoader`

### BaseConnector Execution Contract

```python
class BaseConnector(ABC):
    """All module connectors must implement this interface"""

    def run(self) -> RunResult:
        """Main entry point — orchestrates the full ingestion run"""
        run_id = self._start_run()
        try:
            entities = self._get_enabled_entities()
            results = self._process_entities(entities)
            self._complete_run(run_id, results)
            return RunResult(success=True, run_id=run_id, results=results)
        except Exception as e:
            self._fail_run(run_id, str(e))
            raise

    @abstractmethod
    def _authenticate(self) -> AuthContext:
        """Authenticate to source system"""

    @abstractmethod
    def _extract_entity(self, entity: EntityConfig, auth: AuthContext,
                        watermark: Watermark) -> pd.DataFrame:
        """Extract records for one entity, respecting watermark"""

    @abstractmethod
    def _get_new_watermark(self, entity: EntityConfig,
                           auth: AuthContext) -> Watermark:
        """Get the new watermark to store after successful extraction"""

    def _write_bronze(self, df: pd.DataFrame, entity: EntityConfig):
        """Write to Bronze — provided by base class, not overridable"""
        BronzeWriter(self.config, self.spark).write(df, entity)

    def _handle_schema_evolution(self, df: pd.DataFrame,
                                  entity: EntityConfig) -> pd.DataFrame:
        """Schema evolution per policy in config — provided by base class"""
        return SchemaEvolutionHandler(self.config.features.schemaEvolutionHandling)\
               .handle(df, entity, self.spark)
```

### Entity Processing Flow (Per Run)

```
FOR EACH enabled entity in config.entities:
  1. Load watermark from _entity_watermarks (delta token or timestamp)
  2. Authenticate to source (per module auth handler)
  3. Extract records since watermark (module-specific extraction)
     ├── If watermark is null → full extract (initial load)
     └── If watermark exists → incremental extract
  4. Apply schema evolution handling (merge / strict / overwrite)
  5. Add metadata columns (_run_id, _ingestion_utc, _operation, etc.)
  6. Write to Bronze Delta table (append mode, partitioned by _ingestion_date)
  7. Update _entity_watermarks with new token/timestamp
  8. Write entity result to _connector_runs.entity_results[]
  
  ON ERROR:
  ├── Log error to _error_log
  ├── If errorThresholdPercent exceeded → abort run
  └── Else → continue to next entity (partial run)
```

### Retry and Throttling Policy

Implemented in `retry_policy.py` as a shared concern:

```python
@dataclass
class RetryPolicy:
    max_attempts: int = 3
    initial_backoff_seconds: float = 5.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 300.0
    respect_retry_after_header: bool = True  # Critical for Dataverse throttling

    def execute(self, fn: Callable, *args) -> Any:
        for attempt in range(self.max_attempts):
            try:
                return fn(*args)
            except ThrottlingError as e:
                wait = e.retry_after or self._calculate_backoff(attempt)
                time.sleep(wait)
            except RecoverableError:
                time.sleep(self._calculate_backoff(attempt))
```

### Notebook Deployment During Onboarding

The wizard's "Activate" step (final step) performs:

```typescript
// In ConnectorItemEditor — Activate handler
async function handleActivate(): Promise<void> {
  setIsActivating(true);

  // Step 1: Save item definition (configuration)
  await saveItemDefinition<ConnectorItemDefinition>(workloadClient, item.id, finalConfig);

  // Step 2: Create Bronze Lakehouse (if not exists)
  const lakeHouseId = await ensureBronzeLakehouse(workloadClient, wizardData.storage);

  // Step 3: Deploy notebook template to customer workspace
  const notebookId = await deployNotebook(
    workloadClient,
    item.workspaceId,
    wizardData.moduleType,
    item.id
  );

  // Step 4: Update item definition with notebook ID and lakehouse ID
  await saveItemDefinition(workloadClient, item.id, {
    ...finalConfig,
    runtime: {
      notebookItemId: notebookId,
      bronzeLakeHouseId: lakeHouseId,
      deployedAt: new Date().toISOString(),
      wheelVersion: CURRENT_WHEEL_VERSION
    },
    state: "configured"
  });

  // Step 5: Register Fabric Job Schedule
  const scheduleClient = new JobSchedulerClient(workloadClient);
  await scheduleClient.createItemSchedule(
    item.workspaceId, item.id, "ConnectorIngestionJob",
    buildScheduleRequest(wizardData.schedule)
  );

  // Step 6: Trigger first run immediately
  await scheduleClient.runOnDemandItemJob(
    item.workspaceId, item.id, "ConnectorIngestionJob"
  );

  // Step 7: Navigate to dashboard
  setCurrentView(VIEWS.DASHBOARD);
  setActivationSuccess(true);
}
```

---

## 7. DATA FLOW — END TO END

### Flow A: First-Time Configuration (Onboarding)

```
Customer creates new ConnectorItem in Fabric workspace
       ↓
ConnectorItemEditor loads → state = "empty"
EmptyView displayed: "Configure your connector"
       ↓
Customer clicks "Configure" → wizard-module view
Customer completes 7 wizard steps
Customer clicks "Activate"
       ↓
handleActivate() executes:
  ├── [1] Save configuration to item definition (payload.json → Base64 JSON)
  ├── [2] Create Bronze Lakehouse via Fabric Items API (if not exists)
  ├── [3] Deploy notebook template via Fabric Items API
  ├── [4] Update item definition with runtime IDs
  ├── [5] Create job schedule via JobSchedulerClient
  └── [6] Trigger first on-demand job run
       ↓
Dashboard view displayed
First run starts (async, in Fabric Spark compute)
       ↓
Notebook executes:
  ├── Load config from item definition
  ├── For each entity: extract → bronze write → update watermark
  └── Write run summary to _connector_runs
       ↓
Dashboard polls job status via JobSchedulerClient
Run history appears in dashboard
```

### Flow B: Scheduled Incremental Run

```
Fabric Job Scheduler fires on cron schedule
       ↓
Triggers notebook: connector_runtime_{module}.ipynb
       ↓
Notebook: ConfigLoader.from_item_definition(item_id, workspace_id)
       ↓
For each enabled entity:
  ├── Read watermark from _entity_watermarks
  ├── Call source API with delta token / watermark filter
  ├── Receive incremental records (inserts, updates, deletes)
  ├── Add Bronze metadata columns
  ├── Append to Delta table (mode=append, mergeSchema=true if merge policy)
  └── Update _entity_watermarks with new watermark
       ↓
Write run summary to _connector_runs
       ↓
Dashboard reflects updated run history on next refresh
```

### Flow C: User-Triggered Manual Run

```
User clicks "Run Now" in dashboard ribbon
       ↓
ConnectorItemEditor calls:
  JobSchedulerClient.runOnDemandItemJob(workspaceId, itemId, "ConnectorIngestionJob")
       ↓
Returns jobInstanceId
       ↓
UI polls JobSchedulerClient.getItemJobInstance(workspaceId, itemId, jobInstanceId)
       ↓
Status spinner shown in dashboard
On completion: run history table refreshes
```

### Flow D: Monitoring (Dashboard Refresh)

```
Dashboard component mounts / refresh interval fires
       ↓
Parallel data fetches:
  ├── JobSchedulerClient.getAllItemJobInstances() → job run statuses
  ├── JobSchedulerClient.getAllItemSchedules() → next scheduled run time
  └── [Phase 2] Fabric SQL query on _connector_runs → detailed run history
       ↓
Dashboard state updated:
  ├── Summary cards: last run status, next run time, total records today
  ├── Run history DataGrid: rows from job instances
  └── Entity status list: per-entity last success time (from watermarks)
```

---

## 8. BRONZE LAYER ARCHITECTURE

### Storage Target

```
Customer Fabric Workspace
└── Lakehouse: "FabricUniversalConnector-Bronze"
    ├── Schemas (Delta table groups):
    │   ├── bronze_crm      ← CRM module tables
    │   ├── bronze_bc       ← BC module tables
    │   └── bronze_sql      ← SQL module tables
    └── Files/ (not used for data — reserved for future use)
```

One Bronze Lakehouse is created per customer workspace. All modules share the same Lakehouse but use separate schema namespaces. This simplifies governance, access control, and semantic model building.

### Standard Table Schema

Every Bronze table carries these ISV metadata columns, appended by the runtime:

```
── SOURCE COLUMNS ──────────────────────────────────────────
{all columns from source API, raw names, raw types}

── ISV METADATA COLUMNS (prefix: _) ───────────────────────
_run_id               STRING        UUID of the run that wrote this row
_ingestion_utc        TIMESTAMP     When this row was written to Bronze
_ingestion_date       DATE          Partition key (derived from _ingestion_utc)
_source_modified_utc  TIMESTAMP     When source record was last modified
_operation            STRING        "insert" | "update" | "delete"
_is_current           BOOLEAN       True = latest version of this record
_entity_name          STRING        Source entity logical name
_source_row_version   STRING        ETag / rowversion / @odata.etag from source
_schema_version       STRING        Source schema version at time of ingestion
_connector_id         STRING        Fabric item ID of the ConnectorItem
_module_type          STRING        "crm" | "businesscentral" | "sql"
_wheel_version        STRING        ISV wheel package version
```

### Partitioning

All Bronze tables are partitioned by `_ingestion_date`:

```python
df.write.format("delta") \
    .partitionBy("_ingestion_date") \
    .option("mergeSchema", "true") \
    .mode("append") \
    .saveAsTable(f"{schema}.{table_name}")
```

Partition by ingestion date (not source modification date) because:
1. Source modification dates may be null, historical, or unreliable
2. Operational queries ("what was ingested today/this week") are the dominant access pattern
3. Retention policies can be applied cleanly by ingestion date

### Metadata Tables (per schema)

```
bronze_{module}._meta._connector_runs
  run_id, connector_id, module_type, run_start_utc, run_end_utc,
  status, entities_processed, records_ingested, records_failed,
  error_message, triggered_by, wheel_version, config_schema_version

bronze_{module}._meta._entity_watermarks
  connector_id, entity_name, delta_token, watermark_value,
  watermark_column, last_run_id, last_success_utc, records_at_source_est
  PRIMARY KEY (connector_id, entity_name)

bronze_{module}._meta._schema_evolution_log
  connector_id, entity_name, change_type, column_name,
  old_type, new_type, detected_utc, handled_by

bronze_{module}._meta._error_log
  run_id, entity_name, error_type, error_code, error_message,
  record_id, occurred_utc, retry_attempt
```

### Schema Evolution Policy

The behavior when source schema changes is controlled by `config.features.schemaEvolutionHandling`:

| Policy | Behavior | When to use |
|---|---|---|
| `merge` (default) | Add new columns; keep orphaned columns as null | Production — safe, non-breaking |
| `strict` | Fail the run on any schema change | Highly regulated environments |
| `overwrite` | Re-create table with new schema | Development only — destroys history |

---

## 9. SECURITY ARCHITECTURE

### Credential Flow

```
NO CREDENTIALS IN:
  ✗ Item definition (payload.json)
  ✗ Notebook code
  ✗ Git repository
  ✗ ISV infrastructure

CREDENTIALS STORED IN (customer-controlled):
  ✓ Fabric Connections (preferred) — managed by Fabric platform
  ✓ Azure Key Vault (alternative) — customer's own vault

CREDENTIAL REFERENCE IN item definition:
  "authentication": {
    "mode": "fabric_connection",
    "fabricConnectionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
  }
  OR
  "authentication": {
    "mode": "keyvault_reference",
    "keyVaultUri": "https://vault.vault.azure.net/",
    "secretName": "crm-client-secret"
  }
```

### Authentication Layers

| Layer | Authenticates | Mechanism |
|---|---|---|
| User → Fabric | Human user to Fabric portal | Entra ID SSO (Fabric handles) |
| Fabric SDK → Fabric API | Frontend to Fabric platform | SDK `acquireFrontendAccessToken()` |
| Notebook → Fabric API | Notebook to read item definition | Fabric built-in notebook token |
| Notebook → OneLake | Notebook to write Bronze | Fabric built-in OneLake access |
| Notebook → Source | Notebook to CRM/BC/SQL | Fabric Connection or Key Vault ref |
| ISV → Fabric | Build pipeline (CI/CD) | Service Principal (ISV-owned) |

### Scope Requirements (ConnectorItem)

The ConnectorItem frontend requires these OAuth scopes:

```typescript
// Scopes for wizard operations
const WIZARD_SCOPES = combineScopes(
  SCOPES.ITEM,          // Create Lakehouse, create Notebook items
  SCOPES.WORKSPACE,     // Read workspace context
  SCOPES.JOB_SCHEDULER, // Create/manage schedules, trigger runs
  SCOPES.CONNECTION     // Read available Fabric Connections for auth step
);
```

### Least Privilege for Source Service Principals

| Module | Required SP permissions |
|---|---|
| CRM/Dataverse | System.ReadAll on Dataverse; App User role; Change Tracking enabled on entities |
| Business Central | API.ReadWrite:Financials in BC; specific entity permissions |
| SQL (Azure SQL) | `db_datareader` on specific schemas only; no DDL rights |

---

## 10. DEPLOYMENT ARCHITECTURE

### ISV Deployment Targets

```
Release Pipeline produces:
├── ManifestPackage.nupkg  → Fabric Marketplace (via ISV NuGet feed)
├── React app build        → Azure Static Web Apps (FRONTEND_URL)
└── Python wheel           → Azure Artifacts / PyPI (WHEEL_VERSION)
```

### Customer Deployment Flow

```
1. Customer finds workload in Fabric Marketplace / AppSource
2. Customer installs workload → Fabric downloads ManifestPackage.nupkg
3. Workload registered in customer's Fabric tenant
4. Customer opens workspace → "New item" → Connector
5. ConnectorItemEditor loads (React app from ISV Azure Static Web Apps)
6. Customer completes 7-step wizard
7. On Activate:
   a. Item definition saved in Fabric (customer's Fabric storage)
   b. Bronze Lakehouse created (customer's Fabric compute)
   c. Notebook template deployed (customer's Fabric workspace)
      └── Notebook imports wheel from ISV Artifacts feed
   d. Job schedule registered (customer's Fabric)
   e. First run triggered (customer's Fabric Spark)
8. All subsequent runs execute entirely in customer's Fabric capacity
```

### Version Management

| Artifact | Versioning | Update mechanism |
|---|---|---|
| NuGet manifest | `{year}.{month}` (2026.05) | Fabric notifies tenant of update |
| React frontend | Same as NuGet | Served from ISV host; URL unchanged |
| Python wheel | SemVer `{major}.{minor}.{patch}` | Notebook `%pip install` on each run |
| Notebook template | Tied to wheel major version | Re-deployed on major version bump |

**Wheel update strategy:** The notebook installs `agic-fabric-connector=={WHEEL_VERSION}` where `WHEEL_VERSION` is pinned at notebook deploy time. When the ISV releases a new patch version, the notebook template is re-deployed via a workload update. This gives the ISV full control over which version runs in each customer's Fabric environment.

---

## 11. REPOSITORY STRUCTURE EVOLUTION

### Current → Target Repository Structure

```
fabric-universal-connector/               ← root (no change)
│
├── .ai/                                  ← extended (Phase 1 added analysis/)
│   ├── analysis/repository-analysis.md  ← NEW (Phase 1 output)
│   ├── architecture/target-architecture.md ← NEW (Phase 2 output)
│   ├── contracts/                        ← NEW (Phase 3 output)
│   ├── scaffold/                         ← NEW (Phase 4 output)
│   ├── mvp/                              ← NEW (Phase 5 output)
│   ├── commands/                         ← unchanged
│   └── context/                          ← unchanged
│
├── Workload/                             ← primary changes here
│   ├── app/
│   │   ├── items/
│   │   │   ├── HelloWorldItem/           ← unchanged
│   │   │   └── ConnectorItem/            ← ★ NEW — primary deliverable
│   │   │       ├── ConnectorItemDefinition.ts
│   │   │       ├── ConnectorItemEditor.tsx
│   │   │       ├── ConnectorItemEmptyView.tsx
│   │   │       ├── ConnectorItem.scss
│   │   │       ├── dashboard/
│   │   │       │   ├── ConnectorDashboard.tsx
│   │   │       │   ├── RunHistoryTable.tsx
│   │   │       │   ├── EntityStatusList.tsx
│   │   │       │   ├── RunDetailView.tsx
│   │   │       │   └── EntityDetailView.tsx
│   │   │       ├── ribbon/
│   │   │       │   ├── ConnectorItemRibbon.tsx
│   │   │       │   └── ribbonActionFactory.ts
│   │   │       └── wizard/
│   │   │           ├── WizardModuleStep.tsx
│   │   │           ├── WizardSourceStep.tsx
│   │   │           ├── WizardAuthStep.tsx
│   │   │           ├── WizardEntityStep.tsx
│   │   │           ├── WizardStorageStep.tsx
│   │   │           ├── WizardScheduleStep.tsx
│   │   │           ├── WizardReviewStep.tsx
│   │   │           ├── wizardState.ts
│   │   │           └── wizardValidation.ts
│   │   │
│   │   ├── controller/                   ← add 2 controllers
│   │   │   ├── ... (existing unchanged)
│   │   │   ├── NotebookDeploymentController.ts  ← NEW
│   │   │   └── LakehouseController.ts           ← NEW
│   │   │
│   │   └── assets/
│   │       ├── items/ConnectorItem/      ← NEW (icons, empty state SVG)
│   │       └── locales/en-US/translation.json  ← extended
│   │
│   └── Manifest/
│       ├── items/
│       │   ├── HelloWorldItem/           ← unchanged
│       │   └── ConnectorItem/            ← ★ NEW
│       │       ├── ConnectorItem.json
│       │       └── ConnectorItem.xml
│       ├── Product.json                  ← extended (Connector entry)
│       └── assets/locales/en-US/translations.json  ← extended
│
├── connector/                            ← ★ NEW — ingestion runtime
│   ├── runtime/
│   │   ├── agic_fabric_connector/        ← Python package
│   │   │   ├── __init__.py
│   │   │   ├── base/
│   │   │   ├── config/
│   │   │   ├── auth/
│   │   │   ├── modules/
│   │   │   │   ├── crm/
│   │   │   │   ├── businesscentral/
│   │   │   │   └── sql/
│   │   │   └── utils/
│   │   ├── notebooks/
│   │   │   ├── connector_runtime_crm.ipynb
│   │   │   ├── connector_runtime_bc.ipynb
│   │   │   └── connector_runtime_sql.ipynb
│   │   ├── pyproject.toml
│   │   └── setup.cfg
│   └── tests/
│       ├── unit/
│       └── integration/
│
├── .github/
│   └── workflows/                        ← ★ NEW — CI/CD
│       ├── ci.yml                        # PR validation
│       ├── cd-staging.yml                # deploy to test
│       └── cd-production.yml             # deploy to production
│
├── backend/                              ← remain empty (Phase 3 placeholder)
├── backend_2/                            ← remain empty (Phase 3 placeholder)
├── scripts/                              ← unchanged
├── tools/                                ← unchanged
└── docs/                                 ← extended with architecture docs
```

---

## 12. INTEGRATION POINTS AND API SURFACE

### Fabric APIs Used (ConnectorItem)

| Operation | Client | Scope | Phase |
|---|---|---|---|
| Get item metadata | `workloadClient.itemCrud.getItem()` | ITEM_READ | 1 |
| Read/write item definition | `workloadClient.itemCrud.getItemDefinition/updateItemDefinition()` | ITEM | 1 |
| Create Lakehouse | `ItemClient.createItem({type: "Lakehouse"})` | ITEM | 1 |
| Deploy Notebook | `ItemClient.createItem({type: "Notebook"})` | ITEM | 1 |
| Create job schedule | `JobSchedulerClient.createItemSchedule()` | JOB_SCHEDULER | 1 |
| Trigger on-demand run | `JobSchedulerClient.runOnDemandItemJob()` | JOB_SCHEDULER | 1 |
| Monitor job instances | `JobSchedulerClient.listItemJobInstances()` | JOB_SCHEDULER_READ | 1 |
| List available connections | `ConnectionClient.listConnections()` | CONNECTION_READ | 1 |
| DataHub picker (Lakehouse) | `DataHubController.callDatahubWizardOpen()` | — | 1 |
| Read Bronze metadata | Fabric SQL analytics endpoint (JDBC) | CODE_ACCESS_FABRIC | 2 |
| Spark Livy (test connection) | `SparkLivyClient` | SPARK_LIVY | 2 |

### Source System APIs Used (Runtime — Python Wheel)

| Module | API | Auth | Protocol |
|---|---|---|---|
| CRM | Dataverse Web API + Change Tracking | MSAL client credentials | OData v4 / REST |
| BC | BC REST API v2.0 | MSAL client credentials | OData v4 |
| SQL | JDBC (Spark native) | Fabric Connection or SQL auth | JDBC |

---

## 13. SCALABILITY MODEL

### Tenant Scalability

The architecture is linearly scalable with customer count:

```
N customers × 1 workload installation = N isolated execution contexts
Each customer has:
  - Their own Fabric capacity (no ISV compute)
  - Their own OneLake storage
  - Their own job schedules
  - Their own item definitions
  
ISV fixed costs:
  - Azure Static Web Apps (scales automatically, minimal cost)
  - NuGet feed hosting (static, no scaling needed)
  - Python wheel hosting (static, CDN-served)
```

### Data Volume Scalability (per customer)

```
Initial load: Customer adjusts Spark cluster size
  ├── Starter (F2): handles ~1M records per entity
  ├── Standard (F4): handles ~10M records per entity
  └── Large (F8+): handles 100M+ records per entity

Incremental load: Driven by change volume
  ├── Low-change source: 1,000 changes/interval → tiny Spark job
  └── High-change source: 1M changes/interval → scale cluster

Delta table optimization:
  ├── OPTIMIZE + ZORDER run weekly (scheduled separate notebook)
  └── VACUUM run weekly (configurable retention period)
```

---

## 14. EVOLUTION PATH (Phase 1 → Phase 3)

### Phase 1 — Current Architecture (FERemote + Notebooks)

- FERemote frontend
- Notebook-based ingestion (customer compute)
- Fabric Job Scheduler for scheduling
- Item definition as configuration store
- In-memory dashboard data (job instance API)

### Phase 2 — ISV Backend Service

Triggered when any of these become necessary:
- Real-time webhook ingestion (Dataverse plugins → ISV endpoint → Bronze)
- IP protection for ingestion logic (move from notebooks to backend)
- Advanced transformations requiring stateful service
- Multi-tenant management console (ISV-side)

Migration path: Execute `scripts/Setup/SwitchToRemoteHosting.ps1`

```
Workload changes:
  WorkloadManifest.xml: HostingType → "Remote"
  Add BackendServiceEndpoint to manifest
  Add ISV backend deployment to CI/CD
  Implement Fabric workload backend API contract
  
Architecture additions:
  Azure Container Apps (serverless) → ISV backend service
  Fabric → ISV backend via SubjectAndApp token
  ISV backend → source systems (no browser involved)
```

### Phase 3 — Full Enterprise Platform

- Open Mirroring support (alternative CRM ingestion mode)
- Semantic scaffolding views (Silver layer generation)
- TMDL starter model generation
- Multi-workspace deployment (central config, multiple targets)
- Fabric Event Streams for near-real-time (SQL CDC, Dataverse webhooks)
- ISV management portal (cross-tenant monitoring)

---

## ARCHITECTURE DECISIONS LOG

| ID | Decision | Rationale | Alternative considered |
|---|---|---|---|
| AD-01 | FERemote hosting retained for Phase 1 | No ISV compute cost; full migration path available | Remote hosting — rejected (too complex for Phase 1) |
| AD-02 | Notebook-first ingestion | Customer compute; data stays in tenant | ISV backend — rejected (Phase 2) |
| AD-03 | Python wheel for ingestion logic | Partial IP protection; version control; reusable | Plain notebook code — rejected (no IP protection, hard to update) |
| AD-04 | One Bronze Lakehouse per workspace | Simplified governance; shared access control | Per-module Lakehouse — rejected (management overhead) |
| AD-05 | Item definition as config store | Zero external dependencies; Fabric-native | External database — rejected (unnecessary ISV infrastructure) |
| AD-06 | Deferred connectivity validation | Avoids Spark startup latency in wizard | Real-time test — deferred to Phase 2 |
| AD-07 | Fabric Connections for source credentials | Customer-controlled; Fabric manages secrets | Key Vault (alternative) or inline secrets (rejected — security) |
| AD-08 | Partition Bronze tables by _ingestion_date | Operational query patterns; clean retention | Source modification date — rejected (unreliable, nullable) |
| AD-09 | `mergeSchema=true` as default evolution | Non-breaking; preserves all history | Strict — available as config option |
| AD-10 | 7-step wizard (unsaved until Activate) | Prevent partial/invalid saved configs | Save-per-step — rejected (invalid intermediate states) |

---

**PHASE 2 COMPLETE**

Output: `.ai/architecture/target-architecture.md`

Awaiting Phase 3 instruction: Domain Contracts
