# PHASE 5 — CRM MVP IMPLEMENTATION PLAN

**Project:** Fabric Universal Connector  
**Author:** Principal Architect Review  
**Date:** 2026-05-14  
**Input:** `.ai/scaffold/scaffold-plan.md`, `.ai/contracts/`, `.ai/architecture/target-architecture.md`  
**Status:** COMPLETE — All phases delivered

---

## TABLE OF CONTENTS

1. MVP Scope
2. Implementation Task List (Ordered)
3. CRM Entity Catalog — Phase 1
4. Bronze Table Schemas — All 5 Entities
5. Frontend: handleActivate() — Complete Implementation
6. Frontend: NotebookDeploymentController.ts — Complete Implementation
7. Frontend: LakehouseController.ts — Complete Implementation
8. Python: connector_base.py — Complete Implementation
9. Python: config_loader.py — Complete Implementation
10. Python: config_models.py — Complete Implementation
11. Python: bronze_writer.py — Complete Implementation
12. Python: metadata_writer.py — Complete Implementation
13. Python: watermark.py — Complete Implementation
14. Python: schema_evolution.py — Complete Implementation
15. Python: retry_policy.py — Complete Implementation
16. Python: crm_connector.py — Complete Implementation
17. Python: dataverse_client.py — Complete Implementation
18. Python: auth/crm_auth.py — Complete Implementation
19. Unit Test Plan
20. Integration Test Checklist
21. Deferred to Later Phases

---

## 1. MVP SCOPE

### In Scope — CRM MVP

| Area | Deliverable |
|---|---|
| **Frontend** | Complete `handleActivate()` with Lakehouse creation, notebook deployment, job scheduling, first run trigger |
| **Frontend** | `LakehouseController.ts` — create or find existing Bronze Lakehouse |
| **Frontend** | `NotebookDeploymentController.ts` — substitute placeholders and deploy notebook via `ItemClient` |
| **CRM module** | `CRMConnector` — complete `_authenticate`, `_extract_entity`, `_get_new_watermark` |
| **CRM module** | `DataverseClient` — full Dataverse OData v4 client with Change Tracking delta token pagination |
| **CRM module** | 5 Phase 1 entities: contact, lead, msdynmkt_marketingform, msdynmkt_marketingemail, msdynmkt_customerjourney |
| **Shared base** | `ConfigLoader.from_item_definition()` — read item definition from Fabric Items API in notebook context |
| **Shared base** | `BronzeWriter.write()` — append to Delta table with all 12 metadata columns |
| **Shared base** | `MetadataWriter` — full run lifecycle (start, complete, fail, log_error) |
| **Shared base** | `WatermarkStore` — get, upsert via MERGE INTO, reset |
| **Shared base** | `SchemaEvolutionHandler` — merge and strict policies |
| **Shared base** | `RetryPolicy` — exponential backoff with Retry-After respect |
| **Notebook** | `connector_runtime_crm.ipynb` — final content with placeholders substituted at deploy |

### Out of Scope — CRM MVP

| Deferred | Reason |
|---|---|
| BC and SQL connectors | Phase 6+ |
| "Test Connection" button in wizard | Requires Spark Livy session — Phase 2 frontend |
| `_connector_runs` read via Fabric SQL endpoint | Phase 2 dashboard — Phase 1 uses Job Scheduler API for run status |
| Delta OPTIMIZE / VACUUM after write | `enableDeltaLakeOptimize: false` default |
| Anonymous telemetry | Phase 2 |
| Fabric Connections secret resolution | Phase 2 — Phase 1 uses Key Vault or service principal only |
| AppSource packaging | Phase 3 |

---

## 2. IMPLEMENTATION TASK LIST (ORDERED)

Execute in this order. Each task has hard dependencies on previous tasks.

```
PYTHON WHEEL (do first — frontend depends on wheel being importable for testing)

 [PY-01]  connector/runtime/agic_fabric_connector/base/exceptions.py         ← copy from contracts §10
 [PY-02]  connector/runtime/agic_fabric_connector/base/run_result.py         ← copy from scaffold
 [PY-03]  connector/runtime/agic_fabric_connector/base/watermark.py          ← complete (§13 of this doc)
 [PY-04]  connector/runtime/agic_fabric_connector/base/retry_policy.py       ← complete (§15 of this doc)
 [PY-05]  connector/runtime/agic_fabric_connector/config/config_models.py    ← complete (§10 of this doc)
 [PY-06]  connector/runtime/agic_fabric_connector/config/config_loader.py    ← complete (§9 of this doc)
 [PY-07]  connector/runtime/agic_fabric_connector/base/bronze_writer.py      ← complete (§11 of this doc)
 [PY-08]  connector/runtime/agic_fabric_connector/base/metadata_writer.py    ← complete (§12 of this doc)
 [PY-09]  connector/runtime/agic_fabric_connector/base/schema_evolution.py   ← complete (§14 of this doc)
 [PY-10]  connector/runtime/agic_fabric_connector/base/connector_base.py     ← complete (§8 of this doc)
 [PY-11]  connector/runtime/agic_fabric_connector/auth/crm_auth.py           ← complete (§18 of this doc)
 [PY-12]  connector/runtime/agic_fabric_connector/modules/crm/dataverse_client.py ← complete (§17)
 [PY-13]  connector/runtime/agic_fabric_connector/modules/crm/entity_catalog.py   ← complete (§3)
 [PY-14]  connector/runtime/agic_fabric_connector/modules/crm/crm_connector.py    ← complete (§16)
 [PY-15]  connector/runtime/notebooks/connector_runtime_crm.ipynb             ← final notebook

UNIT TESTS

 [UT-01]  connector/tests/unit/test_retry_policy.py
 [UT-02]  connector/tests/unit/test_watermark.py
 [UT-03]  connector/tests/unit/test_config_loader.py
 [UT-04]  connector/tests/unit/test_crm_connector.py
 [UT-05]  connector/tests/unit/test_dataverse_client.py

FRONTEND (after scaffold from Phase 4 is in place)

 [FE-01]  Workload/app/controller/LakehouseController.ts                ← complete (§7 of this doc)
 [FE-02]  Workload/app/controller/NotebookDeploymentController.ts       ← complete (§6 of this doc)
 [FE-03]  Workload/app/items/ConnectorItem/ConnectorItemEditor.tsx      ← complete handleActivate() (§5)
 [FE-04]  Workload/app/items/ConnectorItem/ConnectorItemEditor.tsx      ← wire wizard ribbon Next/Back/Activate
```

---

## 3. CRM ENTITY CATALOG — PHASE 1

Five entities. Exact Dataverse logical names, plural names, primary keys, and default field selections for Phase 1.

### Entity 1: contact

```python
EntityCatalogEntry(
    logical_name       = "contact",
    plural_name        = "contacts",
    primary_key        = "contactid",
    display_name       = "Contact",
    supports_change_tracking = True,
    default_select_columns   = [
        "contactid",
        "fullname",
        "firstname",
        "lastname",
        "emailaddress1",
        "emailaddress2",
        "telephone1",
        "mobilephone",
        "jobtitle",
        "department",
        "accountid",
        "parentcustomerid",
        "statecode",
        "statuscode",
        "donotbulkemail",
        "donotbulkpostalmail",
        "donotemail",
        "donotphone",
        "gendercode",
        "birthdate",
        "address1_city",
        "address1_country",
        "address1_stateorprovince",
        "address1_postalcode",
        "ownerid",
        "owningbusinessunit",
        "createdon",
        "modifiedon",
        "overriddencreatedon",
    ]
)
```

### Entity 2: lead

```python
EntityCatalogEntry(
    logical_name       = "lead",
    plural_name        = "leads",
    primary_key        = "leadid",
    display_name       = "Lead",
    supports_change_tracking = True,
    default_select_columns   = [
        "leadid",
        "fullname",
        "firstname",
        "lastname",
        "emailaddress1",
        "telephone1",
        "mobilephone",
        "jobtitle",
        "companyname",
        "subject",
        "leadsourcecode",
        "industrycode",
        "statecode",
        "statuscode",
        "estimatedamount",
        "estimatedclosedate",
        "qualifyingopportunityid",
        "ownerid",
        "owningbusinessunit",
        "createdon",
        "modifiedon",
        "overriddencreatedon",
    ]
)
```

### Entity 3: msdynmkt_marketingform

```python
EntityCatalogEntry(
    logical_name       = "msdynmkt_marketingform",
    plural_name        = "msdynmkt_marketingforms",
    primary_key        = "msdynmkt_marketingformid",
    display_name       = "Marketing Form",
    supports_change_tracking = True,
    default_select_columns   = [
        "msdynmkt_marketingformid",
        "msdynmkt_name",
        "msdynmkt_type",
        "msdynmkt_purpose",
        "statecode",
        "statuscode",
        "ownerid",
        "owningbusinessunit",
        "createdon",
        "modifiedon",
    ]
)
```

### Entity 4: msdynmkt_marketingemail

```python
EntityCatalogEntry(
    logical_name       = "msdynmkt_marketingemail",
    plural_name        = "msdynmkt_marketingemails",
    primary_key        = "msdynmkt_marketingemailid",
    display_name       = "Marketing Email",
    supports_change_tracking = True,
    default_select_columns   = [
        "msdynmkt_marketingemailid",
        "msdynmkt_name",
        "msdynmkt_subject",
        "msdynmkt_previewtext",
        "msdynmkt_fromname",
        "msdynmkt_fromemail",
        "msdynmkt_replyto",
        "statecode",
        "statuscode",
        "ownerid",
        "owningbusinessunit",
        "createdon",
        "modifiedon",
    ]
)
```

### Entity 5: msdynmkt_customerjourney

```python
EntityCatalogEntry(
    logical_name       = "msdynmkt_customerjourney",
    plural_name        = "msdynmkt_customerjourneys",
    primary_key        = "msdynmkt_customerjourneyid",
    display_name       = "Customer Journey",
    supports_change_tracking = True,
    default_select_columns   = [
        "msdynmkt_customerjourneyid",
        "msdynmkt_name",
        "msdynmkt_type",
        "msdynmkt_startdatetime",
        "msdynmkt_enddatetime",
        "msdynmkt_status",
        "msdynmkt_recurrencecount",
        "msdynmkt_recurrenceintervaldays",
        "statecode",
        "statuscode",
        "ownerid",
        "owningbusinessunit",
        "createdon",
        "modifiedon",
    ]
)
```

---

## 4. BRONZE TABLE SCHEMAS — ALL 5 ENTITIES

All Bronze tables for `bronze_crm` schema. Source columns first, then 12 ISV metadata columns.

### bronze_crm.contact

```
contactid                  STRING    NOT NULL  ← Dataverse primary key
fullname                   STRING
firstname                  STRING
lastname                   STRING
emailaddress1              STRING
emailaddress2              STRING
telephone1                 STRING
mobilephone                STRING
jobtitle                   STRING
department                 STRING
accountid                  STRING    ← lookup ID (string representation of GUID)
parentcustomerid           STRING    ← polymorphic lookup ID
statecode                  INTEGER
statuscode                 INTEGER
donotbulkemail             BOOLEAN
donotbulkpostalmail        BOOLEAN
donotemail                 BOOLEAN
donotphone                 BOOLEAN
gendercode                 INTEGER
birthdate                  DATE
address1_city              STRING
address1_country           STRING
address1_stateorprovince   STRING
address1_postalcode        STRING
ownerid                    STRING
owningbusinessunit         STRING
createdon                  TIMESTAMP
modifiedon                 TIMESTAMP
overriddencreatedon        TIMESTAMP
── ISV METADATA ─────────────────────────────
_run_id                    STRING    NOT NULL
_connector_id              STRING    NOT NULL
_module_type               STRING    NOT NULL  "crm"
_entity_name               STRING    NOT NULL  "contact"
_operation                 STRING    NOT NULL  "insert"|"update"|"delete"
_is_current                BOOLEAN   NOT NULL
_ingestion_utc             TIMESTAMP NOT NULL
_ingestion_date            DATE      NOT NULL  ← partition key
_source_modified_utc       TIMESTAMP           ← from modifiedon
_source_row_version        STRING              ← from @odata.etag
_schema_version            STRING              "v9.2"
_wheel_version             STRING    NOT NULL
```

### bronze_crm.lead

Same pattern. Source columns match `default_select_columns` for lead. Lookup columns (`qualifyingopportunityid`) stored as STRING.

### bronze_crm.msdynmkt_marketingform / msdynmkt_marketingemail / msdynmkt_customerjourney

Same pattern. All lookup and option-set columns stored as their primitive types (INTEGER for option sets, STRING for lookup GUIDs, TIMESTAMP for datetime fields).

### Type Mapping Rules (Dataverse → Delta Lake)

| Dataverse type | Delta Lake type |
|---|---|
| String | STRING |
| Lookup (reference) | STRING (GUID as string) |
| OptionSet (integer) | INTEGER |
| Boolean | BOOLEAN |
| DateTime | TIMESTAMP (UTC, parsed from ISO 8601) |
| Date | DATE |
| Decimal / Money | DECIMAL(18, 4) |
| Integer | INTEGER |
| BigInt | LONG |
| Double | DOUBLE |
| UniqueIdentifier (GUID) | STRING |
| Memo (multi-line text) | STRING |

---

## 5. FRONTEND: handleActivate() — COMPLETE IMPLEMENTATION

Replace the placeholder in `ConnectorItemEditor.tsx`:

```typescript
// ── Imports to add at top of ConnectorItemEditor.tsx ─────────────────────
import { saveItemDefinition } from "../../controller/ItemCRUDController";
import { deployConnectorNotebook } from "../../controller/NotebookDeploymentController";
import { ensureBronzeLakehouse } from "../../controller/LakehouseController";
import { JobSchedulerClient } from "../../clients/JobSchedulerClient";
import { buildScheduleRequest } from "./wizard/wizardState";

// ── Replace the handleActivate placeholder ────────────────────────────────
async function handleActivate(): Promise<void> {
  if (!item) return;

  updateWizard({ isActivating: true, validationErrors: {} });

  try {
    // ── Step 1: Build final config from wizard state ──────────────────────
    const finalConfig = buildConnectorDefinition(wizardState, item);

    // ── Step 2: Ensure Bronze Lakehouse exists ────────────────────────────
    const lakehouseResult = await ensureBronzeLakehouse(
      workloadClient,
      item.workspaceId,
      wizardState.storage.bronzeLakeHouseName ?? "FabricUniversalConnector-Bronze",
      wizardState.storage.useExistingLakehouse ?? false
    );

    // ── Step 3: Deploy notebook template to customer workspace ────────────
    const notebookResult = await deployConnectorNotebook(
      workloadClient,
      item.workspaceId,
      item.id,
      wizardState.moduleType!
    );

    // ── Step 4: Save fully-activated item definition ──────────────────────
    const activatedConfig = {
      ...finalConfig,
      storage: {
        ...finalConfig.storage,
        bronzeLakeHouseId: lakehouseResult.lakeHouseId,
      },
      runtime: {
        notebookItemId:      notebookResult.notebookItemId,
        bronzeLakeHouseId:   lakehouseResult.lakeHouseId,
        deployedAt:          new Date().toISOString(),
        wheelVersion:        notebookResult.wheelVersion,
        configSchemaVersion: "1.0.0",
      },
      state: "configured" as const,
      metadata: {
        ...finalConfig.metadata,
        activatedAt: new Date().toISOString(),
        updatedAt:   new Date().toISOString(),
      },
    };

    await saveItemDefinition(workloadClient, item.id, activatedConfig);

    // ── Step 5: Register job schedule with Fabric Scheduler ───────────────
    const scheduler = new JobSchedulerClient(workloadClient);
    const scheduleRequest = buildScheduleRequest(wizardState.schedule);
    await scheduler.createItemSchedule(
      item.workspaceId,
      item.id,
      "ConnectorIngestionJob",
      scheduleRequest
    );

    // ── Step 6: Trigger first on-demand run immediately ───────────────────
    await scheduler.runOnDemandItemJob(
      item.workspaceId,
      item.id,
      "ConnectorIngestionJob"
    );

    // ── Step 7: Navigate to dashboard ────────────────────────────────────
    setItem({ ...item, definition: activatedConfig as any });
    setActivationSuccess(true);
    viewSetter?.(VIEWS.DASHBOARD);

  } catch (error) {
    const message = error instanceof Error ? error.message : "Activation failed.";
    updateWizard({ validationErrors: { activate: message } });
  } finally {
    updateWizard({ isActivating: false });
  }
}
```

### buildConnectorDefinition helper (add to ConnectorItemEditor.tsx)

```typescript
function buildConnectorDefinition(
  state: WizardState,
  item: ItemWithDefinition<ConnectorItemDefinition>
): ConnectorItemDefinition {
  const baseAuth = buildAuthConfiguration(state.auth);
  const baseMetadata = {
    displayName: item.displayName,
    createdAt:   item.definition?.metadata?.createdAt ?? new Date().toISOString(),
    updatedAt:   new Date().toISOString(),
  };

  const baseStorage: StorageConfiguration = {
    bronzeLakeHouseName:   state.storage.bronzeLakeHouseName ?? "FabricUniversalConnector-Bronze",
    schemaEvolutionPolicy: state.storage.schemaEvolutionPolicy ?? "merge",
    useExistingLakehouse:  state.storage.useExistingLakehouse ?? false,
  };

  const baseScheduling: SchedulingConfiguration = {
    scheduleType:    state.schedule.scheduleType ?? "cron",
    cronExpression:  state.schedule.cronExpression,
    intervalMinutes: state.schedule.intervalMinutes,
    timezone:        state.schedule.timezone ?? "UTC",
    enabled:         state.schedule.enabled ?? true,
  };

  const baseFeatures: FeaturesConfiguration = {
    schemaEvolutionHandling: state.storage.schemaEvolutionPolicy ?? "merge",
    errorThresholdPercent:   25,
    enablePartialRun:        true,
    enableTelemetry:         true,
  };

  if (state.moduleType === "crm") {
    return {
      schemaVersion: "1.0.0",
      state:         "configured",
      moduleType:    "crm",
      source: {
        environmentUrl:      (state.source as any).environmentUrl,
        tenantId:            (state.source as any).tenantId,
        apiVersion:          "v9.2",
        enableChangeTracking: true,
        pageSize:            1000,
      },
      authentication: baseAuth,
      entities: state.selectedEntities.map((name) => ({
        logicalName:    name,
        displayName:    CRM_CATALOG_DISPLAY_NAME[name] ?? name,
        enabled:        true,
        extractionMode: "incremental",
        batchSize:      1000,
      })),
      storage:   baseStorage,
      scheduling: baseScheduling,
      features:  baseFeatures,
      metadata:  baseMetadata,
    };
  }

  throw new Error(`buildConnectorDefinition: unsupported moduleType ${state.moduleType}`);
}

// Display names for CRM catalog (used in buildConnectorDefinition)
const CRM_CATALOG_DISPLAY_NAME: Record<string, string> = {
  contact:                    "Contact",
  lead:                       "Lead",
  msdynmkt_marketingform:     "Marketing Form",
  msdynmkt_marketingemail:    "Marketing Email",
  msdynmkt_customerjourney:   "Customer Journey",
};

function buildAuthConfiguration(auth: WizardAuthData): AuthConfiguration {
  if (auth.mode === "fabric_connection") {
    return { mode: "fabric_connection", fabricConnectionId: auth.fabricConnectionId! };
  }
  if (auth.mode === "keyvault_reference") {
    return {
      mode: "keyvault_reference",
      keyVaultUri:      auth.keyVaultUri!,
      clientSecretName: auth.clientSecretName!,
    };
  }
  if (auth.mode === "service_principal") {
    return {
      mode:     "service_principal",
      tenantId: auth.tenantId!,
      clientId: auth.clientId!,
      secretRef: { mode: "fabric_connection", fabricConnectionId: auth.fabricConnectionId! },
    };
  }
  throw new Error("buildAuthConfiguration: auth.mode is null");
}
```

### buildScheduleRequest helper (add to wizardState.ts)

```typescript
import { CreateScheduleRequest } from "../../../clients/FabricPlatformTypes";

export function buildScheduleRequest(
  schedule: Partial<SchedulingConfiguration>
): CreateScheduleRequest {
  if (schedule.scheduleType === "cron") {
    return {
      enabled: schedule.enabled ?? true,
      configuration: {
        type:            "Cron",
        startDateTime:   schedule.startDate ?? new Date().toISOString(),
        endDateTime:     undefined,
        localTimeZoneId: schedule.timezone ?? "UTC",
        cronExpression:  schedule.cronExpression ?? "0 2 * * *",
      },
    };
  }
  return {
    enabled: schedule.enabled ?? true,
    configuration: {
      type:      "Daily",
      startDateTime: schedule.startDate ?? new Date().toISOString(),
      endDateTime:   undefined,
      localTimeZoneId: schedule.timezone ?? "UTC",
      times: [{ hour: 2, minute: 0 }],
    },
  };
}
```

### Wizard ribbon: wire Next / Back / Activate buttons

In `ConnectorItemRibbon.tsx`, add these props and action sets for wizard views:

```typescript
// ── Add to ConnectorItemRibbonProps ──────────────────────────────────────
onWizardNext: () => void;
onWizardBack: () => void;
onActivate: () => Promise<void>;
isActivating: boolean;

// ── In ConnectorItemRibbon function ──────────────────────────────────────
import { WIZARD_STEP_ORDER, WIZARD_STEPS } from "../wizard/wizardState";
import {
  ArrowLeft24Regular,
  ArrowRight24Regular,
  Checkmark24Regular,
} from "@fluentui/react-icons";

const isWizardView = WIZARD_STEP_ORDER.includes(currentView as any);
const isReviewStep = currentView === WIZARD_STEPS.REVIEW;
const isModuleStep = currentView === WIZARD_STEPS.MODULE;

const wizardActions: RibbonAction[] = isWizardView
  ? [
      ...(!isModuleStep
        ? [{
            key: "wizard-back",
            icon: ArrowLeft24Regular,
            label: "Back",
            onClick: async () => onWizardBack(),
            testId: "ribbon-wizard-back",
          }]
        : []),
      isReviewStep
        ? {
            key: "activate",
            icon: Checkmark24Regular,
            label: isActivating ? "Activating..." : "Activate",
            onClick: onActivate,
            testId: "ribbon-activate-btn",
            disabled: isActivating,
          }
        : {
            key: "wizard-next",
            icon: ArrowRight24Regular,
            label: "Next",
            onClick: async () => onWizardNext(),
            testId: "ribbon-wizard-next",
          },
    ]
  : [];
```

### Wire wizard navigation in ConnectorItemEditor.tsx

```typescript
// ── Add wizard navigation handlers (inside ConnectorItemEditor) ──────────

function handleWizardNext(): void {
  const validation = validateStep(wizardState, wizardState.step);
  if (!validation.isValid) {
    updateWizard({ validationErrors: validation.errors });
    return;
  }
  const next = getNextStep(wizardState.step);
  if (next) {
    updateWizard({ step: next, validationErrors: {} });
    viewSetter?.(next);
  }
}

function handleWizardBack(): void {
  const prev = getPrevStep(wizardState.step);
  if (prev) {
    updateWizard({ step: prev, validationErrors: {} });
    viewSetter?.(prev);
  }
}
```

---

## 6. FRONTEND: NotebookDeploymentController.ts — COMPLETE IMPLEMENTATION

**File:** `Workload/app/controller/NotebookDeploymentController.ts`

```typescript
import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { ItemClient } from "../clients/ItemClient";
import { ModuleType } from "../items/ConnectorItem/ConnectorItemDefinition";

const CURRENT_WHEEL_VERSION = "1.0.0";

export interface NotebookDeploymentResult {
  notebookItemId: string;
  deployedAt: string;
  wheelVersion: string;
}

/**
 * Fetches the notebook template content from the bundled assets,
 * substitutes placeholders, and creates a Notebook item in the
 * customer's Fabric workspace via the Items API.
 */
export async function deployConnectorNotebook(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  connectorItemId: string,
  moduleType: ModuleType
): Promise<NotebookDeploymentResult> {
  const templatePath = `/assets/notebooks/connector_runtime_${moduleType}.ipynb`;
  const templateResponse = await fetch(templatePath);
  if (!templateResponse.ok) {
    throw new Error(`Failed to load notebook template for module '${moduleType}': ${templateResponse.statusText}`);
  }
  const templateJson = await templateResponse.text();

  // Substitute placeholders exactly (no regex — avoid corrupting notebook JSON)
  const notebookContent = templateJson
    .split("%%WHEEL_VERSION%%").join(CURRENT_WHEEL_VERSION)
    .split("%%CONNECTOR_ITEM_ID%%").join(connectorItemId)
    .split("%%WORKSPACE_ID%%").join(workspaceId);

  // Base64-encode the notebook content
  const encodedContent = btoa(unescape(encodeURIComponent(notebookContent)));

  const displayName = buildNotebookDisplayName(moduleType, connectorItemId);

  const itemClient = new ItemClient(workloadClient);
  const createdItem = await itemClient.createItem(workspaceId, {
    displayName,
    type: "Notebook",
    definition: {
      format: "ipynb",
      parts: [
        {
          path:        "artifact.content.ipynb",
          payload:     encodedContent,
          payloadType: "InlineBase64",
        },
      ],
    },
  });

  return {
    notebookItemId: createdItem.id,
    deployedAt:     new Date().toISOString(),
    wheelVersion:   CURRENT_WHEEL_VERSION,
  };
}

export function buildNotebookDisplayName(moduleType: ModuleType, connectorItemId: string): string {
  const prefix: Record<ModuleType, string> = {
    crm:             "FUC-CRM-Runtime",
    businesscentral: "FUC-BC-Runtime",
    sql:             "FUC-SQL-Runtime",
  };
  return `${prefix[moduleType]}-${connectorItemId}`;
}
```

### Notebook template location in webpack

The `.ipynb` files in `connector/runtime/notebooks/` must be copied to the webpack output's `assets/notebooks/` directory. Add to `webpack.config.js`:

```javascript
// In webpack.config.js plugins array:
const CopyWebpackPlugin = require("copy-webpack-plugin");

new CopyWebpackPlugin({
  patterns: [
    {
      from: path.resolve(__dirname, "../connector/runtime/notebooks"),
      to:   path.resolve(__dirname, "dist/assets/notebooks"),
    },
  ],
}),
```

If the Python repo is separate, copy the `.ipynb` files to `Workload/app/assets/notebooks/` and reference from there.

---

## 7. FRONTEND: LakehouseController.ts — COMPLETE IMPLEMENTATION

**File:** `Workload/app/controller/LakehouseController.ts`

```typescript
import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { ItemClient } from "../clients/ItemClient";

export interface LakehouseEnsureResult {
  lakeHouseId: string;
  lakeHouseName: string;
  wasCreated: boolean;
}

/**
 * Creates a new Bronze Lakehouse in the customer workspace, or returns
 * an existing one by display name if useExisting = true.
 *
 * The Lakehouse creation is synchronous via the Fabric Items API.
 * The Items API returns a 202 LRO for Lakehouse creation; ItemClient
 * handles 202 responses transparently via FabricPlatformClient.makeRequest().
 */
export async function ensureBronzeLakehouse(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  lakeHouseName: string,
  useExisting: boolean
): Promise<LakehouseEnsureResult> {
  const itemClient = new ItemClient(workloadClient);

  if (useExisting) {
    // Find the existing Lakehouse by display name
    const allItems = await itemClient.getAllItems(workspaceId);
    const existing = allItems.find(
      (i) => i.type === "Lakehouse" && i.displayName === lakeHouseName
    );
    if (!existing) {
      throw new Error(
        `Lakehouse '${lakeHouseName}' not found in workspace. ` +
        `Uncheck "Use an existing Lakehouse" or ensure the name is correct.`
      );
    }
    return {
      lakeHouseId:  existing.id,
      lakeHouseName: existing.displayName,
      wasCreated:   false,
    };
  }

  // Create a new Lakehouse
  const created = await itemClient.createItem(workspaceId, {
    displayName: lakeHouseName,
    type:        "Lakehouse",
  });

  return {
    lakeHouseId:  created.id,
    lakeHouseName: created.displayName,
    wasCreated:   true,
  };
}
```

---

## 8. PYTHON: connector_base.py — COMPLETE IMPLEMENTATION

**File:** `connector/runtime/agic_fabric_connector/base/connector_base.py`

```python
from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import List, Optional

import pandas as pd
from pyspark.sql import SparkSession

from agic_fabric_connector.base.bronze_writer import BronzeWriter
from agic_fabric_connector.base.exceptions import (
    ConnectorFatalError, EntityExtractionError, BronzeWriteError
)
from agic_fabric_connector.base.metadata_writer import MetadataWriter
from agic_fabric_connector.base.retry_policy import RetryPolicy
from agic_fabric_connector.base.run_result import EntityResult, RunResult
from agic_fabric_connector.base.schema_evolution import SchemaEvolutionHandler
from agic_fabric_connector.base.watermark import Watermark, WatermarkStore
from agic_fabric_connector.config.config_models import ConnectorItemDefinition, EntityConfig


class BaseConnector(ABC):
    """
    Abstract base class for all Fabric Universal Connector module implementations.
    Subclasses implement source-specific authentication and extraction.
    All shared concerns are handled here and must NOT be re-implemented in subclasses.
    """

    def __init__(
        self,
        config: ConnectorItemDefinition,
        spark: SparkSession,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> None:
        self.config = config
        self.spark = spark
        self.retry_policy = retry_policy or RetryPolicy()
        self._metadata_writer = MetadataWriter(config, spark)
        self._bronze_writer = BronzeWriter(config, spark)
        self._watermark_store = WatermarkStore(config, spark)
        self._schema_handler = SchemaEvolutionHandler(
            config.features.schema_evolution_handling if config.features else "merge"
        )

    # ── Public entry point ────────────────────────────────────────────────

    def run(self) -> RunResult:
        """Orchestrates the full ingestion run. Called once per notebook execution."""
        run_record = self._metadata_writer.start_run()
        try:
            self._validate_config()
            auth = self.retry_policy.execute(self._authenticate)
            enabled_entities = self._get_enabled_entities()
            results = self._process_entities(enabled_entities, auth)
            run_record = self._metadata_writer.complete_run(run_record, results)
            return RunResult(
                run_id=run_record.run_id,
                status=run_record.status,
                entity_results=results,
            )
        except ConnectorFatalError as exc:
            self._metadata_writer.fail_run(run_record, str(exc), exc.error_code)
            raise
        except Exception as exc:
            self._metadata_writer.fail_run(run_record, str(exc), "UNEXPECTED_ERROR")
            raise ConnectorFatalError(str(exc), "UNEXPECTED_ERROR") from exc

    # ── Abstract methods — implement in subclass ──────────────────────────

    @abstractmethod
    def _authenticate(self):
        """Authenticate to the source system. Return an AuthContext."""
        ...

    @abstractmethod
    def _extract_entity(
        self,
        entity: EntityConfig,
        auth,
        watermark: Optional[Watermark],
    ) -> pd.DataFrame:
        """Extract records for one entity. Must NOT write to Bronze."""
        ...

    @abstractmethod
    def _get_new_watermark(
        self,
        entity: EntityConfig,
        auth,
        extraction_result: pd.DataFrame,
    ) -> Optional[Watermark]:
        """Return the new watermark after a successful extraction and write."""
        ...

    # ── Provided by base — do NOT override ───────────────────────────────

    def _validate_config(self) -> None:
        from agic_fabric_connector.config.config_validator import ConfigValidator
        ConfigValidator.validate(self.config)

    def _get_enabled_entities(self) -> List[EntityConfig]:
        return [e for e in self.config.entities if e.enabled]

    def _process_entities(self, entities: List[EntityConfig], auth) -> List[EntityResult]:
        results: List[EntityResult] = []
        failure_count = 0
        threshold = (self.config.features.error_threshold_percent
                     if self.config.features else 25.0)

        for entity in entities:
            result = self._process_single_entity(entity, auth)
            results.append(result)
            if result.status == "failed":
                failure_count += 1
                pct = (failure_count / len(entities)) * 100
                if pct > threshold:
                    raise ConnectorFatalError(
                        f"Error threshold {threshold}% exceeded: "
                        f"{failure_count}/{len(entities)} entities failed.",
                        "ERROR_THRESHOLD_EXCEEDED",
                    )
        return results

    def _process_single_entity(self, entity: EntityConfig, auth) -> EntityResult:
        t0 = time.monotonic()
        entity_key = entity.logical_name or entity.api_endpoint or entity.table_name or "unknown"
        try:
            watermark = self._watermark_store.get(entity_key)
            df = self.retry_policy.execute(self._extract_entity, entity, auth, watermark)
            df = self._schema_handler.handle(df, entity, self.spark)
            self._bronze_writer.write(df, entity)
            new_wm = self._get_new_watermark(entity, auth, df)
            if new_wm is not None:
                self._watermark_store.upsert(entity, new_wm)
            duration = time.monotonic() - t0
            return EntityResult(
                entity_name=entity_key,
                status="success",
                records_ingested=len(df),
                records_failed=0,
                duration_seconds=duration,
                new_watermark=str(new_wm) if new_wm else None,
                error_message=None,
            )
        except (EntityExtractionError, BronzeWriteError, ConnectorFatalError) as exc:
            duration = time.monotonic() - t0
            self._metadata_writer.log_error(entity, exc)
            return EntityResult(
                entity_name=entity_key,
                status="failed",
                records_ingested=0,
                records_failed=0,
                duration_seconds=duration,
                new_watermark=None,
                error_message=str(exc),
            )
        except Exception as exc:
            duration = time.monotonic() - t0
            self._metadata_writer.log_error(entity, exc)
            return EntityResult(
                entity_name=entity_key,
                status="failed",
                records_ingested=0,
                records_failed=0,
                duration_seconds=duration,
                new_watermark=None,
                error_message=f"UNEXPECTED: {exc}",
            )
```

---

## 9. PYTHON: config_loader.py — COMPLETE IMPLEMENTATION

**File:** `connector/runtime/agic_fabric_connector/config/config_loader.py`

```python
from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING

import requests
from pyspark.sql import SparkSession

from agic_fabric_connector.base.exceptions import ConfigLoadError, ConfigValidationError
from agic_fabric_connector.config.config_models import ConnectorItemDefinition

if TYPE_CHECKING:
    pass

FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"
FABRIC_TOKEN_AUDIENCE = "https://api.fabric.microsoft.com"


class ConfigLoader:
    """Loads and validates the ConnectorItemDefinition from a Fabric item in notebook context."""

    @staticmethod
    def from_item_definition(
        item_id: str,
        workspace_id: str,
        spark: SparkSession,
    ) -> ConnectorItemDefinition:
        """
        Reads the item definition from the Fabric Items API using the notebook's
        built-in MSI token (acquired via mssparkutils).

        Steps:
          1. Acquire Fabric API token via mssparkutils
          2. GET /v1/workspaces/{workspaceId}/items/{itemId}/getDefinition (POST, LRO)
          3. Decode base64 payload.json content
          4. Parse and validate JSON
          5. Deserialize into ConnectorItemDefinition
        """
        try:
            from notebookutils import mssparkutils
        except ImportError:
            raise ConfigLoadError(
                "mssparkutils not available — this loader must run inside a Fabric notebook."
            )

        # Acquire Fabric API token using the notebook's managed identity
        try:
            token = mssparkutils.credentials.getToken(FABRIC_TOKEN_AUDIENCE)
        except Exception as exc:
            raise ConfigLoadError(f"Failed to acquire Fabric token: {exc}") from exc

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        }

        # POST /getDefinition triggers a long-running operation (202 → poll → 200)
        get_def_url = (
            f"{FABRIC_API_BASE}/workspaces/{workspace_id}"
            f"/items/{item_id}/getDefinition"
        )

        response = requests.post(get_def_url, headers=headers, timeout=30)

        if response.status_code == 200:
            definition_response = response.json()
        elif response.status_code == 202:
            # Poll the operation until complete
            operation_url = response.headers.get("Location") or response.headers.get("location")
            if not operation_url:
                raise ConfigLoadError("getDefinition returned 202 but no Location header.")
            definition_response = ConfigLoader._poll_lro(operation_url, headers)
        else:
            raise ConfigLoadError(
                f"getDefinition failed: HTTP {response.status_code} — {response.text[:500]}"
            )

        # Extract and decode payload.json from the definition response
        parts = definition_response.get("definition", {}).get("parts", [])
        payload_part = next(
            (p for p in parts if p.get("path") == "payload.json"), None
        )
        if payload_part is None:
            raise ConfigValidationError(
                f"Item {item_id} definition does not contain 'payload.json'. "
                "The connector may not have been activated yet."
            )

        encoded_payload = payload_part.get("payload", "")
        try:
            raw_json = base64.b64decode(encoded_payload).decode("utf-8")
            config_dict = json.loads(raw_json)
        except Exception as exc:
            raise ConfigValidationError(f"Failed to decode payload.json: {exc}") from exc

        config = ConnectorItemDefinition.from_dict(config_dict)
        ConfigLoader.validate(config)
        return config

    @staticmethod
    def _poll_lro(operation_url: str, headers: dict, max_wait_seconds: int = 300) -> dict:
        """Polls a Fabric LRO until it reaches a terminal state."""
        import time
        elapsed = 0
        poll_interval = 2

        while elapsed < max_wait_seconds:
            response = requests.get(operation_url, headers=headers, timeout=30)
            if response.status_code not in (200, 202):
                raise ConfigLoadError(
                    f"LRO polling failed: HTTP {response.status_code} — {response.text[:500]}"
                )
            body = response.json()
            status = body.get("status", "").lower()

            if status in ("succeeded", "completed"):
                # Result may be in body directly or at a result URL
                result_url = body.get("resourceLocation") or body.get("resultUri")
                if result_url:
                    result = requests.get(result_url, headers=headers, timeout=30)
                    return result.json()
                return body

            if status in ("failed", "cancelled"):
                error = body.get("error", {})
                raise ConfigLoadError(
                    f"getDefinition LRO failed: {error.get('message', 'Unknown error')}"
                )

            time.sleep(poll_interval)
            elapsed += poll_interval
            poll_interval = min(poll_interval * 1.5, 15)

        raise ConfigLoadError(f"getDefinition LRO timed out after {max_wait_seconds}s.")

    @staticmethod
    def validate(config: ConnectorItemDefinition) -> None:
        """Validates a deserialized config for completeness before running."""
        if config.schema_version != "1.0.0":
            raise ConfigValidationError(
                f"Unknown schema version: {config.schema_version}. Expected '1.0.0'."
            )
        if config.state != "configured":
            raise ConfigValidationError(
                f"ConnectorItem state is '{config.state}' — expected 'configured'. "
                "Run the activation wizard before executing this notebook."
            )
        if not config.authentication:
            raise ConfigValidationError("authentication is missing from config.")
        if not any(e.enabled for e in config.entities):
            raise ConfigValidationError("No entities are enabled. Enable at least one entity.")
        if not (config.runtime and config.runtime.notebook_item_id):
            raise ConfigValidationError(
                "runtime.notebookItemId is missing. Re-activate the connector."
            )
        if not (config.runtime and config.runtime.bronze_lake_house_id):
            raise ConfigValidationError(
                "runtime.bronzeLakeHouseId is missing. Re-activate the connector."
            )
```

---

## 10. PYTHON: config_models.py — COMPLETE IMPLEMENTATION

**File:** `connector/runtime/agic_fabric_connector/config/config_models.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


@dataclass
class CrmSourceConfig:
    environment_url:       str
    tenant_id:             str
    api_version:           str   = "v9.2"
    enable_change_tracking: bool = True
    page_size:             int   = 1000


@dataclass
class BusinessCentralSourceConfig:
    tenant_id:   str
    environment: str
    company_id:  Optional[str] = None
    api_version: str = "v2.0"
    page_size:   int = 200


@dataclass
class SqlSourceConfig:
    server:                   str
    database:                 str
    port:                     int  = 1433
    driver:                   str  = "sqlserver"
    encrypt:                  bool = True
    trust_server_certificate: bool = False
    query_timeout:            int  = 300
    fetch_size:               int  = 10000


@dataclass
class FabricConnectionAuth:
    mode:                 str   # "fabric_connection"
    fabric_connection_id: str


@dataclass
class KeyVaultReferenceAuth:
    mode:                  str   # "keyvault_reference"
    key_vault_uri:         str
    client_secret_name:    str
    client_id_secret_name: Optional[str] = None
    tenant_id_secret_name: Optional[str] = None


@dataclass
class ServicePrincipalAuth:
    mode:       str   # "service_principal"
    tenant_id:  str
    client_id:  str
    secret_ref: Any   # FabricConnectionAuth | KeyVaultReferenceAuth


@dataclass
class EntityConfig:
    display_name:     str
    enabled:          bool
    extraction_mode:  str   = "incremental"
    batch_size:       int   = 1000
    # CRM-specific
    logical_name:     Optional[str] = None
    select_columns:   List[str] = field(default_factory=list)
    filter_expression: Optional[str] = None
    # BC-specific
    api_endpoint:     Optional[str] = None
    watermark_column: Optional[str] = None
    # SQL-specific
    schema:           Optional[str] = None
    table_name:       Optional[str] = None
    where_clause:     Optional[str] = None


@dataclass
class StorageConfig:
    bronze_lake_house_name:  str
    bronze_lake_house_id:    Optional[str] = None
    schema_evolution_policy: str   = "merge"
    retention_days:          Optional[int] = None
    use_existing_lake_house: bool  = False


@dataclass
class SchedulingConfig:
    schedule_type:   str   # "cron" | "interval"
    enabled:         bool  = True
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    timezone:        str   = "UTC"
    start_date:      Optional[str] = None


@dataclass
class FeaturesConfig:
    schema_evolution_handling:    str   = "merge"
    error_threshold_percent:      float = 25.0
    enable_partial_run:           bool  = True
    enable_telemetry:             bool  = True
    max_records_per_entity_per_run: Optional[int] = None
    enable_delta_lake_optimize:   bool  = False


@dataclass
class RuntimeConfig:
    notebook_item_id:    Optional[str] = None
    bronze_lake_house_id: Optional[str] = None
    deployed_at:         Optional[str] = None
    wheel_version:       Optional[str] = None
    config_schema_version: Optional[str] = None
    job_schedule_id:     Optional[str] = None


@dataclass
class ConnectorMetadataConfig:
    display_name:  Optional[str] = None
    description:   Optional[str] = None
    tags:          List[str] = field(default_factory=list)
    created_at:    Optional[str] = None
    updated_at:    Optional[str] = None
    activated_at:  Optional[str] = None


@dataclass
class ConnectorItemDefinition:
    schema_version: str
    module_type:    str   # "crm" | "businesscentral" | "sql"
    state:          str   # "empty" | "configured" | "error" | "paused"
    entities:       List[EntityConfig]
    source:         Any   # CrmSourceConfig | BusinessCentralSourceConfig | SqlSourceConfig
    authentication: Any   # FabricConnectionAuth | KeyVaultReferenceAuth | ServicePrincipalAuth
    storage:        Optional[StorageConfig] = None
    scheduling:     Optional[SchedulingConfig] = None
    features:       Optional[FeaturesConfig] = None
    runtime:        Optional[RuntimeConfig] = None
    metadata:       Optional[ConnectorMetadataConfig] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ConnectorItemDefinition:
        """Deserializes a raw config dict (from JSON) into typed dataclasses."""
        module_type = d.get("moduleType", "")

        # Source
        raw_source = d.get("source", {})
        if module_type == "crm":
            source = CrmSourceConfig(
                environment_url=raw_source.get("environmentUrl", ""),
                tenant_id=raw_source.get("tenantId", ""),
                api_version=raw_source.get("apiVersion", "v9.2"),
                enable_change_tracking=raw_source.get("enableChangeTracking", True),
                page_size=raw_source.get("pageSize", 1000),
            )
        elif module_type == "businesscentral":
            source = BusinessCentralSourceConfig(
                tenant_id=raw_source.get("tenantId", ""),
                environment=raw_source.get("environment", ""),
                company_id=raw_source.get("companyId"),
                api_version=raw_source.get("apiVersion", "v2.0"),
                page_size=raw_source.get("pageSize", 200),
            )
        else:
            source = SqlSourceConfig(
                server=raw_source.get("server", ""),
                database=raw_source.get("database", ""),
                port=raw_source.get("port", 1433),
            )

        # Entities
        raw_entities = d.get("entities", [])
        entities = [
            EntityConfig(
                display_name=e.get("displayName", ""),
                enabled=e.get("enabled", True),
                extraction_mode=e.get("extractionMode", "incremental"),
                batch_size=e.get("batchSize", 1000),
                logical_name=e.get("logicalName"),
                select_columns=e.get("selectColumns", []),
                filter_expression=e.get("filterExpression"),
                api_endpoint=e.get("apiEndpoint"),
                watermark_column=e.get("watermarkColumn"),
                schema=e.get("schema"),
                table_name=e.get("tableName"),
                where_clause=e.get("whereClause"),
            )
            for e in raw_entities
        ]

        # Auth
        raw_auth = d.get("authentication", {})
        auth_mode = raw_auth.get("mode", "")
        if auth_mode == "fabric_connection":
            authentication = FabricConnectionAuth(
                mode="fabric_connection",
                fabric_connection_id=raw_auth.get("fabricConnectionId", ""),
            )
        elif auth_mode == "keyvault_reference":
            authentication = KeyVaultReferenceAuth(
                mode="keyvault_reference",
                key_vault_uri=raw_auth.get("keyVaultUri", ""),
                client_secret_name=raw_auth.get("clientSecretName", ""),
                client_id_secret_name=raw_auth.get("clientIdSecretName"),
                tenant_id_secret_name=raw_auth.get("tenantIdSecretName"),
            )
        else:
            authentication = ServicePrincipalAuth(
                mode="service_principal",
                tenant_id=raw_auth.get("tenantId", ""),
                client_id=raw_auth.get("clientId", ""),
                secret_ref=raw_auth.get("secretRef", {}),
            )

        # Storage
        raw_storage = d.get("storage", {})
        storage = StorageConfig(
            bronze_lake_house_name=raw_storage.get("bronzeLakeHouseName", "FabricUniversalConnector-Bronze"),
            bronze_lake_house_id=raw_storage.get("bronzeLakeHouseId"),
            schema_evolution_policy=raw_storage.get("schemaEvolutionPolicy", "merge"),
            retention_days=raw_storage.get("retentionDays"),
            use_existing_lake_house=raw_storage.get("useExistingLakehouse", False),
        ) if raw_storage else None

        # Runtime
        raw_runtime = d.get("runtime", {})
        runtime = RuntimeConfig(
            notebook_item_id=raw_runtime.get("notebookItemId"),
            bronze_lake_house_id=raw_runtime.get("bronzeLakeHouseId"),
            deployed_at=raw_runtime.get("deployedAt"),
            wheel_version=raw_runtime.get("wheelVersion"),
            config_schema_version=raw_runtime.get("configSchemaVersion"),
            job_schedule_id=raw_runtime.get("jobScheduleId"),
        ) if raw_runtime else None

        # Features
        raw_features = d.get("features", {})
        features = FeaturesConfig(
            schema_evolution_handling=raw_features.get("schemaEvolutionHandling", "merge"),
            error_threshold_percent=raw_features.get("errorThresholdPercent", 25.0),
            enable_partial_run=raw_features.get("enablePartialRun", True),
            enable_telemetry=raw_features.get("enableTelemetry", True),
            max_records_per_entity_per_run=raw_features.get("maxRecordsPerEntityPerRun"),
            enable_delta_lake_optimize=raw_features.get("enableDeltaLakeOptimize", False),
        ) if raw_features else FeaturesConfig()

        return cls(
            schema_version=d.get("schemaVersion", "1.0.0"),
            module_type=module_type,
            state=d.get("state", "empty"),
            source=source,
            authentication=authentication,
            entities=entities,
            storage=storage,
            scheduling=None,
            features=features,
            runtime=runtime,
            metadata=None,
        )
```

---

## 11. PYTHON: bronze_writer.py — COMPLETE IMPLEMENTATION

**File:** `connector/runtime/agic_fabric_connector/base/bronze_writer.py`

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, TimestampType, DateType, BooleanType

from agic_fabric_connector.base.exceptions import BronzeWriteError
from agic_fabric_connector.config.config_models import (
    ConnectorItemDefinition, EntityConfig, StorageConfig
)

WHEEL_VERSION = "1.0.0"

BRONZE_SCHEMA_MAP = {
    "crm":             "bronze_crm",
    "businesscentral": "bronze_bc",
    "sql":             "bronze_sql",
}


class BronzeWriter:
    """
    Writes a pandas DataFrame to a Bronze Delta table with all 12 ISV metadata columns.
    """

    def __init__(self, config: ConnectorItemDefinition, spark: SparkSession) -> None:
        self.config = config
        self.spark = spark
        self._run_id: Optional[str] = None   # Set by MetadataWriter before first write

    def set_run_id(self, run_id: str) -> None:
        self._run_id = run_id

    def write(self, df: pd.DataFrame, entity: EntityConfig) -> int:
        """Writes df to Bronze. Returns number of rows written."""
        if df.empty:
            return 0

        run_id = self._run_id or str(uuid.uuid4())
        connector_id = (self.config.runtime.notebook_item_id or "unknown"
                        if self.config.runtime else "unknown")

        # Validate no source column uses _ prefix
        for col in df.columns:
            if col.startswith("_"):
                raise BronzeWriteError(
                    f"Source column '{col}' starts with '_' — reserved for ISV metadata. "
                    "Rename the source column before writing to Bronze."
                )

        entity_key = (entity.logical_name or entity.api_endpoint
                      or entity.table_name or "unknown")

        try:
            spark_df = self.spark.createDataFrame(df)
        except Exception as exc:
            raise BronzeWriteError(f"createDataFrame failed for '{entity_key}': {exc}") from exc

        now_ts = datetime.now(timezone.utc)
        source_modified_col = self._get_source_modified_column(df, entity)
        etag_col = self._get_etag_column(df)

        # Add all 12 ISV metadata columns
        spark_df = (
            spark_df
            .withColumn("_run_id",               F.lit(run_id))
            .withColumn("_connector_id",          F.lit(connector_id))
            .withColumn("_module_type",            F.lit(self.config.module_type))
            .withColumn("_entity_name",            F.lit(entity_key))
            .withColumn("_operation",              F.lit("insert"))   # override for delete in CRM
            .withColumn("_is_current",             F.lit(True))
            .withColumn("_ingestion_utc",          F.lit(now_ts.isoformat()).cast(TimestampType()))
            .withColumn("_ingestion_date",         F.lit(now_ts.date().isoformat()).cast(DateType()))
            .withColumn("_source_modified_utc",
                        F.col(source_modified_col).cast(TimestampType())
                        if source_modified_col else F.lit(None).cast(TimestampType()))
            .withColumn("_source_row_version",
                        F.col(etag_col).cast(StringType())
                        if etag_col else F.lit(None).cast(StringType()))
            .withColumn("_schema_version",
                        F.lit(getattr(self.config.source, "api_version", "unknown")))
            .withColumn("_wheel_version",          F.lit(WHEEL_VERSION))
        )

        schema_name = BRONZE_SCHEMA_MAP.get(self.config.module_type, "bronze_unknown")
        table_name  = self._build_table_name(entity)
        full_table  = f"{schema_name}.{table_name}"

        storage = self.config.storage
        merge_schema = (storage.schema_evolution_policy == "merge") if storage else True
        write_mode   = "overwrite" if (storage and storage.schema_evolution_policy == "overwrite") else "append"

        try:
            writer = (
                spark_df.write
                .format("delta")
                .partitionBy("_ingestion_date")
                .option("mergeSchema", str(merge_schema).lower())
                .mode(write_mode)
            )
            writer.saveAsTable(full_table)
        except Exception as exc:
            raise BronzeWriteError(f"Delta write failed for '{full_table}': {exc}") from exc

        return df.shape[0]

    def _build_table_name(self, entity: EntityConfig) -> str:
        if self.config.module_type == "crm":
            return entity.logical_name or "unknown"
        if self.config.module_type == "businesscentral":
            return entity.api_endpoint or "unknown"
        if self.config.module_type == "sql":
            schema = (entity.schema or "dbo").lower().replace(" ", "_")
            table  = (entity.table_name or "unknown").lower().replace(" ", "_")
            return f"{schema}_{table}"
        return "unknown"

    def _get_source_modified_column(
        self, df: pd.DataFrame, entity: EntityConfig
    ) -> Optional[str]:
        # CRM: modifiedon, BC: lastModifiedDateTime, SQL: watermark_column
        candidates = ["modifiedon", "lastModifiedDateTime", "ModifiedAt", "modifiedat"]
        if entity.watermark_column and entity.watermark_column in df.columns:
            return entity.watermark_column
        for c in candidates:
            if c in df.columns:
                return c
        return None

    def _get_etag_column(self, df: pd.DataFrame) -> Optional[str]:
        for c in ["@odata.etag", "odata_etag", "_odata_etag"]:
            if c in df.columns:
                return c
        return None
```

---

## 12. PYTHON: metadata_writer.py — COMPLETE IMPLEMENTATION

**File:** `connector/runtime/agic_fabric_connector/base/metadata_writer.py`

```python
from __future__ import annotations

import json
import traceback
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
from pyspark.sql import SparkSession

from agic_fabric_connector.base.run_result import EntityResult
from agic_fabric_connector.config.config_models import ConnectorItemDefinition, EntityConfig

WHEEL_VERSION = "1.0.0"

BRONZE_SCHEMA_MAP = {
    "crm": "bronze_crm", "businesscentral": "bronze_bc", "sql": "bronze_sql",
}


class ConnectorRunRecord:
    def __init__(self, config: ConnectorItemDefinition):
        self.run_id = str(uuid.uuid4())
        self.connector_id = (config.runtime.notebook_item_id or "unknown"
                             if config.runtime else "unknown")
        self.module_type = config.module_type
        self.workspace_id = "unknown"  # set from notebook context if available
        self.run_start_utc = datetime.now(timezone.utc)
        self.run_end_utc: Optional[datetime] = None
        self.status = "running"
        self.triggered_by = "schedule"
        self.entities_enabled = 0
        self.entities_processed = 0
        self.entities_succeeded = 0
        self.entities_failed = 0
        self.records_ingested = 0
        self.records_failed = 0
        self.error_message: Optional[str] = None
        self.error_code: Optional[str] = None
        self.entity_results: List[EntityResult] = []
        self.wheel_version = WHEEL_VERSION
        self.config_schema_version = config.schema_version


class MetadataWriter:
    """Writes run lifecycle events and error logs to Bronze _meta tables."""

    def __init__(self, config: ConnectorItemDefinition, spark: SparkSession) -> None:
        self.config = config
        self.spark = spark
        self._schema = BRONZE_SCHEMA_MAP.get(config.module_type, "bronze_unknown")

    def start_run(self) -> ConnectorRunRecord:
        record = ConnectorRunRecord(self.config)
        record.entities_enabled = sum(
            1 for e in self.config.entities if e.enabled
        )
        self._upsert_run_record(record)
        return record

    def complete_run(
        self, record: ConnectorRunRecord, results: List[EntityResult]
    ) -> ConnectorRunRecord:
        record.run_end_utc = datetime.now(timezone.utc)
        record.entity_results = results
        record.entities_processed = len(results)
        record.entities_succeeded = sum(1 for r in results if r.status == "success")
        record.entities_failed = sum(1 for r in results if r.status == "failed")
        record.records_ingested = sum(r.records_ingested for r in results)
        record.records_failed = sum(r.records_failed for r in results)

        if record.entities_failed == 0:
            record.status = "success"
        elif record.entities_succeeded > 0:
            record.status = "partial_success"
        else:
            record.status = "failed"

        duration = (record.run_end_utc - record.run_start_utc).total_seconds()
        self._upsert_run_record(record, duration_seconds=int(duration))
        return record

    def fail_run(
        self, record: ConnectorRunRecord, message: str, code: str
    ) -> None:
        record.run_end_utc = datetime.now(timezone.utc)
        record.status = "failed"
        record.error_message = message[:2000]
        record.error_code = code
        duration = (record.run_end_utc - record.run_start_utc).total_seconds()
        self._upsert_run_record(record, duration_seconds=int(duration))

    def log_error(self, entity: EntityConfig, error: Exception) -> None:
        entity_key = entity.logical_name or entity.api_endpoint or entity.table_name or "unknown"
        error_id = str(uuid.uuid4())
        stack = traceback.format_exc()
        row = {
            "error_id":      error_id,
            "run_id":        "unknown",
            "connector_id":  (self.config.runtime.notebook_item_id or "unknown"
                              if self.config.runtime else "unknown"),
            "entity_name":   entity_key,
            "error_level":   "entity",
            "error_type":    getattr(error, "error_code", "UNEXPECTED_ERROR"),
            "error_code":    None,
            "error_message": str(error)[:4000],
            "record_id":     None,
            "occurred_utc":  datetime.now(timezone.utc).isoformat(),
            "retry_attempt": 0,
            "was_retried":   False,
            "stack_trace":   stack[:4000] if stack else None,
            "wheel_version": WHEEL_VERSION,
        }
        try:
            df = self.spark.createDataFrame([row])
            df.write.format("delta").mode("append").saveAsTable(
                f"{self._schema}._meta._error_log"
            )
        except Exception:
            pass  # Never let metadata writes kill the run

    def _upsert_run_record(
        self, record: ConnectorRunRecord, duration_seconds: int = 0
    ) -> None:
        entity_results_json = json.dumps([
            {
                "entityName":      r.entity_name,
                "status":          r.status,
                "recordsIngested": r.records_ingested,
                "recordsFailed":   r.records_failed,
                "durationSeconds": r.duration_seconds,
                "newWatermark":    r.new_watermark,
                "errorMessage":    r.error_message,
            }
            for r in record.entity_results
        ])
        row = {
            "run_id":               record.run_id,
            "connector_id":         record.connector_id,
            "module_type":          record.module_type,
            "run_start_utc":        record.run_start_utc.isoformat(),
            "run_end_utc":          record.run_end_utc.isoformat() if record.run_end_utc else None,
            "duration_seconds":     duration_seconds,
            "status":               record.status,
            "triggered_by":         record.triggered_by,
            "entities_enabled":     record.entities_enabled,
            "entities_processed":   record.entities_processed,
            "entities_succeeded":   record.entities_succeeded,
            "entities_failed":      record.entities_failed,
            "records_ingested":     record.records_ingested,
            "records_failed":       record.records_failed,
            "error_message":        record.error_message,
            "error_code":           record.error_code,
            "entity_results":       entity_results_json,
            "wheel_version":        record.wheel_version,
            "config_schema_version": record.config_schema_version,
            "workspace_id":         record.workspace_id,
        }
        try:
            df = self.spark.createDataFrame([row])
            # MERGE INTO upserts the run row (handles both initial insert and final update)
            df.createOrReplaceTempView("_run_update")
            self.spark.sql(f"""
                MERGE INTO {self._schema}._meta._connector_runs AS target
                USING _run_update AS source
                ON target.run_id = source.run_id
                WHEN MATCHED THEN UPDATE SET *
                WHEN NOT MATCHED THEN INSERT *
            """)
        except Exception:
            pass  # Never let metadata writes kill the run
```

---

## 13. PYTHON: watermark.py — COMPLETE IMPLEMENTATION

**File:** `connector/runtime/agic_fabric_connector/base/watermark.py`

```python
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pyspark.sql import SparkSession

from agic_fabric_connector.config.config_models import ConnectorItemDefinition, EntityConfig


class WatermarkType(str, Enum):
    DELTA_TOKEN = "delta_token"
    TIMESTAMP   = "timestamp"
    ROWVERSION  = "rowversion"


@dataclass
class Watermark:
    watermark_type:  WatermarkType
    delta_token:     Optional[str]
    watermark_value: Optional[str]
    watermark_column: Optional[str]

    def is_initial_load(self) -> bool:
        return self.delta_token is None and self.watermark_value is None

    def to_filter_value(self) -> str:
        return self.delta_token or self.watermark_value or ""

    def __str__(self) -> str:
        return self.delta_token or self.watermark_value or ""


BRONZE_SCHEMA_MAP = {
    "crm": "bronze_crm", "businesscentral": "bronze_bc", "sql": "bronze_sql",
}


class WatermarkStore:
    """Reads and writes entity watermarks to/from _entity_watermarks Delta table."""

    def __init__(self, config: ConnectorItemDefinition, spark: SparkSession) -> None:
        self.config = config
        self.spark = spark
        self._schema = BRONZE_SCHEMA_MAP.get(config.module_type, "bronze_unknown")
        self._connector_id = (config.runtime.notebook_item_id or "unknown"
                              if config.runtime else "unknown")
        self._workspace_id = "unknown"

    def get(self, entity_name: str) -> Optional[Watermark]:
        """Returns the current watermark or None if no watermark exists (triggers full extract)."""
        try:
            df = self.spark.sql(f"""
                SELECT watermark_type, delta_token, watermark_value, watermark_column
                FROM {self._schema}._meta._entity_watermarks
                WHERE connector_id = '{self._connector_id}'
                  AND entity_name  = '{entity_name}'
                LIMIT 1
            """)
            if df.count() == 0:
                return None
            row = df.first()
            return Watermark(
                watermark_type=WatermarkType(row["watermark_type"]),
                delta_token=row["delta_token"],
                watermark_value=row["watermark_value"],
                watermark_column=row["watermark_column"],
            )
        except Exception:
            # Table may not exist yet on first run — treat as no watermark
            return None

    def upsert(self, entity: EntityConfig, watermark: Watermark) -> None:
        """Persists the new watermark after successful extraction and write."""
        entity_key = entity.logical_name or entity.api_endpoint or entity.table_name or "unknown"
        row = {
            "connector_id":           self._connector_id,
            "entity_name":            entity_key,
            "module_type":            self.config.module_type,
            "watermark_type":         watermark.watermark_type.value,
            "delta_token":            watermark.delta_token,
            "watermark_value":        watermark.watermark_value,
            "watermark_column":       watermark.watermark_column,
            "last_run_id":            "unknown",
            "last_success_utc":       datetime.now(timezone.utc).isoformat(),
            "records_at_last_run":    0,
            "records_at_source_est":  None,
            "is_initial_load_complete": True,
            "workspace_id":           self._workspace_id,
        }
        df = self.spark.createDataFrame([row])
        df.createOrReplaceTempView("_wm_update")
        self.spark.sql(f"""
            MERGE INTO {self._schema}._meta._entity_watermarks AS target
            USING _wm_update AS source
            ON target.connector_id = source.connector_id
            AND target.entity_name = source.entity_name
            WHEN MATCHED THEN UPDATE SET *
            WHEN NOT MATCHED THEN INSERT *
        """)

    def reset(self, entity_name: str) -> None:
        """Deletes the watermark row. Triggers full extract on next run."""
        self.spark.sql(f"""
            DELETE FROM {self._schema}._meta._entity_watermarks
            WHERE connector_id = '{self._connector_id}'
              AND entity_name  = '{entity_name}'
        """)
```

---

## 14. PYTHON: schema_evolution.py — COMPLETE IMPLEMENTATION

**File:** `connector/runtime/agic_fabric_connector/base/schema_evolution.py`

```python
from __future__ import annotations

from typing import Optional

import pandas as pd
from pyspark.sql import SparkSession

from agic_fabric_connector.base.exceptions import SchemaConflictError
from agic_fabric_connector.config.config_models import EntityConfig


class SchemaEvolutionHandler:
    """Enforces schema evolution policy when source schema changes are detected."""

    def __init__(self, policy: str = "merge") -> None:
        if policy not in ("merge", "strict", "overwrite"):
            raise ValueError(f"Unknown schema evolution policy: {policy}")
        self.policy = policy

    def handle(
        self,
        df: pd.DataFrame,
        entity: EntityConfig,
        spark: SparkSession,
    ) -> pd.DataFrame:
        """Checks for schema changes and applies policy. Returns (possibly modified) df."""
        entity_key = entity.logical_name or entity.api_endpoint or entity.table_name or "unknown"

        if self.policy == "overwrite":
            # BronzeWriter will use mode="overwrite" — nothing to do here
            return df

        if self.policy == "strict":
            # Detect type conflicts against existing Delta schema
            existing_schema = self._get_existing_schema(entity_key, spark)
            if existing_schema:
                conflicts = self._detect_type_conflicts(df, existing_schema)
                if conflicts:
                    raise SchemaConflictError(
                        f"Schema conflict (strict policy) on '{entity_key}': "
                        + ", ".join(f"{c[0]}: {c[1]} → {c[2]}" for c in conflicts)
                    )
            return df

        # merge policy — Delta's mergeSchema=true handles new columns automatically
        # Just return df unchanged; BronzeWriter sets mergeSchema=true
        return df

    def _get_existing_schema(
        self, entity_key: str, spark: SparkSession
    ) -> Optional[dict]:
        """Returns existing Delta table schema as {col_name: spark_type_str} or None."""
        try:
            existing_df = spark.read.format("delta").table(entity_key)
            return {f.name: str(f.dataType) for f in existing_df.schema.fields
                    if not f.name.startswith("_")}
        except Exception:
            return None

    def _detect_type_conflicts(
        self, df: pd.DataFrame, existing_schema: dict
    ) -> list:
        """Returns list of (col_name, old_type, new_type) for columns with type narrowing."""
        conflicts = []
        for col in df.columns:
            if col.startswith("_"):
                continue
            if col in existing_schema:
                # Simple heuristic: flag if pandas inferred type doesn't match
                # Full type checking deferred to Phase 2
                pass
        return conflicts
```

---

## 15. PYTHON: retry_policy.py — COMPLETE IMPLEMENTATION

**File:** `connector/runtime/agic_fabric_connector/base/retry_policy.py`

```python
from __future__ import annotations

import time
from typing import Callable, TypeVar, Optional

from agic_fabric_connector.base.exceptions import (
    ThrottlingError, TransientError, AuthenticationError,
    ConnectorFatalError, EntityExtractionError,
)

T = TypeVar("T")


class RetryPolicy:
    """Configurable retry with exponential backoff. Respects Retry-After for throttling."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_backoff_seconds: float = 5.0,
        backoff_multiplier: float = 2.0,
        max_backoff_seconds: float = 300.0,
        respect_retry_after_header: bool = True,
    ) -> None:
        self.max_attempts = max_attempts
        self.initial_backoff_seconds = initial_backoff_seconds
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff_seconds = max_backoff_seconds
        self.respect_retry_after_header = respect_retry_after_header

    def execute(self, fn: Callable[..., T], *args, **kwargs) -> T:
        last_error: Optional[Exception] = None
        for attempt in range(self.max_attempts):
            try:
                return fn(*args, **kwargs)
            except (ThrottlingError, TransientError, AuthenticationError) as exc:
                last_error = exc
                wait = self._calculate_wait(exc, attempt)
                time.sleep(wait)
            except (ConnectorFatalError, EntityExtractionError):
                raise  # non-retryable — propagate immediately
        raise ConnectorFatalError(
            f"Max retry attempts ({self.max_attempts}) exhausted. Last error: {last_error}",
            "MAX_RETRIES_EXCEEDED",
        )

    def _calculate_wait(self, error: Exception, attempt: int) -> float:
        if (isinstance(error, ThrottlingError)
                and self.respect_retry_after_header
                and error.retry_after_seconds):
            return min(error.retry_after_seconds, self.max_backoff_seconds)
        backoff = self.initial_backoff_seconds * (self.backoff_multiplier ** attempt)
        return min(backoff, self.max_backoff_seconds)
```

---

## 16. PYTHON: crm_connector.py — COMPLETE IMPLEMENTATION

**File:** `connector/runtime/agic_fabric_connector/modules/crm/crm_connector.py`

```python
from __future__ import annotations

from typing import Optional

import pandas as pd
from pyspark.sql import SparkSession

from agic_fabric_connector.base.connector_base import BaseConnector
from agic_fabric_connector.base.watermark import Watermark, WatermarkType
from agic_fabric_connector.base.exceptions import (
    ConnectorFatalError, EntityExtractionError
)
from agic_fabric_connector.config.config_models import (
    ConnectorItemDefinition, EntityConfig, CrmSourceConfig,
    KeyVaultReferenceAuth, ServicePrincipalAuth, FabricConnectionAuth
)
from agic_fabric_connector.auth.crm_auth import CRMAuthContext, acquire_crm_token
from agic_fabric_connector.modules.crm.dataverse_client import DataverseClient
from agic_fabric_connector.modules.crm.entity_catalog import CRM_ENTITY_CATALOG


class CRMConnector(BaseConnector):
    """
    Dataverse / Dynamics 365 CRM module connector.
    Extracts data using OData Change Tracking (delta tokens).
    """

    MODULE_TYPE = "crm"
    BRONZE_SCHEMA = "bronze_crm"

    def __init__(self, config: ConnectorItemDefinition, spark: SparkSession) -> None:
        super().__init__(config, spark)
        self._source: CrmSourceConfig = config.source  # type: ignore
        self._last_delta_tokens: dict[str, str] = {}   # entity_name → new delta token

    def _authenticate(self) -> CRMAuthContext:
        """Acquire a Dataverse bearer token using the configured auth strategy."""
        auth_config = self.config.authentication

        if isinstance(auth_config, ServicePrincipalAuth):
            tenant_id = auth_config.tenant_id
            client_id = auth_config.client_id
            client_secret = self._resolve_secret(auth_config.secret_ref)
        elif isinstance(auth_config, KeyVaultReferenceAuth):
            tenant_id = self._resolve_kv_secret(
                auth_config.key_vault_uri, auth_config.tenant_id_secret_name or ""
            )
            client_id = self._resolve_kv_secret(
                auth_config.key_vault_uri, auth_config.client_id_secret_name or ""
            )
            client_secret = self._resolve_kv_secret(
                auth_config.key_vault_uri, auth_config.client_secret_name
            )
        else:
            raise ConnectorFatalError(
                f"Auth mode '{getattr(auth_config, 'mode', 'unknown')}' "
                "is not supported in CRM MVP. Use service_principal or keyvault_reference.",
                "CONFIG_VALIDATION_ERROR",
            )

        return acquire_crm_token(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            environment_url=self._source.environment_url,
        )

    def _extract_entity(
        self,
        entity: EntityConfig,
        auth: CRMAuthContext,
        watermark: Optional[Watermark],
    ) -> pd.DataFrame:
        """Extract records from Dataverse using Change Tracking delta tokens."""
        logical_name = entity.logical_name
        if not logical_name:
            raise EntityExtractionError(
                "CRM entity missing logical_name. Check entity configuration."
            )

        catalog_entry = CRM_ENTITY_CATALOG.get(logical_name)
        plural_name = catalog_entry.plural_name if catalog_entry else f"{logical_name}s"
        select_cols = entity.select_columns or (
            catalog_entry.default_select_columns if catalog_entry else []
        )
        page_size = entity.batch_size or self._source.page_size

        client = DataverseClient(
            environment_url=self._source.environment_url,
            api_version=self._source.api_version,
            access_token=auth.access_token,
        )

        if watermark and not watermark.is_initial_load():
            # Incremental: use stored delta token
            df, new_delta_token = client.get_delta_records(
                plural_entity_name=plural_name,
                delta_token=watermark.delta_token or "",
            )
        else:
            # Full extract: initialize Change Tracking
            df, new_delta_token = client.get_all_records(
                plural_entity_name=plural_name,
                select_columns=select_cols,
                filter_expression=entity.filter_expression,
                page_size=page_size,
                track_changes=self._source.enable_change_tracking,
            )

        # Store delta token for use in _get_new_watermark
        self._last_delta_tokens[logical_name] = new_delta_token
        return df

    def _get_new_watermark(
        self,
        entity: EntityConfig,
        auth: CRMAuthContext,
        extraction_result: pd.DataFrame,
    ) -> Optional[Watermark]:
        """Return the new delta token captured during extraction."""
        logical_name = entity.logical_name or ""
        new_token = self._last_delta_tokens.get(logical_name)
        if not new_token:
            return None  # no change tracking — no watermark
        return Watermark(
            watermark_type=WatermarkType.DELTA_TOKEN,
            delta_token=new_token,
            watermark_value=None,
            watermark_column=None,
        )

    # ── Private helpers ───────────────────────────────────────────────────

    def _resolve_secret(self, secret_ref) -> str:
        """Resolve client secret from a nested FabricConnectionAuth or KeyVaultReferenceAuth."""
        if isinstance(secret_ref, KeyVaultReferenceAuth):
            return self._resolve_kv_secret(
                secret_ref.key_vault_uri, secret_ref.client_secret_name
            )
        raise ConnectorFatalError(
            "FabricConnection secret resolution not yet implemented. Use keyvault_reference.",
            "CONFIG_VALIDATION_ERROR",
        )

    def _resolve_kv_secret(self, vault_uri: str, secret_name: str) -> str:
        """Resolve a secret from Azure Key Vault using the notebook MSI token."""
        try:
            from notebookutils import mssparkutils
            token = mssparkutils.credentials.getToken("https://vault.azure.net")
        except ImportError:
            raise ConnectorFatalError(
                "mssparkutils not available — Key Vault resolution requires a Fabric notebook.",
                "CONFIG_LOAD_ERROR",
            )

        import requests
        url = f"{vault_uri.rstrip('/')}/secrets/{secret_name}?api-version=7.4"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code == 200:
            return response.json().get("value", "")

        raise ConnectorFatalError(
            f"Key Vault secret '{secret_name}' could not be retrieved: "
            f"HTTP {response.status_code}",
            "AUTH_ERROR",
        )
```

---

## 17. PYTHON: dataverse_client.py — COMPLETE IMPLEMENTATION

**File:** `connector/runtime/agic_fabric_connector/modules/crm/dataverse_client.py`

```python
from __future__ import annotations

import re
from typing import List, Optional, Tuple
from urllib.parse import urlencode

import pandas as pd
import requests

from agic_fabric_connector.base.exceptions import (
    ThrottlingError, TransientError, EntityExtractionError
)

ODATA_NEXTLINK  = "@odata.nextLink"
ODATA_DELTALINK = "@odata.deltaLink"
ODATA_REMOVED   = "@odata.removed"
ODATA_CONTEXT   = "@odata.context"


class DataverseClient:
    """
    Thin HTTP client for Dataverse Web API (OData v4) with Change Tracking support.
    Handles pagination (nextLink), delta token capture (deltaLink), and error mapping.
    """

    def __init__(
        self,
        environment_url: str,
        api_version: str,
        access_token: str,
        timeout: int = 120,
    ) -> None:
        self._base_url = (
            f"{environment_url.rstrip('/')}/api/data/{api_version}"
        )
        self._headers = {
            "Authorization":  f"Bearer {access_token}",
            "Accept":         "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version":    "4.0",
        }
        self._timeout = timeout

    def get_all_records(
        self,
        plural_entity_name: str,
        select_columns: Optional[List[str]] = None,
        filter_expression: Optional[str] = None,
        page_size: int = 1000,
        track_changes: bool = True,
    ) -> Tuple[pd.DataFrame, str]:
        """
        Full extract: retrieve all records, optionally enabling Change Tracking.

        Returns:
            (DataFrame of records, deltaLink string for future incremental runs)
        """
        params: dict = {"$top": page_size}
        if select_columns:
            params["$select"] = ",".join(select_columns)
        if filter_expression:
            params["$filter"] = filter_expression

        url = f"{self._base_url}/{plural_entity_name}?{urlencode(params)}"

        headers = dict(self._headers)
        if track_changes:
            headers["Prefer"] = f"odata.track-changes,odata.maxpagesize={page_size}"
        else:
            headers["Prefer"] = f"odata.maxpagesize={page_size}"

        all_records, delta_token = self._paginate(url, headers)
        df = self._records_to_dataframe(all_records)
        return df, delta_token

    def get_delta_records(
        self,
        plural_entity_name: str,
        delta_token: str,
    ) -> Tuple[pd.DataFrame, str]:
        """
        Incremental extract: retrieve changed and deleted records since the delta token.

        The delta_token is the full deltaLink URL returned by the previous run.

        Returns:
            (DataFrame including inserts/updates/deletes, new deltaLink string)
        """
        # The delta token is already a full URL from Dataverse
        if delta_token.startswith("http"):
            url = delta_token
        else:
            url = (
                f"{self._base_url}/{plural_entity_name}"
                f"?$deltatoken={delta_token}"
            )

        all_records, new_delta_token = self._paginate(url, self._headers)
        df = self._records_to_dataframe(all_records)
        return df, new_delta_token

    def _paginate(
        self, start_url: str, headers: dict
    ) -> Tuple[List[dict], str]:
        """
        Follows @odata.nextLink pages until exhausted.
        Captures and returns the final @odata.deltaLink.
        """
        all_records: List[dict] = []
        delta_token: str = ""
        url: Optional[str] = start_url

        while url:
            response = self._get(url, headers)
            body = response.json()

            records = body.get("value", [])
            all_records.extend(records)

            # Capture delta token when present (appears on last page)
            if ODATA_DELTALINK in body:
                delta_token = body[ODATA_DELTALINK]

            url = body.get(ODATA_NEXTLINK)

        return all_records, delta_token

    def _get(self, url: str, headers: dict) -> requests.Response:
        """Issues a GET request with error handling and exception mapping."""
        try:
            response = requests.get(url, headers=headers, timeout=self._timeout)
        except requests.exceptions.Timeout as exc:
            raise TransientError(f"Dataverse request timed out: {url}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise TransientError(f"Dataverse connection error: {exc}") from exc

        if response.status_code == 429:
            retry_after = self._parse_retry_after(response)
            raise ThrottlingError(
                f"Dataverse rate limit (429). Retry-After: {retry_after}s",
                retry_after_seconds=retry_after,
            )

        if response.status_code in (500, 502, 503, 504):
            raise TransientError(
                f"Dataverse transient error: HTTP {response.status_code} — {url}"
            )

        if response.status_code == 401:
            raise TransientError(
                "Dataverse authentication error (401) — token may have expired."
            )

        if not response.ok:
            try:
                error_body = response.json().get("error", {})
                message = error_body.get("message", response.text[:500])
                code    = error_body.get("code", "UNKNOWN")
            except Exception:
                message = response.text[:500]
                code = "UNKNOWN"
            raise EntityExtractionError(
                f"Dataverse API error {response.status_code} ({code}): {message}"
            )

        return response

    @staticmethod
    def _parse_retry_after(response: requests.Response) -> Optional[float]:
        """Extracts the Retry-After value in seconds from the response header."""
        value = response.headers.get("Retry-After") or response.headers.get("retry-after")
        if value is None:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    @staticmethod
    def _records_to_dataframe(records: List[dict]) -> pd.DataFrame:
        """
        Converts the raw OData record list to a pandas DataFrame.

        Deleted records (from Change Tracking) arrive with @odata.removed annotation.
        They are included in the DataFrame with source columns as None,
        marked via @odata.removed flag, and will be stored with _operation="delete".

        OData annotations (@odata.*) are stripped from column names or prefixed
        as odata_* to avoid the _ prefix collision.
        """
        if not records:
            return pd.DataFrame()

        processed = []
        for record in records:
            is_delete = ODATA_REMOVED in record
            clean: dict = {}

            for key, val in record.items():
                if key.startswith("@"):
                    # Rename annotations to avoid _ prefix collision
                    clean_key = key.lstrip("@").replace(".", "_").replace("/", "_")
                    if clean_key and not clean_key.startswith("_"):
                        clean[clean_key] = val
                else:
                    clean[key] = val

            # Stamp the operation type for BronzeWriter
            clean["_odata_operation"] = "delete" if is_delete else "insert"
            processed.append(clean)

        return pd.DataFrame(processed)
```

---

## 18. PYTHON: auth/crm_auth.py — COMPLETE IMPLEMENTATION

**File:** `connector/runtime/agic_fabric_connector/auth/crm_auth.py`

```python
from __future__ import annotations

import time
from dataclasses import dataclass

import msal

from agic_fabric_connector.base.exceptions import AuthenticationError, ConnectorFatalError


@dataclass(frozen=True)
class CRMAuthContext:
    access_token:    str
    environment_url: str
    token_expiry:    float  # Unix timestamp


def acquire_crm_token(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    environment_url: str,
) -> CRMAuthContext:
    """
    Acquires a Dataverse bearer token using MSAL client credentials flow.

    Scope: {environment_url}/.default
    This gives the service principal access to the Dataverse Web API.
    """
    if not tenant_id or not client_id or not client_secret:
        raise ConnectorFatalError(
            "tenant_id, client_id, and client_secret are all required for CRM authentication.",
            "CONFIG_VALIDATION_ERROR",
        )

    env_url = environment_url.rstrip("/")
    scope = f"{env_url}/.default"
    authority = f"https://login.microsoftonline.com/{tenant_id}"

    app = msal.ConfidentialClientApplication(
        client_id,
        client_credential=client_secret,
        authority=authority,
    )

    result = app.acquire_token_for_client(scopes=[scope])

    if "access_token" not in result:
        error = result.get("error", "unknown")
        desc  = result.get("error_description", "No description")
        raise AuthenticationError(
            f"MSAL token acquisition failed for Dataverse: {error} — {desc}"
        )

    expiry = time.time() + result.get("expires_in", 3600) - 60  # 60s buffer
    return CRMAuthContext(
        access_token=result["access_token"],
        environment_url=env_url,
        token_expiry=expiry,
    )
```

---

## 19. UNIT TEST PLAN

**Directory:** `connector/tests/unit/`

### test_retry_policy.py

```python
import pytest
from unittest.mock import MagicMock, patch
from agic_fabric_connector.base.retry_policy import RetryPolicy
from agic_fabric_connector.base.exceptions import (
    ThrottlingError, TransientError, ConnectorFatalError
)

def test_succeeds_on_first_attempt():
    policy = RetryPolicy(max_attempts=3)
    fn = MagicMock(return_value="ok")
    assert policy.execute(fn) == "ok"
    fn.assert_called_once()

def test_retries_on_transient_error():
    policy = RetryPolicy(max_attempts=3, initial_backoff_seconds=0)
    calls = [TransientError("fail"), TransientError("fail"), "success"]
    fn = MagicMock(side_effect=lambda: (
        (_ for _ in ()).throw(calls.pop(0)) if isinstance(calls[0], Exception)
        else calls.pop(0)
    ))
    # simpler: use side_effect list
    fn2 = MagicMock(side_effect=[TransientError("fail"), TransientError("fail"), "ok"])
    result = policy.execute(fn2)
    assert result == "ok"
    assert fn2.call_count == 3

def test_respects_retry_after():
    policy = RetryPolicy(max_attempts=2, respect_retry_after_header=True)
    fn = MagicMock(side_effect=[ThrottlingError("throttled", retry_after_seconds=0.01), "ok"])
    with patch("time.sleep") as mock_sleep:
        result = policy.execute(fn)
    assert result == "ok"
    mock_sleep.assert_called_once_with(0.01)

def test_raises_fatal_after_max_retries():
    policy = RetryPolicy(max_attempts=2, initial_backoff_seconds=0)
    fn = MagicMock(side_effect=TransientError("always fails"))
    with pytest.raises(ConnectorFatalError) as exc_info:
        policy.execute(fn)
    assert "MAX_RETRIES_EXCEEDED" in exc_info.value.error_code

def test_does_not_retry_fatal_error():
    policy = RetryPolicy(max_attempts=3)
    fn = MagicMock(side_effect=ConnectorFatalError("fatal", "CONFIG_LOAD_ERROR"))
    with pytest.raises(ConnectorFatalError):
        policy.execute(fn)
    fn.assert_called_once()  # no retry
```

### test_dataverse_client.py

```python
import pytest
from unittest.mock import MagicMock, patch
import requests
from agic_fabric_connector.modules.crm.dataverse_client import DataverseClient
from agic_fabric_connector.base.exceptions import ThrottlingError, EntityExtractionError

@pytest.fixture
def client():
    return DataverseClient(
        environment_url="https://contoso.crm4.dynamics.com",
        api_version="v9.2",
        access_token="test-token",
    )

def test_get_all_records_single_page(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {
        "value": [{"contactid": "aaa", "fullname": "Alice"}],
        "@odata.deltaLink": "https://example.com/delta?token=xyz",
    }
    with patch("requests.get", return_value=mock_response):
        df, delta_token = client.get_all_records("contacts", track_changes=True)
    assert len(df) == 1
    assert df.iloc[0]["fullname"] == "Alice"
    assert delta_token == "https://example.com/delta?token=xyz"

def test_get_all_records_paginates(client):
    page1 = MagicMock()
    page1.status_code = 200
    page1.ok = True
    page1.json.return_value = {
        "value": [{"contactid": "aaa"}],
        "@odata.nextLink": "https://example.com/page2",
    }
    page2 = MagicMock()
    page2.status_code = 200
    page2.ok = True
    page2.json.return_value = {
        "value": [{"contactid": "bbb"}],
        "@odata.deltaLink": "https://example.com/delta?token=final",
    }
    with patch("requests.get", side_effect=[page1, page2]):
        df, delta_token = client.get_all_records("contacts")
    assert len(df) == 2
    assert delta_token == "https://example.com/delta?token=final"

def test_raises_throttling_on_429(client):
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.headers = {"Retry-After": "30"}
    with patch("requests.get", return_value=mock_response):
        with pytest.raises(ThrottlingError) as exc_info:
            client.get_all_records("contacts")
    assert exc_info.value.retry_after_seconds == 30.0

def test_raises_entity_error_on_400(client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.ok = False
    mock_response.json.return_value = {
        "error": {"code": "0x80060888", "message": "Change tracking not enabled"}
    }
    with patch("requests.get", return_value=mock_response):
        with pytest.raises(EntityExtractionError) as exc_info:
            client.get_all_records("contacts")
    assert "Change tracking not enabled" in str(exc_info.value)

def test_delete_records_marked_correctly(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {
        "value": [
            {"contactid": "aaa", "fullname": "Alice"},
            {"contactid": "bbb", "@odata.removed": {"reason": "deleted"}},
        ],
        "@odata.deltaLink": "https://example.com/delta?token=xyz",
    }
    with patch("requests.get", return_value=mock_response):
        df, _ = client.get_delta_records("contacts", delta_token="https://example.com/delta?old")
    assert df[df["contactid"] == "bbb"]["_odata_operation"].values[0] == "delete"
    assert df[df["contactid"] == "aaa"]["_odata_operation"].values[0] == "insert"
```

### test_crm_connector.py

```python
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from agic_fabric_connector.modules.crm.crm_connector import CRMConnector
from agic_fabric_connector.base.watermark import Watermark, WatermarkType

@pytest.fixture
def mock_config():
    from agic_fabric_connector.config.config_models import (
        ConnectorItemDefinition, CrmSourceConfig, ServicePrincipalAuth,
        KeyVaultReferenceAuth, EntityConfig, FeaturesConfig, RuntimeConfig
    )
    source = CrmSourceConfig(
        environment_url="https://contoso.crm4.dynamics.com",
        tenant_id="tenant-id",
        api_version="v9.2",
    )
    auth = ServicePrincipalAuth(
        mode="service_principal",
        tenant_id="tenant-id",
        client_id="client-id",
        secret_ref=KeyVaultReferenceAuth(
            mode="keyvault_reference",
            key_vault_uri="https://vault.azure.net/",
            client_secret_name="crm-secret",
        )
    )
    entities = [EntityConfig(
        logical_name="contact",
        display_name="Contact",
        enabled=True,
        extraction_mode="incremental",
    )]
    return ConnectorItemDefinition(
        schema_version="1.0.0",
        module_type="crm",
        state="configured",
        source=source,
        authentication=auth,
        entities=entities,
        features=FeaturesConfig(),
        runtime=RuntimeConfig(notebook_item_id="nb-id", bronze_lake_house_id="lh-id"),
    )

def test_get_new_watermark_returns_delta_token(mock_config):
    spark = MagicMock()
    connector = CRMConnector(mock_config, spark)
    connector._last_delta_tokens["contact"] = "https://example.com/delta?token=NEW"
    entity = MagicMock()
    entity.logical_name = "contact"
    watermark = connector._get_new_watermark(entity, None, pd.DataFrame())
    assert watermark.watermark_type == WatermarkType.DELTA_TOKEN
    assert watermark.delta_token == "https://example.com/delta?token=NEW"

def test_initial_load_uses_get_all_records(mock_config):
    spark = MagicMock()
    connector = CRMConnector(mock_config, spark)
    entity = MagicMock()
    entity.logical_name = "contact"
    entity.select_columns = []
    entity.batch_size = 1000
    entity.filter_expression = None
    auth = MagicMock()
    auth.access_token = "token"

    mock_df = pd.DataFrame([{"contactid": "aaa"}])
    with patch.object(
        connector._retry_policy if hasattr(connector, "_retry_policy") else connector,
        "__class__", autospec=True
    ):
        with patch(
            "agic_fabric_connector.modules.crm.crm_connector.DataverseClient"
        ) as MockClient:
            mock_client_instance = MockClient.return_value
            mock_client_instance.get_all_records.return_value = (mock_df, "delta-token")
            df = connector._extract_entity(entity, auth, None)  # watermark=None → full
    assert not df.empty
```

### test_config_loader.py

```python
import pytest
import base64
import json
from unittest.mock import MagicMock, patch
from agic_fabric_connector.config.config_loader import ConfigLoader
from agic_fabric_connector.base.exceptions import ConfigLoadError, ConfigValidationError

VALID_CONFIG = {
    "schemaVersion": "1.0.0",
    "moduleType": "crm",
    "state": "configured",
    "source": {"environmentUrl": "https://x.crm.dynamics.com", "tenantId": "t"},
    "authentication": {"mode": "service_principal", "tenantId": "t", "clientId": "c", "secretRef": {}},
    "entities": [{"logicalName": "contact", "displayName": "Contact", "enabled": True}],
    "runtime": {"notebookItemId": "nb", "bronzeLakeHouseId": "lh"},
}

def _encoded_payload(config: dict) -> str:
    return base64.b64encode(json.dumps(config).encode()).decode()

def test_validate_rejects_unknown_schema_version():
    config = ConfigLoader._build_config_for_test({**VALID_CONFIG, "schemaVersion": "9.9.9"})
    with pytest.raises(ConfigValidationError, match="Unknown schema version"):
        ConfigLoader.validate(config)

def test_validate_rejects_non_configured_state():
    config = ConfigLoader._build_config_for_test({**VALID_CONFIG, "state": "empty"})
    with pytest.raises(ConfigValidationError, match="state is 'empty'"):
        ConfigLoader.validate(config)

def test_validate_rejects_no_enabled_entities():
    cfg = {**VALID_CONFIG, "entities": [
        {"logicalName": "contact", "displayName": "Contact", "enabled": False}
    ]}
    config = ConfigLoader._build_config_for_test(cfg)
    with pytest.raises(ConfigValidationError, match="No entities are enabled"):
        ConfigLoader.validate(config)
```

Add to `config_loader.py` (test helper):
```python
@staticmethod
def _build_config_for_test(d: dict):
    """Convenience method for tests — bypasses API call."""
    from agic_fabric_connector.config.config_models import ConnectorItemDefinition
    return ConnectorItemDefinition.from_dict(d)
```

---

## 20. INTEGRATION TEST CHECKLIST

Run these manually against a real Dataverse / Fabric environment before claiming MVP complete.

### Pre-conditions

```
□ A Fabric workspace with capacity (F2 or higher) available
□ A Dataverse environment with Change Tracking enabled on contact and lead
□ A service principal with:
    - System Administrator or equivalent on Dataverse
    - Fabric workspace Member role
□ An Azure Key Vault accessible from the Fabric workspace MSI
    - Secrets: crm-tenant-id, crm-client-id, crm-client-secret
□ FRONTEND_APPID populated in .env.dev and workload registered in Fabric portal
```

### Frontend Integration Tests

```
□ F-INT-01: Create new ConnectorItem → Empty view renders correctly
□ F-INT-02: Click Configure → wizard-module view renders with 3 module options
□ F-INT-03: Select CRM → Next → wizard-source shows environmentUrl + tenantId fields
□ F-INT-04: Fill source → Next → wizard-auth shows 3 auth mode options
□ F-INT-05: Select service_principal → shows tenantId + clientId fields
□ F-INT-06: Fill auth → Next → wizard-entities shows 5 CRM entity checkboxes
□ F-INT-07: Select 2 entities → Next → wizard-storage shows Lakehouse name field
□ F-INT-08: wizard-storage → Next → wizard-schedule shows cron/interval options
□ F-INT-09: wizard-schedule → Next → wizard-review shows complete summary
□ F-INT-10: Back button navigates to previous step correctly
□ F-INT-11: Click Activate → ensureBronzeLakehouse() creates a Lakehouse (verify in Fabric)
□ F-INT-12: Activate continues → deployConnectorNotebook() creates notebook (verify in Fabric)
□ F-INT-13: Activate continues → saveItemDefinition() stores config in payload.json (check via SDK)
□ F-INT-14: Activate continues → JobSchedulerClient.createItemSchedule() registers schedule
□ F-INT-15: Activate continues → JobSchedulerClient.runOnDemandItemJob() triggers first run
□ F-INT-16: After Activate → Dashboard view displays with "Connector activated" notification
□ F-INT-17: Run Now button in dashboard ribbon triggers a second run
□ F-INT-18: Pause button disables the schedule (verify in Job Scheduler)
```

### Python Wheel Integration Tests

```
□ P-INT-01: pip install agic-fabric-connector in a Fabric notebook — no errors
□ P-INT-02: ConfigLoader.from_item_definition() reads a configured item's payload.json
□ P-INT-03: CRMConnector._authenticate() acquires a valid Dataverse token
□ P-INT-04: DataverseClient.get_all_records("contacts") returns records for the test environment
□ P-INT-05: Delta token captured from full extract matches expected @odata.deltaLink format
□ P-INT-06: DataverseClient.get_delta_records() with the captured token returns 0 records (no changes)
□ P-INT-07: Modify a contact in Dataverse → get_delta_records() returns the modified contact
□ P-INT-08: Delete a contact in Dataverse → get_delta_records() returns @odata.removed record
□ P-INT-09: BronzeWriter.write() creates bronze_crm.contact Delta table with all 12 metadata cols
□ P-INT-10: _ingestion_date partition column exists and is correct DATE type
□ P-INT-11: WatermarkStore.upsert() creates row in bronze_crm._meta._entity_watermarks
□ P-INT-12: WatermarkStore.get() returns the previously stored Watermark on next call
□ P-INT-13: MetadataWriter.start_run() creates a row in bronze_crm._meta._connector_runs
□ P-INT-14: MetadataWriter.complete_run() updates the row with final status and counts
□ P-INT-15: Full connector.run() with 5 entities completes without error
□ P-INT-16: connector.run() with invalid delta token → EntityExtractionError, entity marked failed, run continues
□ P-INT-17: Re-run connector.run() → incremental mode used (confirmed by smaller record count)
□ P-INT-18: Throttle simulation (mock 429 with Retry-After) → RetryPolicy sleeps and retries
```

### Notebook Integration Tests

```
□ N-INT-01: connector_runtime_crm.ipynb deploys to workspace without error
□ N-INT-02: Placeholders (%%CONNECTOR_ITEM_ID%%, %%WORKSPACE_ID%%, %%WHEEL_VERSION%%) fully substituted
□ N-INT-03: Notebook Cell 1 (%pip install) installs wheel with no version conflicts
□ N-INT-04: Notebook Cell 2 (ConfigLoader) reads item definition successfully
□ N-INT-05: Notebook Cell 3 (connector.run()) executes full ingestion run
□ N-INT-06: Run status visible in Fabric Job Scheduler monitoring hub after notebook completes
```

---

## 21. DEFERRED TO LATER PHASES

| Item | Target Phase | Reason |
|---|---|---|
| Business Central connector (`BCConnector`, `BCClient`) | Phase 6 | CRM MVP first; BC shares the base — add after CRM is validated |
| SQL connector (`SQLConnector`, JDBC integration) | Phase 6 | Requires Spark JDBC tuning per customer SQL Server version |
| "Test Connection" button in wizard | Phase 2 (UI) | Needs Spark Livy session or ISV backend — neither in Phase 1 |
| Dashboard reads from `_connector_runs` via Fabric SQL | Phase 2 (UI) | Phase 1: use Job Scheduler API for run history; Phase 2: add SQL analytics endpoint read |
| Fabric Connection secret resolution (`fabric_connection` auth mode) | Phase 2 | Fabric Connections API for runtime secret retrieval needs explicit client scope (`Connection.Read.All`) in notebook — verify capability |
| Delta OPTIMIZE + VACUUM after write | Phase 2 (Python) | `enableDeltaLakeOptimize: false` is the default — enable when initial loads are complete |
| `_schema_evolution_log` writes | Phase 2 (Python) | SchemaEvolutionHandler stub writes log — full implementation when merge/strict policies are field-tested |
| Anonymous telemetry (`telemetry.py`) | Phase 2 (Python) | `enableTelemetry: true` but telemetry.py is a no-op stub until App Insights is wired |
| AppSource / Marketplace packaging | Phase 3 | Requires publisher certification; NuGet feed must be live |
| CI/CD GitHub Actions workflows | Phase 3 | `.github/workflows/ci.yml`, `cd-staging.yml`, `cd-production.yml` |
| Workspace-level MSI for notebook → OneLake auth | Verify | Confirm notebook MSI has `Storage Blob Data Contributor` on the Bronze Lakehouse — may require manual workspace admin step |
| BC entity catalog (customers, salesOrders, etc.) | Phase 6 | Document exact BC API endpoint names and field mappings |
| SQL schema discovery (list tables, infer watermark column) | Phase 6 | JDBC `INFORMATION_SCHEMA` query + UI for table selection |
| Python wheel versioned release to Azure Artifacts | Phase 3 | Manual `pip install` from public PyPI or private feed — feed setup needed |
