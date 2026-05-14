# PHASE 4 — SCAFFOLDING PLAN

**Project:** Fabric Universal Connector  
**Author:** Principal Architect Review  
**Date:** 2026-05-14  
**Input:** `.ai/architecture/target-architecture.md`, `.ai/contracts/`  
**Status:** COMPLETE — Awaiting Phase 5 instruction

---

## TABLE OF CONTENTS

1. Scaffold Overview and Execution Order
2. Directory Structure to Create
3. Step 1 — Manifest: ConnectorItem.xml
4. Step 2 — Manifest: ConnectorItem.json
5. Step 3 — Manifest: Product.json (modifications)
6. Step 4 — Manifest i18n: translations.json (additions)
7. Step 5 — App.tsx (route addition)
8. Step 6 — ConnectorItemDefinition.ts
9. Step 7 — wizardState.ts
10. Step 8 — wizardValidation.ts
11. Step 9 — ConnectorItem.scss
12. Step 10 — ConnectorItemEmptyView.tsx
13. Step 11 — ConnectorItemRibbon.tsx + ribbonActionFactory.ts
14. Step 12 — Wizard Step Components (7 files)
15. Step 13 — Dashboard Components (5 files)
16. Step 14 — ConnectorItemEditor.tsx (main orchestrator)
17. Step 15 — UI i18n: translation.json (additions)
18. Step 16 — Item barrel export: index.ts
19. Step 17 — Controllers: NotebookDeploymentController.ts + LakehouseController.ts
20. Step 18 — Python Wheel: Directory Structure + pyproject.toml
21. Step 19 — Python Wheel: Core Module Files (skeletons)
22. Step 20 — Notebook Templates
23. Step 21 — Asset Placeholders
24. Dependency Graph
25. Validation Checklist

---

## 1. SCAFFOLD OVERVIEW AND EXECUTION ORDER

### Guiding Principles

Every file in this scaffold follows the conventions in `.ai/commands/item/createItem.md`:
- All views are registered as static arrays — no dynamic JSX switching
- `useViewNavigation()` is only called inside components that are children of `<ItemEditor>`
- `ribbon` prop is always a function: `ribbon={(context) => <ConnectorItemRibbon viewContext={context} ... />}`
- Wizard state lives in the editor component, NOT in item definition
- Item definition is only saved on the final Activate step
- Notifications use `RegisteredNotification[]` pattern
- The empty view wraps in a local component to access `useViewNavigation()`

### Execution Dependencies

```
Manifest files     → Product.json         → translations.json (manifest i18n)
ConnectorItemDefinition.ts → wizardState.ts → wizardValidation.ts
ConnectorItemEmptyView → ConnectorItemRibbon → Wizard* components → Dashboard* components → ConnectorItemEditor
translation.json (UI i18n) → all editor components that call t()
ConnectorItemEditor → index.ts → App.tsx
Controllers → ConnectorItemEditor (imported by Activate handler)
```

### Files Count Summary

| Category | Files |
|---|---|
| Manifest (Workload/Manifest/) | 2 new + 2 modified |
| TypeScript types | 3 |
| React components | 15 |
| Controllers | 2 |
| SCSS | 1 |
| i18n | 2 modified |
| Python wheel | ~20 skeleton files |
| Notebook templates | 3 |
| **Total new files** | **~48** |

---

## 2. DIRECTORY STRUCTURE TO CREATE

Run these `mkdir` commands in order before creating any files:

```powershell
# ── Manifest ─────────────────────────────────────────────────
New-Item -ItemType Directory -Force "Workload\Manifest\items\ConnectorItem"

# ── Frontend item ─────────────────────────────────────────────
New-Item -ItemType Directory -Force "Workload\app\items\ConnectorItem"
New-Item -ItemType Directory -Force "Workload\app\items\ConnectorItem\wizard"
New-Item -ItemType Directory -Force "Workload\app\items\ConnectorItem\dashboard"
New-Item -ItemType Directory -Force "Workload\app\items\ConnectorItem\ribbon"

# ── Assets ───────────────────────────────────────────────────
New-Item -ItemType Directory -Force "Workload\app\assets\items\ConnectorItem"

# ── Controllers ───────────────────────────────────────────────
# (Workload\app\controller\ already exists — no new directory needed)

# ── Python wheel ─────────────────────────────────────────────
New-Item -ItemType Directory -Force "connector\runtime\agic_fabric_connector\base"
New-Item -ItemType Directory -Force "connector\runtime\agic_fabric_connector\config"
New-Item -ItemType Directory -Force "connector\runtime\agic_fabric_connector\auth"
New-Item -ItemType Directory -Force "connector\runtime\agic_fabric_connector\modules\crm"
New-Item -ItemType Directory -Force "connector\runtime\agic_fabric_connector\modules\businesscentral"
New-Item -ItemType Directory -Force "connector\runtime\agic_fabric_connector\modules\sql"
New-Item -ItemType Directory -Force "connector\runtime\agic_fabric_connector\utils"
New-Item -ItemType Directory -Force "connector\runtime\notebooks"
New-Item -ItemType Directory -Force "connector\tests\unit"
New-Item -ItemType Directory -Force "connector\tests\integration"

# ── CI/CD ────────────────────────────────────────────────────
New-Item -ItemType Directory -Force ".github\workflows"
```

---

## 3. STEP 1 — MANIFEST: ConnectorItem.xml

**File:** `Workload/Manifest/items/ConnectorItem/ConnectorItem.xml`

Pattern: exact copy of `HelloWorldItem.xml` with `Connector` substituted for `HelloWorld`.

```xml
<?xml version='1.0' encoding='utf-8'?>
<ItemManifestConfiguration SchemaVersion="2.0.0">
  <Item TypeName="{{WORKLOAD_NAME}}.Connector" Category="Data">
    <Workload WorkloadName="{{WORKLOAD_NAME}}" />
  </Item>
</ItemManifestConfiguration>
```

---

## 4. STEP 2 — MANIFEST: ConnectorItem.json

**File:** `Workload/Manifest/items/ConnectorItem/ConnectorItem.json`

Pattern: based on `HelloWorldItem.json` — preserve all fields, substitute names.

```json
{
  "name": "Connector",
  "version": "1.100",
  "displayName": "ConnectorItem_DisplayName",
  "displayNamePlural": "ConnectorItem_DisplayName_Plural",
  "editor": {
    "path": "/ConnectorItem-editor"
  },
  "icon": {
    "name": "assets/images/ConnectorItem_Icon.png"
  },
  "activeIcon": {
    "name": "assets/images/ConnectorItem_Icon.png"
  },
  "contextMenuItems": [],
  "quickActionItems": [],
  "supportedInMonitoringHub": true,
  "supportedInDatahubL1": true,
  "editorTab": {
    "onDeactivate": "item.tab.onDeactivate",
    "canDeactivate": "item.tab.canDeactivate",
    "canDestroy": "item.tab.canDestroy",
    "onDestroy": "item.tab.onDestroy",
    "onDelete": "item.tab.onDelete"
  },
  "createItemDialogConfig": {
    "onCreationFailure": {
      "action": "item.onCreationFailure"
    },
    "onCreationSuccess": {
      "action": "item.onCreationSuccess"
    }
  }
}
```

**Critical:** `"name": "Connector"` must match the entry in `ITEM_NAMES=HelloWorld,Connector` in `.env.dev`.

---

## 5. STEP 3 — MANIFEST: Product.json (MODIFICATIONS)

**File:** `Workload/Manifest/Product.json` — modify in-place.

Add `Connector` to `recommendedItemTypes` and add a create card. The final file must look exactly like:

```json
{
    "name": "Product",
    "version": "1.100",
    "displayName": "Workload_Display_Name",
    "fullDisplayName": "Workload_Full_Display_Name",
    "description": "Workload_Description",
    "favicon": "assets/images/Workload_Icon.png",
    "icon": {
      "name": "assets/images/Workload_Icon.png"
    },
    "homePage": {
      "learningMaterials": [
        {
          "title": "Workload_Hub_GetStarted_1_Title",
          "introduction": "Workload_Hub_GetStarted_1_Sub_Title",
          "description": "Workload_Hub_GetStarted_1_Description",
          "image": "assets/images/Workload_Hub_GetStarted_1.png",
          "link": "https://aka.ms/get-started-learning-docs"
        }
      ],
      "newSection": {
        "customActions": []
      },
      "recommendedItemTypes": [
        "HelloWorld",
        "Connector"
      ]
    },
    "createExperience": {
      "description": "Workload_Description",
      "cards": [
        {
          "title": "HelloWorldItem_DisplayName",
          "description": "HelloWorldItem_Description",
          "icon": {
            "name": "assets/images/HelloWorldItem_Icon.png"
          },
          "icon_small": {
            "name": "assets/images/HelloWorldItem_Icon.png"
          },
          "availableIn": [
            "home",
            "create-hub",
            "workspace-plus-new",
            "workspace-plus-new-teams"
          ],
          "itemType": "HelloWorld",
          "createItemDialogConfig": {
            "onCreationFailure": { "action": "item.onCreationFailure" },
            "onCreationSuccess": { "action": "item.onCreationSuccess" }
          }
        },
        {
          "title": "ConnectorItem_DisplayName",
          "description": "ConnectorItem_Description",
          "icon": {
            "name": "assets/images/ConnectorItem_Icon.png"
          },
          "icon_small": {
            "name": "assets/images/ConnectorItem_Icon.png"
          },
          "availableIn": [
            "home",
            "create-hub",
            "workspace-plus-new",
            "workspace-plus-new-teams"
          ],
          "itemType": "Connector",
          "createItemDialogConfig": {
            "onCreationFailure": { "action": "item.onCreationFailure" },
            "onCreationSuccess": { "action": "item.onCreationSuccess" }
          }
        }
      ]
    },
    "productDetail": {
      "publisher": "Agic Technology srl",
      "slogan": "Workload_Hub_Slogan",
      "description": "Workload_Hub_Description",
      "image": {
        "mediaType": 0,
        "source": "assets/images/Workload_Hub_Banner.png"
      },
      "slideMedia": [
        {
          "mediaType": 1,
          "source": "https://youtube.com/embed/UNgpBOCvwa8?si=KwsR879MaVZd5CJi"
        },
        {
          "mediaType": 0,
          "source": "assets/images/Workload_Hub_SlideMedia_1.png"
        }
      ],
      "supportLink": {
        "documentation": {"url": "https://example.com/documentation"},
        "certification": {"url": "https://example.com/certification"},
        "help": {"url": "https://example.com/help"},
        "privacy": {"url": "https://example.com/privacy"},
        "terms": {"url": "https://example.com/terms"},
        "license": {"url": "https://azuremarketplace.microsoft.com"}
      }
    },
    "itemJobTypes": ["storeData", "others"],
    "compatibleItemTypes": ["Lakehouse"]
}
```

**Changes from current:** added `"Connector"` to `recommendedItemTypes`; added ConnectorItem card to `createExperience.cards`; changed publisher from `"Name of publisher"` to `"Agic Technology srl"`.

---

## 6. STEP 4 — MANIFEST i18n: translations.json (ADDITIONS)

**File:** `Workload/Manifest/assets/locales/en-US/translations.json` — add entries.

Append to the existing object:

```json
{
    "Workload_Display_Name": "Fabric Universal Connector",
    "Workload_Full_Display_Name": "Fabric Universal Connector",
    "Workload_Description": "Ingest data from Dataverse, Business Central, and SQL Server into your Fabric Bronze Lakehouse.",
    "Workload_Hub_Slogan": "Connect your enterprise data sources to Microsoft Fabric.",
    "Workload_Hub_Description": "Fabric Universal Connector enables metadata-driven, incremental ingestion from CRM (Dataverse/D365), Business Central, and SQL Server into your Fabric Bronze Lakehouse — no backend infrastructure required.",
    "Workload_Hub_GetStarted_1_Title": "Get Started",
    "Workload_Hub_GetStarted_1_Sub_Title": "Connect your first data source",
    "Workload_Hub_GetStarted_1_Description": "Create a Connector item and follow the 7-step wizard to configure your first ingestion pipeline.",
    "HelloWorldItem_DisplayName": "Hello World",
    "HelloWorldItem_DisplayName_Plural": "Hello Worlds",
    "HelloWorldItem_Description": "A Hello World Item to start your Dev Experience",
    "ConnectorItem_DisplayName": "Universal Connector",
    "ConnectorItem_DisplayName_Plural": "Universal Connectors",
    "ConnectorItem_Description": "Ingest data from Dataverse, Business Central, or SQL Server into your Bronze Lakehouse."
}
```

---

## 7. STEP 5 — App.tsx (ROUTE ADDITION)

**File:** `Workload/app/App.tsx` — add import and route.

### Import addition (after HelloWorldItemEditor import, line 5):

```typescript
import { ConnectorItemEditor } from "./items/ConnectorItem";
```

### Route addition (inside `<Switch>`, after the HelloWorldItem route):

```typescript
{/* Routings for the Connector Item Editor */}
<Route path="/ConnectorItem-editor/:itemObjectId">
    <ConnectorItemEditor
        workloadClient={workloadClient}
        data-testid="ConnectorItem-editor" />
</Route>
```

### Complete modified App.tsx:

```typescript
import React from "react";
import { Route, Router, Switch } from "react-router-dom";
import { History } from "history";
import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { HelloWorldItemEditor } from "./items/HelloWorldItem";
import { ConnectorItemEditor } from "./items/ConnectorItem";
import { ConditionalPlaygroundRoutes } from "./playground/ConditionalPlaygroundRoutes";

interface AppProps {
    history: History;
    workloadClient: WorkloadClientAPI;
}

export interface PageProps {
    workloadClient: WorkloadClientAPI;
    history?: History;
}

export interface ContextProps {
    itemObjectId?: string;
    workspaceObjectId?: string;
    source?: string;
}

export interface SharedState {
    message: string;
}

export function App({ history, workloadClient }: AppProps) {
    return <Router history={history}>
        <Route exact path="/">
            <div style={{ padding: '20px', backgroundColor: '#f0f0f0' }}>
                <h1>Workload is running!</h1>
                <p>Current URL: {window.location.href}</p>
                <p>Workload Name: {process.env.WORKLOAD_NAME}</p>
            </div>
        </Route>
        <Switch>
            <Route path="/HelloWorldItem-editor/:itemObjectId">
                <HelloWorldItemEditor
                    workloadClient={workloadClient}
                    data-testid="HelloWorldItem-editor" />
            </Route>

            <Route path="/ConnectorItem-editor/:itemObjectId">
                <ConnectorItemEditor
                    workloadClient={workloadClient}
                    data-testid="ConnectorItem-editor" />
            </Route>

            <ConditionalPlaygroundRoutes workloadClient={workloadClient} />
        </Switch>
    </Router>;
}
```

---

## 8. STEP 6 — ConnectorItemDefinition.ts

**File:** `Workload/app/items/ConnectorItem/ConnectorItemDefinition.ts`

This is the TypeScript representation of the JSON Schema defined in `.ai/contracts/config-schema.json`. These types drive all wizard state and editor state. Copy exactly from the TypeScript section of `.ai/contracts/ingestion-contracts.md` Section 12.

```typescript
export type ModuleType = "crm" | "businesscentral" | "sql";
export type ConnectorState = "empty" | "configured" | "error" | "paused";
export type SchemaEvolutionPolicy = "merge" | "strict" | "overwrite";
export type AuthMode = "fabric_connection" | "keyvault_reference" | "service_principal";
export type ExtractionMode = "incremental" | "full";
export type ConnectorRunStatus = "running" | "success" | "partial_success" | "failed" | "cancelled";
export type TriggeredBy = "schedule" | "on_demand" | "activation";
export type WatermarkType = "delta_token" | "timestamp" | "rowversion";

// ── Source configurations ──────────────────────────────────────

export interface CrmSourceConfiguration {
  environmentUrl: string;
  tenantId: string;
  apiVersion?: string;
  enableChangeTracking?: boolean;
  pageSize?: number;
}

export interface BusinessCentralSourceConfiguration {
  tenantId: string;
  environment: string;
  companyId?: string;
  apiVersion?: string;
  pageSize?: number;
}

export interface SqlSourceConfiguration {
  server: string;
  database: string;
  port?: number;
  driver?: "sqlserver" | "azuresql";
  encrypt?: boolean;
  trustServerCertificate?: boolean;
}

// ── Authentication ──────────────────────────────────────────────

export interface FabricConnectionAuth {
  mode: "fabric_connection";
  fabricConnectionId: string;
}

export interface KeyVaultReferenceAuth {
  mode: "keyvault_reference";
  keyVaultUri: string;
  clientIdSecretName?: string;
  clientSecretName: string;
  tenantIdSecretName?: string;
}

export interface ServicePrincipalAuth {
  mode: "service_principal";
  tenantId: string;
  clientId: string;
  secretRef: FabricConnectionAuth | KeyVaultReferenceAuth;
}

export type AuthConfiguration = FabricConnectionAuth | KeyVaultReferenceAuth | ServicePrincipalAuth;

// ── Entity configurations ───────────────────────────────────────

export interface CrmEntityConfiguration {
  logicalName: string;
  displayName: string;
  enabled: boolean;
  extractionMode?: ExtractionMode;
  selectColumns?: string[];
  expandRelationships?: string[];
  filterExpression?: string;
  batchSize?: number;
}

export interface BusinessCentralEntityConfiguration {
  apiEndpoint: string;
  displayName: string;
  enabled: boolean;
  extractionMode?: ExtractionMode;
  watermarkColumn?: string;
  selectColumns?: string[];
  filterExpression?: string;
  batchSize?: number;
}

export interface SqlEntityConfiguration {
  schema: string;
  tableName: string;
  displayName: string;
  enabled: boolean;
  extractionMode?: ExtractionMode;
  watermarkColumn?: string;
  watermarkColumnType?: "datetime" | "rowversion" | "integer";
  selectColumns?: string[];
  whereClause?: string;
  primaryKeys?: string[];
  fetchSize?: number;
}

// ── Storage / Schedule / Features / Runtime / Metadata ─────────

export interface StorageConfiguration {
  bronzeLakeHouseId?: string;
  bronzeLakeHouseName: string;
  schemaEvolutionPolicy?: SchemaEvolutionPolicy;
  retentionDays?: number;
  useExistingLakehouse?: boolean;
}

export interface SchedulingConfiguration {
  scheduleType: "cron" | "interval";
  cronExpression?: string;
  intervalMinutes?: number;
  timezone?: string;
  enabled: boolean;
  startDate?: string;
}

export interface FeaturesConfiguration {
  schemaEvolutionHandling?: SchemaEvolutionPolicy;
  errorThresholdPercent?: number;
  enablePartialRun?: boolean;
  enableTelemetry?: boolean;
  maxRecordsPerEntityPerRun?: number;
  enableDeltaLakeOptimize?: boolean;
}

export interface RuntimeConfiguration {
  notebookItemId?: string;
  bronzeLakeHouseId?: string;
  deployedAt?: string;
  wheelVersion?: string;
  configSchemaVersion?: string;
  jobScheduleId?: string;
}

export interface ConnectorMetadata {
  displayName?: string;
  description?: string;
  tags?: string[];
  createdAt?: string;
  updatedAt?: string;
  activatedAt?: string;
}

// ── Top-level discriminated union ───────────────────────────────

interface ConnectorItemDefinitionBase {
  schemaVersion: "1.0.0";
  state: ConnectorState;
  authentication?: AuthConfiguration;
  storage?: StorageConfiguration;
  scheduling?: SchedulingConfiguration;
  features?: FeaturesConfiguration;
  runtime?: RuntimeConfiguration;
  metadata?: ConnectorMetadata;
}

export interface CrmConnectorItemDefinition extends ConnectorItemDefinitionBase {
  moduleType: "crm";
  source: CrmSourceConfiguration;
  entities: CrmEntityConfiguration[];
}

export interface BusinessCentralConnectorItemDefinition extends ConnectorItemDefinitionBase {
  moduleType: "businesscentral";
  source: BusinessCentralSourceConfiguration;
  entities: BusinessCentralEntityConfiguration[];
}

export interface SqlConnectorItemDefinition extends ConnectorItemDefinitionBase {
  moduleType: "sql";
  source: SqlSourceConfiguration;
  entities: SqlEntityConfiguration[];
}

export type ConnectorItemDefinition =
  | CrmConnectorItemDefinition
  | BusinessCentralConnectorItemDefinition
  | SqlConnectorItemDefinition;

// ── Runtime metadata types (dashboard) ─────────────────────────

export interface EntityRunResult {
  entityName: string;
  status: "success" | "failed" | "skipped";
  recordsIngested: number;
  recordsFailed: number;
  durationSeconds: number;
  newWatermark: string | null;
  errorMessage: string | null;
}

export interface ConnectorRun {
  runId: string;
  connectorId: string;
  moduleType: ModuleType;
  runStartUtc: string;
  runEndUtc: string | null;
  durationSeconds: number | null;
  status: ConnectorRunStatus;
  triggeredBy: TriggeredBy;
  entitiesSucceeded: number;
  entitiesFailed: number;
  recordsIngested: number;
  errorMessage: string | null;
  entityResults: EntityRunResult[];
  wheelVersion: string;
}

export interface EntityWatermark {
  connectorId: string;
  entityName: string;
  watermarkType: WatermarkType;
  lastSuccessUtc: string;
  recordsAtLastRun: number;
  isInitialLoadComplete: boolean;
}

// ── Type guards ─────────────────────────────────────────────────

export function isCrmConnector(def: ConnectorItemDefinition): def is CrmConnectorItemDefinition {
  return def.moduleType === "crm";
}

export function isBusinessCentralConnector(def: ConnectorItemDefinition): def is BusinessCentralConnectorItemDefinition {
  return def.moduleType === "businesscentral";
}

export function isSqlConnector(def: ConnectorItemDefinition): def is SqlConnectorItemDefinition {
  return def.moduleType === "sql";
}

export function createEmptyDefinition(): Pick<ConnectorItemDefinitionBase, "schemaVersion" | "state"> {
  return { schemaVersion: "1.0.0", state: "empty" };
}
```

---

## 9. STEP 7 — wizardState.ts

**File:** `Workload/app/items/ConnectorItem/wizard/wizardState.ts`

```typescript
import {
  ModuleType,
  CrmSourceConfiguration,
  BusinessCentralSourceConfiguration,
  SqlSourceConfiguration,
  CrmEntityConfiguration,
  BusinessCentralEntityConfiguration,
  SqlEntityConfiguration,
  StorageConfiguration,
  SchedulingConfiguration,
} from "../ConnectorItemDefinition";

export const WIZARD_STEPS = {
  MODULE:    "wizard-module",
  SOURCE:    "wizard-source",
  AUTH:      "wizard-auth",
  ENTITIES:  "wizard-entities",
  STORAGE:   "wizard-storage",
  SCHEDULE:  "wizard-schedule",
  REVIEW:    "wizard-review",
} as const;

export type WizardStep = typeof WIZARD_STEPS[keyof typeof WIZARD_STEPS];

export const WIZARD_STEP_ORDER: WizardStep[] = [
  WIZARD_STEPS.MODULE,
  WIZARD_STEPS.SOURCE,
  WIZARD_STEPS.AUTH,
  WIZARD_STEPS.ENTITIES,
  WIZARD_STEPS.STORAGE,
  WIZARD_STEPS.SCHEDULE,
  WIZARD_STEPS.REVIEW,
];

export interface WizardAuthData {
  mode: "fabric_connection" | "keyvault_reference" | "service_principal" | null;
  fabricConnectionId?: string;
  keyVaultUri?: string;
  clientSecretName?: string;
  tenantId?: string;
  clientId?: string;
}

export interface WizardState {
  step: WizardStep;
  moduleType: ModuleType | null;
  source: Partial<CrmSourceConfiguration & BusinessCentralSourceConfiguration & SqlSourceConfiguration>;
  auth: WizardAuthData;
  selectedEntities: string[];
  storage: Partial<StorageConfiguration>;
  schedule: Partial<SchedulingConfiguration>;
  validationErrors: Record<string, string>;
  isActivating: boolean;
}

export const INITIAL_WIZARD_STATE: WizardState = {
  step: WIZARD_STEPS.MODULE,
  moduleType: null,
  source: {},
  auth: { mode: null },
  selectedEntities: [],
  storage: {
    bronzeLakeHouseName: "FabricUniversalConnector-Bronze",
    schemaEvolutionPolicy: "merge",
    useExistingLakehouse: false,
  },
  schedule: {
    scheduleType: "cron",
    cronExpression: "0 2 * * *",
    timezone: "UTC",
    enabled: true,
  },
  validationErrors: {},
  isActivating: false,
};

export function getNextStep(current: WizardStep): WizardStep | null {
  const idx = WIZARD_STEP_ORDER.indexOf(current);
  return idx < WIZARD_STEP_ORDER.length - 1 ? WIZARD_STEP_ORDER[idx + 1] : null;
}

export function getPrevStep(current: WizardStep): WizardStep | null {
  const idx = WIZARD_STEP_ORDER.indexOf(current);
  return idx > 0 ? WIZARD_STEP_ORDER[idx - 1] : null;
}
```

---

## 10. STEP 8 — wizardValidation.ts

**File:** `Workload/app/items/ConnectorItem/wizard/wizardValidation.ts`

```typescript
import { WizardState, WizardStep, WIZARD_STEPS } from "./wizardState";

export type ValidationResult = {
  isValid: boolean;
  errors: Record<string, string>;
};

export function validateStep(state: WizardState, step: WizardStep): ValidationResult {
  switch (step) {
    case WIZARD_STEPS.MODULE:   return validateModuleStep(state);
    case WIZARD_STEPS.SOURCE:   return validateSourceStep(state);
    case WIZARD_STEPS.AUTH:     return validateAuthStep(state);
    case WIZARD_STEPS.ENTITIES: return validateEntitiesStep(state);
    case WIZARD_STEPS.STORAGE:  return validateStorageStep(state);
    case WIZARD_STEPS.SCHEDULE: return validateScheduleStep(state);
    case WIZARD_STEPS.REVIEW:   return validateReviewStep(state);
    default:                    return { isValid: true, errors: {} };
  }
}

function validateModuleStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (!state.moduleType) errors.moduleType = "Please select a module type.";
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateSourceStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (state.moduleType === "crm") {
    if (!state.source.environmentUrl) errors.environmentUrl = "Environment URL is required.";
    if (!state.source.tenantId) errors.tenantId = "Tenant ID is required.";
  }
  if (state.moduleType === "businesscentral") {
    if (!state.source.tenantId) errors.tenantId = "Tenant ID is required.";
    if (!state.source.environment) errors.environment = "Environment name is required.";
  }
  if (state.moduleType === "sql") {
    if (!state.source.server) errors.server = "Server hostname is required.";
    if (!state.source.database) errors.database = "Database name is required.";
  }
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateAuthStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (!state.auth.mode) {
    errors.mode = "Please select an authentication method.";
    return { isValid: false, errors };
  }
  if (state.auth.mode === "fabric_connection" && !state.auth.fabricConnectionId) {
    errors.fabricConnectionId = "Please select a Fabric Connection.";
  }
  if (state.auth.mode === "keyvault_reference") {
    if (!state.auth.keyVaultUri) errors.keyVaultUri = "Key Vault URI is required.";
    if (!state.auth.clientSecretName) errors.clientSecretName = "Secret name is required.";
  }
  if (state.auth.mode === "service_principal") {
    if (!state.auth.tenantId) errors.tenantId = "Tenant ID is required.";
    if (!state.auth.clientId) errors.clientId = "Client ID is required.";
  }
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateEntitiesStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (state.selectedEntities.length === 0) {
    errors.entities = "At least one entity must be selected.";
  }
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateStorageStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (!state.storage.bronzeLakeHouseName) {
    errors.bronzeLakeHouseName = "Lakehouse name is required.";
  }
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateScheduleStep(state: WizardState): ValidationResult {
  const errors: Record<string, string> = {};
  if (!state.schedule.scheduleType) {
    errors.scheduleType = "Schedule type is required.";
  }
  if (state.schedule.scheduleType === "cron" && !state.schedule.cronExpression) {
    errors.cronExpression = "Cron expression is required.";
  }
  if (state.schedule.scheduleType === "interval" && !state.schedule.intervalMinutes) {
    errors.intervalMinutes = "Interval in minutes is required.";
  }
  return { isValid: Object.keys(errors).length === 0, errors };
}

function validateReviewStep(state: WizardState): ValidationResult {
  // All previous steps already validated; review step itself has no additional fields
  return { isValid: true, errors: {} };
}
```

---

## 11. STEP 9 — ConnectorItem.scss

**File:** `Workload/app/items/ConnectorItem/ConnectorItem.scss`

```scss
.connector-item-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.connector-wizard {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 24px;
  max-width: 720px;

  &__header {
    margin-bottom: 8px;
  }

  &__progress {
    margin-bottom: 24px;
  }

  &__actions {
    display: flex;
    gap: 8px;
    margin-top: 24px;
    justify-content: flex-end;
  }
}

.connector-dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  height: 100%;
}

.connector-dashboard__summary-cards {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.connector-dashboard__summary-card {
  flex: 1 1 160px;
  min-width: 140px;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--colorNeutralStroke1);
  background: var(--colorNeutralBackground1);
}

.entity-status-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 0;
}

.entity-status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
  cursor: pointer;
  
  &:hover {
    background: var(--colorNeutralBackground1Hover);
  }
}

.run-history-table {
  flex: 1;
  overflow: auto;
}
```

---

## 12. STEP 10 — ConnectorItemEmptyView.tsx

**File:** `Workload/app/items/ConnectorItem/ConnectorItemEmptyView.tsx`

Pattern: `HelloWorldItemEmptyView.tsx` — uses `ItemEditorEmptyView`, receives `onConfigure` callback.

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { ItemWithDefinition } from "../../controller/ItemCRUDController";
import { ItemEditorEmptyView, EmptyStateTask } from "../../components/ItemEditor";
import { ConnectorItemDefinition } from "./ConnectorItemDefinition";
import "./ConnectorItem.scss";

interface ConnectorItemEmptyViewProps {
  workloadClient: WorkloadClientAPI;
  item?: ItemWithDefinition<ConnectorItemDefinition>;
  onConfigure: () => void;
}

export function ConnectorItemEmptyView({
  item,
  onConfigure,
}: ConnectorItemEmptyViewProps) {
  const { t } = useTranslation();

  const tasks: EmptyStateTask[] = [
    {
      id: "configure",
      label: t("ConnectorItemEmptyView_ConfigureButton", "Configure Connector"),
      icon: undefined,
      description: t(
        "ConnectorItemEmptyView_ConfigureButton_Description",
        "Follow the 7-step wizard to connect your data source."
      ),
      onClick: onConfigure,
    },
  ];

  return (
    <ItemEditorEmptyView
      title={t("ConnectorItemEmptyView_Title", "Connect your data source")}
      description={t(
        "ConnectorItemEmptyView_Description",
        "Configure your connector to start ingesting data from Dataverse, Business Central, or SQL Server into your Fabric Bronze Lakehouse."
      )}
      imageSrc="/assets/items/ConnectorItem/EditorEmpty.svg"
      imageAlt="Connector empty state"
      tasks={tasks}
    />
  );
}
```

---

## 13. STEP 11 — ribbonActionFactory.ts + ConnectorItemRibbon.tsx

### ribbonActionFactory.ts

**File:** `Workload/app/items/ConnectorItem/ribbon/ribbonActionFactory.ts`

```typescript
import {
  Play24Regular,
  Pause24Regular,
  Settings24Regular,
  ArrowReset24Regular,
} from "@fluentui/react-icons";
import { RibbonAction } from "../../../components/ItemEditor";

export function createRunNowAction(onClick: () => Promise<void>, disabled: boolean): RibbonAction {
  return {
    key: "run-now",
    icon: Play24Regular,
    label: "Run Now",
    onClick,
    testId: "ribbon-run-now-btn",
    tooltip: "Trigger an immediate ingestion run",
    disabled,
  };
}

export function createPauseAction(onClick: () => Promise<void>, isPaused: boolean): RibbonAction {
  return {
    key: "pause-schedule",
    icon: Pause24Regular,
    label: isPaused ? "Resume" : "Pause",
    onClick,
    testId: "ribbon-pause-btn",
    tooltip: isPaused ? "Resume scheduled runs" : "Pause scheduled runs",
  };
}

export function createReconfigureAction(onClick: () => void): RibbonAction {
  return {
    key: "reconfigure",
    icon: Settings24Regular,
    label: "Reconfigure",
    onClick: async () => onClick(),
    testId: "ribbon-reconfigure-btn",
    tooltip: "Edit connector configuration",
  };
}

export function createResetWatermarkAction(onClick: () => Promise<void>): RibbonAction {
  return {
    key: "reset-watermark",
    icon: ArrowReset24Regular,
    label: "Reset Watermark",
    onClick,
    testId: "ribbon-reset-watermark-btn",
    tooltip: "Reset the change-tracking watermark — next run will perform a full extract",
  };
}
```

### ConnectorItemRibbon.tsx

**File:** `Workload/app/items/ConnectorItem/ribbon/ConnectorItemRibbon.tsx`

```typescript
import React from "react";
import { PageProps } from "../../../App";
import {
  Ribbon,
  RibbonAction,
  createSettingsAction,
} from "../../../components/ItemEditor";
import { ViewContext } from "../../../components";
import { ConnectorState } from "../ConnectorItemDefinition";
import { VIEWS } from "../ConnectorItemEditor";
import {
  createRunNowAction,
  createPauseAction,
  createReconfigureAction,
} from "./ribbonActionFactory";

export interface ConnectorItemRibbonProps extends PageProps {
  viewContext: ViewContext;
  connectorState: ConnectorState;
  isRunning: boolean;
  isSchedulePaused: boolean;
  onRunNow: () => Promise<void>;
  onPauseToggle: () => Promise<void>;
  onReconfigure: () => void;
  onOpenSettings: () => Promise<void>;
}

export function ConnectorItemRibbon({
  viewContext,
  connectorState,
  isRunning,
  isSchedulePaused,
  onRunNow,
  onPauseToggle,
  onReconfigure,
  onOpenSettings,
}: ConnectorItemRibbonProps) {
  const { currentView } = viewContext;
  const isDashboard = currentView === VIEWS.DASHBOARD;

  const homeActions: RibbonAction[] = isDashboard
    ? [
        createRunNowAction(onRunNow, isRunning),
        createPauseAction(onPauseToggle, isSchedulePaused),
        createReconfigureAction(onReconfigure),
        createSettingsAction(onOpenSettings),
      ]
    : [createSettingsAction(onOpenSettings)];

  return (
    <Ribbon
      homeToolbarActions={homeActions}
      additionalToolbars={[]}
      rightActionButtons={[]}
      viewContext={viewContext}
    />
  );
}
```

---

## 14. STEP 12 — WIZARD STEP COMPONENTS (7 FILES)

All wizard steps follow the same structural pattern: they receive `wizardState`, `onUpdate(patch)`, and `validationErrors` props. They render a form section. They do NOT call `setCurrentView` — navigation is handled by the parent editor via ribbon buttons.

### Common Wizard Step Props Interface

```typescript
// Used by all 7 wizard step components
export interface WizardStepProps {
  wizardState: WizardState;
  onUpdate: (patch: Partial<WizardState>) => void;
  validationErrors: Record<string, string>;
}
```

### WizardModuleStep.tsx

**File:** `Workload/app/items/ConnectorItem/wizard/WizardModuleStep.tsx`

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { Radio, RadioGroup, Label, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardModuleStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();

  return (
    <div className="connector-wizard">
      <div className="connector-wizard__header">
        <Text size={600} weight="semibold">
          {t("Wizard_Module_Title", "Select data source type")}
        </Text>
        <Text block>
          {t("Wizard_Module_Description", "Choose the source system you want to connect.")}
        </Text>
      </div>

      <RadioGroup
        value={wizardState.moduleType ?? ""}
        onChange={(_, data) => onUpdate({ moduleType: data.value as any, selectedEntities: [] })}
      >
        <Radio value="crm" label={t("Wizard_Module_CRM", "Microsoft Dataverse / Dynamics 365 CRM")} />
        <Radio value="businesscentral" label={t("Wizard_Module_BC", "Microsoft Dynamics 365 Business Central")} />
        <Radio value="sql" label={t("Wizard_Module_SQL", "SQL Server / Azure SQL")} />
      </RadioGroup>

      {validationErrors.moduleType && (
        <Text style={{ color: "var(--colorPaletteRedForeground1)" }}>
          {validationErrors.moduleType}
        </Text>
      )}
    </div>
  );
}
```

### WizardSourceStep.tsx

**File:** `Workload/app/items/ConnectorItem/wizard/WizardSourceStep.tsx`

Renders source fields specific to `wizardState.moduleType`. Shows different fields based on the selected module:
- CRM: `environmentUrl` (URL input), `tenantId` (text)
- BC: `tenantId` (text), `environment` (text), `companyId` (text, optional)
- SQL: `server` (text), `database` (text), `port` (number, default 1433)

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { Field, Input, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardSourceStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();
  const { moduleType, source } = wizardState;

  const updateSource = (patch: Record<string, unknown>) =>
    onUpdate({ source: { ...source, ...patch } });

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Source_Title", "Configure source")}
      </Text>

      {moduleType === "crm" && (
        <>
          <Field label={t("Wizard_Source_CRM_Url", "Environment URL")}
                 validationMessage={validationErrors.environmentUrl} required>
            <Input
              value={(source as any).environmentUrl ?? ""}
              placeholder="https://org.crm4.dynamics.com"
              onChange={(_, d) => updateSource({ environmentUrl: d.value })}
            />
          </Field>
          <Field label={t("Wizard_Source_TenantId", "Tenant ID")}
                 validationMessage={validationErrors.tenantId} required>
            <Input
              value={(source as any).tenantId ?? ""}
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              onChange={(_, d) => updateSource({ tenantId: d.value })}
            />
          </Field>
        </>
      )}

      {moduleType === "businesscentral" && (
        <>
          <Field label={t("Wizard_Source_TenantId", "Tenant ID")}
                 validationMessage={validationErrors.tenantId} required>
            <Input value={(source as any).tenantId ?? ""}
                   onChange={(_, d) => updateSource({ tenantId: d.value })} />
          </Field>
          <Field label={t("Wizard_Source_BC_Environment", "Environment")}
                 validationMessage={validationErrors.environment} required>
            <Input value={(source as any).environment ?? ""}
                   placeholder="Production"
                   onChange={(_, d) => updateSource({ environment: d.value })} />
          </Field>
          <Field label={t("Wizard_Source_BC_CompanyId", "Company ID (optional)")}>
            <Input value={(source as any).companyId ?? ""}
                   onChange={(_, d) => updateSource({ companyId: d.value })} />
          </Field>
        </>
      )}

      {moduleType === "sql" && (
        <>
          <Field label={t("Wizard_Source_SQL_Server", "Server")}
                 validationMessage={validationErrors.server} required>
            <Input value={(source as any).server ?? ""}
                   placeholder="server.database.windows.net"
                   onChange={(_, d) => updateSource({ server: d.value })} />
          </Field>
          <Field label={t("Wizard_Source_SQL_Database", "Database")}
                 validationMessage={validationErrors.database} required>
            <Input value={(source as any).database ?? ""}
                   onChange={(_, d) => updateSource({ database: d.value })} />
          </Field>
        </>
      )}
    </div>
  );
}
```

### WizardAuthStep.tsx

**File:** `Workload/app/items/ConnectorItem/wizard/WizardAuthStep.tsx`

Renders auth mode selector (Radio: Fabric Connection / Key Vault Reference / Service Principal) and the fields specific to each mode. Note: service principal mode always requires a secondary secret reference (nested FabricConnection or KeyVault).

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { Radio, RadioGroup, Field, Input, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardAuthStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();
  const { auth } = wizardState;

  const updateAuth = (patch: Partial<typeof auth>) =>
    onUpdate({ auth: { ...auth, ...patch } });

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Auth_Title", "Configure authentication")}
      </Text>

      <RadioGroup
        value={auth.mode ?? ""}
        onChange={(_, d) => updateAuth({ mode: d.value as any })}
      >
        <Radio value="fabric_connection"
               label={t("Wizard_Auth_FabricConnection", "Fabric Connection (Recommended)")} />
        <Radio value="keyvault_reference"
               label={t("Wizard_Auth_KeyVault", "Azure Key Vault Reference")} />
        <Radio value="service_principal"
               label={t("Wizard_Auth_ServicePrincipal", "Service Principal")} />
      </RadioGroup>

      {auth.mode === "fabric_connection" && (
        <Field label={t("Wizard_Auth_ConnectionId", "Fabric Connection ID")}
               validationMessage={validationErrors.fabricConnectionId} required>
          <Input value={auth.fabricConnectionId ?? ""}
                 placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                 onChange={(_, d) => updateAuth({ fabricConnectionId: d.value })} />
        </Field>
      )}

      {auth.mode === "keyvault_reference" && (
        <>
          <Field label={t("Wizard_Auth_KV_Uri", "Key Vault URI")}
                 validationMessage={validationErrors.keyVaultUri} required>
            <Input value={auth.keyVaultUri ?? ""}
                   placeholder="https://myvault.vault.azure.net/"
                   onChange={(_, d) => updateAuth({ keyVaultUri: d.value })} />
          </Field>
          <Field label={t("Wizard_Auth_KV_SecretName", "Client Secret Name")}
                 validationMessage={validationErrors.clientSecretName} required>
            <Input value={auth.clientSecretName ?? ""}
                   onChange={(_, d) => updateAuth({ clientSecretName: d.value })} />
          </Field>
        </>
      )}

      {auth.mode === "service_principal" && (
        <>
          <Field label={t("Wizard_Auth_SP_TenantId", "Tenant ID")}
                 validationMessage={validationErrors.tenantId} required>
            <Input value={auth.tenantId ?? ""}
                   onChange={(_, d) => updateAuth({ tenantId: d.value })} />
          </Field>
          <Field label={t("Wizard_Auth_SP_ClientId", "Client ID")}
                 validationMessage={validationErrors.clientId} required>
            <Input value={auth.clientId ?? ""}
                   onChange={(_, d) => updateAuth({ clientId: d.value })} />
          </Field>
          <Text size={300}>
            {t("Wizard_Auth_SP_SecretHint", "Client secret must be stored in a Fabric Connection or Key Vault — not entered here.")}
          </Text>
        </>
      )}
    </div>
  );
}
```

### WizardEntityStep.tsx

**File:** `Workload/app/items/ConnectorItem/wizard/WizardEntityStep.tsx`

Shows a checklist of available entities for the selected module. For CRM: uses `CRM_ENTITY_CATALOG` (5 Phase 1 entities). For BC/SQL: shows a text input to add entity names manually (Phase 1 simplification — no schema discovery yet).

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { Checkbox, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

const CRM_CATALOG = [
  { key: "contact",                    label: "Contact" },
  { key: "lead",                       label: "Lead" },
  { key: "msdynmkt_marketingform",     label: "Marketing Form" },
  { key: "msdynmkt_marketingemail",    label: "Marketing Email" },
  { key: "msdynmkt_customerjourney",   label: "Customer Journey" },
];

export function WizardEntityStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();
  const { moduleType, selectedEntities } = wizardState;

  const toggle = (key: string) => {
    const next = selectedEntities.includes(key)
      ? selectedEntities.filter((e) => e !== key)
      : [...selectedEntities, key];
    onUpdate({ selectedEntities: next });
  };

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Entities_Title", "Select entities to ingest")}
      </Text>

      {moduleType === "crm" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {CRM_CATALOG.map(({ key, label }) => (
            <Checkbox
              key={key}
              label={label}
              checked={selectedEntities.includes(key)}
              onChange={() => toggle(key)}
            />
          ))}
        </div>
      )}

      {(moduleType === "businesscentral" || moduleType === "sql") && (
        <Text>
          {t("Wizard_Entities_ManualNote",
            "Entity configuration for this module is set during the review step.")}
        </Text>
      )}

      {validationErrors.entities && (
        <Text style={{ color: "var(--colorPaletteRedForeground1)" }}>
          {validationErrors.entities}
        </Text>
      )}
    </div>
  );
}
```

### WizardStorageStep.tsx

**File:** `Workload/app/items/ConnectorItem/wizard/WizardStorageStep.tsx`

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { Field, Input, Switch, Radio, RadioGroup, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardStorageStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();
  const { storage } = wizardState;
  const update = (patch: Partial<typeof storage>) => onUpdate({ storage: { ...storage, ...patch } });

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Storage_Title", "Configure Bronze Lakehouse")}
      </Text>

      <Switch
        label={t("Wizard_Storage_UseExisting", "Use an existing Lakehouse")}
        checked={storage.useExistingLakehouse ?? false}
        onChange={(_, d) => update({ useExistingLakehouse: d.checked })}
      />

      <Field label={t("Wizard_Storage_LakehouseName", "Lakehouse Name")}
             validationMessage={validationErrors.bronzeLakeHouseName} required>
        <Input
          value={storage.bronzeLakeHouseName ?? "FabricUniversalConnector-Bronze"}
          onChange={(_, d) => update({ bronzeLakeHouseName: d.value })}
          disabled={storage.useExistingLakehouse}
        />
      </Field>

      <Field label={t("Wizard_Storage_SchemaPolicy", "Schema Evolution Policy")}>
        <RadioGroup
          value={storage.schemaEvolutionPolicy ?? "merge"}
          onChange={(_, d) => update({ schemaEvolutionPolicy: d.value as any })}
        >
          <Radio value="merge"
                 label={t("Wizard_Storage_Policy_Merge", "Merge (Recommended — adds new columns)")} />
          <Radio value="strict"
                 label={t("Wizard_Storage_Policy_Strict", "Strict (Fail on any schema change)")} />
        </RadioGroup>
      </Field>
    </div>
  );
}
```

### WizardScheduleStep.tsx

**File:** `Workload/app/items/ConnectorItem/wizard/WizardScheduleStep.tsx`

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { Field, Input, Radio, RadioGroup, Text } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardScheduleStep({ wizardState, onUpdate, validationErrors }: WizardStepProps) {
  const { t } = useTranslation();
  const { schedule } = wizardState;
  const update = (patch: Partial<typeof schedule>) => onUpdate({ schedule: { ...schedule, ...patch } });

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Schedule_Title", "Configure ingestion schedule")}
      </Text>

      <RadioGroup
        value={schedule.scheduleType ?? "cron"}
        onChange={(_, d) => update({ scheduleType: d.value as any })}
      >
        <Radio value="cron" label={t("Wizard_Schedule_Cron", "Cron expression")} />
        <Radio value="interval" label={t("Wizard_Schedule_Interval", "Fixed interval")} />
      </RadioGroup>

      {schedule.scheduleType === "cron" && (
        <Field label={t("Wizard_Schedule_CronExpr", "Cron Expression")}
               hint={t("Wizard_Schedule_CronHint", "e.g. 0 2 * * * (daily at 02:00 UTC)")}
               validationMessage={validationErrors.cronExpression} required>
          <Input
            value={schedule.cronExpression ?? "0 2 * * *"}
            onChange={(_, d) => update({ cronExpression: d.value })}
          />
        </Field>
      )}

      {schedule.scheduleType === "interval" && (
        <Field label={t("Wizard_Schedule_IntervalMinutes", "Interval (minutes)")}
               hint={t("Wizard_Schedule_IntervalHint", "Minimum 15 minutes")}
               validationMessage={validationErrors.intervalMinutes} required>
          <Input
            type="number"
            value={String(schedule.intervalMinutes ?? 60)}
            onChange={(_, d) => update({ intervalMinutes: parseInt(d.value, 10) })}
          />
        </Field>
      )}

      <Field label={t("Wizard_Schedule_Timezone", "Timezone")}>
        <Input
          value={schedule.timezone ?? "UTC"}
          onChange={(_, d) => update({ timezone: d.value })}
        />
      </Field>
    </div>
  );
}
```

### WizardReviewStep.tsx

**File:** `Workload/app/items/ConnectorItem/wizard/WizardReviewStep.tsx`

Shows a read-only summary of all wizard choices before Activate. Groups: Module, Source, Auth, Entities, Storage, Schedule.

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { Text, Badge, Divider } from "@fluentui/react-components";
import { WizardStepProps } from "./wizardState";

export function WizardReviewStep({ wizardState }: WizardStepProps) {
  const { t } = useTranslation();
  const { moduleType, source, auth, selectedEntities, storage, schedule } = wizardState;

  const row = (label: string, value: string) => (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0" }}>
      <Text weight="semibold">{label}</Text>
      <Text>{value || "—"}</Text>
    </div>
  );

  return (
    <div className="connector-wizard">
      <Text size={600} weight="semibold" block className="connector-wizard__header">
        {t("Wizard_Review_Title", "Review & Activate")}
      </Text>
      <Text block>
        {t("Wizard_Review_Description",
          "Review your configuration. Click Activate to deploy the connector and start the first ingestion run.")}
      </Text>

      <Divider>{t("Wizard_Review_Module", "Module")}</Divider>
      {row("Type", moduleType ?? "")}

      <Divider>{t("Wizard_Review_Source", "Source")}</Divider>
      {Object.entries(source).map(([k, v]) => row(k, String(v ?? "")))}

      <Divider>{t("Wizard_Review_Auth", "Authentication")}</Divider>
      {row("Mode", auth.mode ?? "")}

      <Divider>{t("Wizard_Review_Entities", "Entities")}</Divider>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
        {selectedEntities.map((e) => <Badge key={e} appearance="filled">{e}</Badge>)}
      </div>

      <Divider>{t("Wizard_Review_Storage", "Storage")}</Divider>
      {row("Lakehouse", storage.bronzeLakeHouseName ?? "")}
      {row("Schema Policy", storage.schemaEvolutionPolicy ?? "merge")}

      <Divider>{t("Wizard_Review_Schedule", "Schedule")}</Divider>
      {row("Type", schedule.scheduleType ?? "")}
      {schedule.scheduleType === "cron" && row("Expression", schedule.cronExpression ?? "")}
      {schedule.scheduleType === "interval" && row("Every (min)", String(schedule.intervalMinutes ?? ""))}
      {row("Timezone", schedule.timezone ?? "UTC")}
    </div>
  );
}
```

---

## 15. STEP 13 — DASHBOARD COMPONENTS (5 FILES)

### ConnectorDashboard.tsx

**File:** `Workload/app/items/ConnectorItem/dashboard/ConnectorDashboard.tsx`

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { Text, Spinner } from "@fluentui/react-components";
import { ItemEditorDefaultView } from "../../../components/ItemEditor";
import { ConnectorRun, EntityWatermark } from "../ConnectorItemDefinition";
import { RunHistoryTable } from "./RunHistoryTable";
import { EntityStatusList } from "./EntityStatusList";
import "../ConnectorItem.scss";

interface ConnectorDashboardProps {
  runs: ConnectorRun[];
  watermarks: EntityWatermark[];
  isLoading: boolean;
  onRunClick: (runId: string) => void;
  onEntityClick: (entityName: string) => void;
}

export function ConnectorDashboard({
  runs,
  watermarks,
  isLoading,
  onRunClick,
  onEntityClick,
}: ConnectorDashboardProps) {
  const { t } = useTranslation();
  const lastRun = runs[0] ?? null;

  return (
    <ItemEditorDefaultView
      left={{
        title: t("Dashboard_Entities_Title", "Entities"),
        width: 260,
        collapsible: true,
        content: (
          <EntityStatusList
            watermarks={watermarks}
            onEntityClick={onEntityClick}
          />
        ),
      }}
      center={{
        content: isLoading ? (
          <Spinner label={t("Dashboard_Loading", "Loading run history...")} />
        ) : (
          <div className="connector-dashboard">
            <div className="connector-dashboard__summary-cards">
              <div className="connector-dashboard__summary-card">
                <Text size={200}>{t("Dashboard_LastRun", "Last Run")}</Text>
                <Text size={500} weight="semibold" block>
                  {lastRun?.status ?? t("Dashboard_NoRuns", "Never")}
                </Text>
              </div>
              <div className="connector-dashboard__summary-card">
                <Text size={200}>{t("Dashboard_RecordsIngested", "Records (last run)")}</Text>
                <Text size={500} weight="semibold" block>
                  {lastRun?.recordsIngested?.toLocaleString() ?? "—"}
                </Text>
              </div>
            </div>
            <RunHistoryTable runs={runs} onRunClick={onRunClick} />
          </div>
        ),
      }}
    />
  );
}
```

### RunHistoryTable.tsx

**File:** `Workload/app/items/ConnectorItem/dashboard/RunHistoryTable.tsx`

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import {
  DataGrid,
  DataGridHeader,
  DataGridHeaderCell,
  DataGridBody,
  DataGridRow,
  DataGridCell,
  TableColumnDefinition,
  createTableColumn,
  TableCellLayout,
  Badge,
} from "@fluentui/react-components";
import { ConnectorRun, ConnectorRunStatus } from "../ConnectorItemDefinition";

interface RunHistoryTableProps {
  runs: ConnectorRun[];
  onRunClick: (runId: string) => void;
}

function statusBadgeColor(status: ConnectorRunStatus) {
  switch (status) {
    case "success":         return "success";
    case "partial_success": return "warning";
    case "failed":          return "danger";
    case "running":         return "informative";
    default:                return "subtle";
  }
}

export function RunHistoryTable({ runs, onRunClick }: RunHistoryTableProps) {
  const { t } = useTranslation();

  const columns: TableColumnDefinition<ConnectorRun>[] = [
    createTableColumn<ConnectorRun>({
      columnId: "status",
      renderHeaderCell: () => t("RunHistory_Status", "Status"),
      renderCell: (run) => (
        <TableCellLayout>
          <Badge color={statusBadgeColor(run.status) as any} appearance="filled">
            {run.status}
          </Badge>
        </TableCellLayout>
      ),
    }),
    createTableColumn<ConnectorRun>({
      columnId: "startTime",
      renderHeaderCell: () => t("RunHistory_Started", "Started"),
      renderCell: (run) => (
        <TableCellLayout>
          {new Date(run.runStartUtc).toLocaleString()}
        </TableCellLayout>
      ),
    }),
    createTableColumn<ConnectorRun>({
      columnId: "duration",
      renderHeaderCell: () => t("RunHistory_Duration", "Duration"),
      renderCell: (run) => (
        <TableCellLayout>
          {run.durationSeconds != null ? `${run.durationSeconds}s` : "—"}
        </TableCellLayout>
      ),
    }),
    createTableColumn<ConnectorRun>({
      columnId: "records",
      renderHeaderCell: () => t("RunHistory_Records", "Records"),
      renderCell: (run) => (
        <TableCellLayout>{run.recordsIngested.toLocaleString()}</TableCellLayout>
      ),
    }),
    createTableColumn<ConnectorRun>({
      columnId: "triggeredBy",
      renderHeaderCell: () => t("RunHistory_TriggeredBy", "Triggered By"),
      renderCell: (run) => <TableCellLayout>{run.triggeredBy}</TableCellLayout>,
    }),
  ];

  return (
    <DataGrid
      items={runs}
      columns={columns}
      getRowId={(run) => run.runId}
      onRowClick={(_, run) => onRunClick(run.runId)}
      className="run-history-table"
    >
      <DataGridHeader>
        <DataGridRow>
          {({ renderHeaderCell }) => (
            <DataGridHeaderCell>{renderHeaderCell()}</DataGridHeaderCell>
          )}
        </DataGridRow>
      </DataGridHeader>
      <DataGridBody<ConnectorRun>>
        {({ item, rowId }) => (
          <DataGridRow<ConnectorRun> key={rowId} style={{ cursor: "pointer" }}>
            {({ renderCell }) => <DataGridCell>{renderCell(item)}</DataGridCell>}
          </DataGridRow>
        )}
      </DataGridBody>
    </DataGrid>
  );
}
```

### EntityStatusList.tsx

**File:** `Workload/app/items/ConnectorItem/dashboard/EntityStatusList.tsx`

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { Text, Badge } from "@fluentui/react-components";
import { EntityWatermark } from "../ConnectorItemDefinition";
import "../ConnectorItem.scss";

interface EntityStatusListProps {
  watermarks: EntityWatermark[];
  onEntityClick: (entityName: string) => void;
}

export function EntityStatusList({ watermarks, onEntityClick }: EntityStatusListProps) {
  const { t } = useTranslation();

  if (watermarks.length === 0) {
    return (
      <Text size={200} style={{ padding: 8 }}>
        {t("EntityList_Empty", "No entities configured.")}
      </Text>
    );
  }

  return (
    <div className="entity-status-list">
      {watermarks.map((w) => (
        <div
          key={w.entityName}
          className="entity-status-item"
          onClick={() => onEntityClick(w.entityName)}
        >
          <Badge
            color={w.isInitialLoadComplete ? "success" : "informative"}
            appearance="filled"
            size="small"
          />
          <Text size={300}>{w.entityName}</Text>
        </div>
      ))}
    </div>
  );
}
```

### RunDetailView.tsx

**File:** `Workload/app/items/ConnectorItem/dashboard/RunDetailView.tsx`

Receives `runId` from `useViewNavigation()` params. Finds the matching `ConnectorRun` and renders entity result breakdown.

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { Text, Table, TableRow, TableCell, TableBody, TableHeader, TableHeaderCell } from "@fluentui/react-components";
import { ConnectorRun } from "../ConnectorItemDefinition";

interface RunDetailViewProps {
  runs: ConnectorRun[];
  runId: string | null;
}

export function RunDetailView({ runs, runId }: RunDetailViewProps) {
  const { t } = useTranslation();
  const run = runs.find((r) => r.runId === runId);

  if (!run) return <Text>{t("RunDetail_NotFound", "Run not found.")}</Text>;

  return (
    <div style={{ padding: 16 }}>
      <Text size={600} weight="semibold" block>
        {t("RunDetail_Title", "Run Details")} — {run.status}
      </Text>
      <Text block>{t("RunDetail_Started", "Started")}: {new Date(run.runStartUtc).toLocaleString()}</Text>
      {run.errorMessage && (
        <Text block style={{ color: "var(--colorPaletteRedForeground1)" }}>
          {t("RunDetail_Error", "Error")}: {run.errorMessage}
        </Text>
      )}

      <Table style={{ marginTop: 16 }}>
        <TableHeader>
          <TableRow>
            <TableHeaderCell>{t("RunDetail_Entity", "Entity")}</TableHeaderCell>
            <TableHeaderCell>{t("RunDetail_Status", "Status")}</TableHeaderCell>
            <TableHeaderCell>{t("RunDetail_Records", "Records")}</TableHeaderCell>
            <TableHeaderCell>{t("RunDetail_Duration", "Duration")}</TableHeaderCell>
            <TableHeaderCell>{t("RunDetail_Error", "Error")}</TableHeaderCell>
          </TableRow>
        </TableHeader>
        <TableBody>
          {run.entityResults.map((er) => (
            <TableRow key={er.entityName}>
              <TableCell>{er.entityName}</TableCell>
              <TableCell>{er.status}</TableCell>
              <TableCell>{er.recordsIngested.toLocaleString()}</TableCell>
              <TableCell>{er.durationSeconds}s</TableCell>
              <TableCell>{er.errorMessage ?? "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

### EntityDetailView.tsx

**File:** `Workload/app/items/ConnectorItem/dashboard/EntityDetailView.tsx`

```typescript
import React from "react";
import { useTranslation } from "react-i18next";
import { Text } from "@fluentui/react-components";
import { EntityWatermark } from "../ConnectorItemDefinition";

interface EntityDetailViewProps {
  watermarks: EntityWatermark[];
  entityName: string | null;
}

export function EntityDetailView({ watermarks, entityName }: EntityDetailViewProps) {
  const { t } = useTranslation();
  const watermark = watermarks.find((w) => w.entityName === entityName);

  if (!watermark) return <Text>{t("EntityDetail_NotFound", "Entity not found.")}</Text>;

  return (
    <div style={{ padding: 16 }}>
      <Text size={600} weight="semibold" block>
        {watermark.entityName}
      </Text>
      <Text block>{t("EntityDetail_LastSuccess", "Last Success")}: {new Date(watermark.lastSuccessUtc).toLocaleString()}</Text>
      <Text block>{t("EntityDetail_Records", "Records (last run)")}: {watermark.recordsAtLastRun.toLocaleString()}</Text>
      <Text block>{t("EntityDetail_WatermarkType", "Watermark Type")}: {watermark.watermarkType}</Text>
      <Text block>{t("EntityDetail_InitialLoad", "Initial Load Complete")}: {watermark.isInitialLoadComplete ? "Yes" : "No"}</Text>
    </div>
  );
}
```

---

## 16. STEP 14 — ConnectorItemEditor.tsx (MAIN ORCHESTRATOR)

**File:** `Workload/app/items/ConnectorItem/ConnectorItemEditor.tsx`

This is the largest file and the integration point for all sub-components. Pattern: `HelloWorldItemEditor.tsx` with wizard state machine added.

```typescript
import React, { useEffect, useState } from "react";
import { useParams, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { PageProps, ContextProps } from "../../App";
import {
  ItemWithDefinition,
  getWorkloadItem,
  saveItemDefinition,
} from "../../controller/ItemCRUDController";
import { callOpenSettings } from "../../controller/SettingsController";
import {
  ItemEditor,
  useViewNavigation,
  RegisteredNotification,
} from "../../components/ItemEditor";
import { JobSchedulerClient } from "../../clients/JobSchedulerClient";
import {
  ConnectorItemDefinition,
  ConnectorRun,
  EntityWatermark,
} from "./ConnectorItemDefinition";
import { ConnectorItemEmptyView } from "./ConnectorItemEmptyView";
import { ConnectorItemRibbon } from "./ribbon/ConnectorItemRibbon";
import { WizardModuleStep } from "./wizard/WizardModuleStep";
import { WizardSourceStep } from "./wizard/WizardSourceStep";
import { WizardAuthStep } from "./wizard/WizardAuthStep";
import { WizardEntityStep } from "./wizard/WizardEntityStep";
import { WizardStorageStep } from "./wizard/WizardStorageStep";
import { WizardScheduleStep } from "./wizard/WizardScheduleStep";
import { WizardReviewStep } from "./wizard/WizardReviewStep";
import { ConnectorDashboard } from "./dashboard/ConnectorDashboard";
import { RunDetailView } from "./dashboard/RunDetailView";
import { EntityDetailView } from "./dashboard/EntityDetailView";
import {
  WizardState,
  INITIAL_WIZARD_STATE,
  WIZARD_STEPS,
  validateStep,
  getNextStep,
  getPrevStep,
} from "./wizard/wizardState";
import "./ConnectorItem.scss";

export const VIEWS = {
  EMPTY:            "empty",
  WIZARD_MODULE:    WIZARD_STEPS.MODULE,
  WIZARD_SOURCE:    WIZARD_STEPS.SOURCE,
  WIZARD_AUTH:      WIZARD_STEPS.AUTH,
  WIZARD_ENTITIES:  WIZARD_STEPS.ENTITIES,
  WIZARD_STORAGE:   WIZARD_STEPS.STORAGE,
  WIZARD_SCHEDULE:  WIZARD_STEPS.SCHEDULE,
  WIZARD_REVIEW:    WIZARD_STEPS.REVIEW,
  DASHBOARD:        "dashboard",
  RUN_DETAIL:       "run-detail",
  ENTITY_DETAIL:    "entity-detail",
} as const;

export function ConnectorItemEditor({ workloadClient }: PageProps) {
  const pageContext = useParams<ContextProps>();
  const { pathname } = useLocation();
  const { t } = useTranslation();

  const [isLoading, setIsLoading] = useState(true);
  const [item, setItem] = useState<ItemWithDefinition<ConnectorItemDefinition>>();
  const [viewSetter, setViewSetter] = useState<((view: string) => void) | null>(null);
  const [wizardState, setWizardState] = useState<WizardState>(INITIAL_WIZARD_STATE);
  const [activationSuccess, setActivationSuccess] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [isSchedulePaused, setIsSchedulePaused] = useState(false);
  const [runs, setRuns] = useState<ConnectorRun[]>([]);
  const [watermarks, setWatermarks] = useState<EntityWatermark[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedEntityName, setSelectedEntityName] = useState<string | null>(null);

  async function loadItem(): Promise<void> {
    if (pageContext.itemObjectId && item && item.id === pageContext.itemObjectId) return;
    setIsLoading(true);
    try {
      const loaded = await getWorkloadItem<ConnectorItemDefinition>(
        workloadClient,
        pageContext.itemObjectId
      );
      setItem(loaded);
    } catch {
      setItem(undefined);
    }
    setIsLoading(false);
  }

  useEffect(() => { loadItem(); }, [pageContext, pathname]);

  useEffect(() => {
    if (!isLoading && item && viewSetter) {
      const state = (item.definition as any)?.state;
      viewSetter(state === "configured" || state === "paused" ? VIEWS.DASHBOARD : VIEWS.EMPTY);
    }
  }, [isLoading, item, viewSetter]);

  const updateWizard = (patch: Partial<WizardState>) =>
    setWizardState((prev) => ({ ...prev, ...patch }));

  async function handleActivate(): Promise<void> {
    // Activation implemented in Phase 5 — placeholder for now
    console.log("Activate:", wizardState);
  }

  async function handleRunNow(): Promise<void> {
    if (!item) return;
    setIsRunning(true);
    try {
      const scheduler = new JobSchedulerClient(workloadClient);
      await scheduler.runOnDemandItemJob(item.workspaceId, item.id, "ConnectorIngestionJob");
    } finally {
      setIsRunning(false);
    }
  }

  async function handlePauseToggle(): Promise<void> {
    setIsSchedulePaused((prev) => !prev);
  }

  // ── Wrapper components for views that need useViewNavigation ──

  const EmptyViewWrapper = () => {
    const { setCurrentView } = useViewNavigation();
    return (
      <ConnectorItemEmptyView
        workloadClient={workloadClient}
        item={item}
        onConfigure={() => {
          setWizardState(INITIAL_WIZARD_STATE);
          setCurrentView(VIEWS.WIZARD_MODULE);
        }}
      />
    );
  };

  const DashboardWrapper = () => {
    const { setCurrentView } = useViewNavigation();
    return (
      <ConnectorDashboard
        runs={runs}
        watermarks={watermarks}
        isLoading={isLoading}
        onRunClick={(runId) => {
          setSelectedRunId(runId);
          setCurrentView(VIEWS.RUN_DETAIL);
        }}
        onEntityClick={(entityName) => {
          setSelectedEntityName(entityName);
          setCurrentView(VIEWS.ENTITY_DETAIL);
        }}
      />
    );
  };

  // ── Static view array ─────────────────────────────────────────

  const views = [
    { name: VIEWS.EMPTY, component: <EmptyViewWrapper /> },

    {
      name: VIEWS.WIZARD_MODULE,
      component: <WizardModuleStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_SOURCE,
      component: <WizardSourceStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_AUTH,
      component: <WizardAuthStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_ENTITIES,
      component: <WizardEntityStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_STORAGE,
      component: <WizardStorageStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_SCHEDULE,
      component: <WizardScheduleStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },
    {
      name: VIEWS.WIZARD_REVIEW,
      component: <WizardReviewStep wizardState={wizardState} onUpdate={updateWizard}
                    validationErrors={wizardState.validationErrors} />,
    },

    { name: VIEWS.DASHBOARD, component: <DashboardWrapper /> },

    {
      name: VIEWS.RUN_DETAIL,
      component: <RunDetailView runs={runs} runId={selectedRunId} />,
      isDetailView: true,
    },
    {
      name: VIEWS.ENTITY_DETAIL,
      component: <EntityDetailView watermarks={watermarks} entityName={selectedEntityName} />,
      isDetailView: true,
    },
  ];

  // ── Notifications ─────────────────────────────────────────────

  const notifications: RegisteredNotification[] = [
    {
      name: "activation-success",
      showInViews: [VIEWS.DASHBOARD],
      component: activationSuccess ? (
        <div>{t("ConnectorItem_ActivationSuccess", "Connector activated. First run starting...")}</div>
      ) : null,
    },
  ];

  return (
    <ItemEditor
      isLoading={isLoading}
      loadingMessage={t("ConnectorItemEditor_Loading", "Loading connector...")}
      ribbon={(context) => (
        <ConnectorItemRibbon
          workloadClient={workloadClient}
          viewContext={context}
          connectorState={(item?.definition as any)?.state ?? "empty"}
          isRunning={isRunning}
          isSchedulePaused={isSchedulePaused}
          onRunNow={handleRunNow}
          onPauseToggle={handlePauseToggle}
          onReconfigure={() => {
            setWizardState(INITIAL_WIZARD_STATE);
            viewSetter?.(VIEWS.WIZARD_MODULE);
          }}
          onOpenSettings={async () => {
            if (item) {
              const res = await getWorkloadItem(workloadClient, item.id);
              await callOpenSettings(workloadClient, (res as any).item, "About");
            }
          }}
        />
      )}
      messageBar={notifications}
      views={views}
      viewSetter={(fn) => { if (!viewSetter) setViewSetter(() => fn); }}
    />
  );
}
```

---

## 17. STEP 15 — UI i18n: translation.json (ADDITIONS)

**File:** `Workload/app/assets/locales/en-US/translation.json` — append the following keys:

```json
{
  "ConnectorItemEditor_Loading": "Loading connector...",
  "ConnectorItemEmptyView_Title": "Connect your data source",
  "ConnectorItemEmptyView_Description": "Configure your connector to start ingesting data from Dataverse, Business Central, or SQL Server into your Fabric Bronze Lakehouse.",
  "ConnectorItemEmptyView_ConfigureButton": "Configure Connector",
  "ConnectorItemEmptyView_ConfigureButton_Description": "Follow the 7-step wizard to connect your data source.",
  "ConnectorItem_ActivationSuccess": "Connector activated. First run starting...",
  "Wizard_Module_Title": "Select data source type",
  "Wizard_Module_Description": "Choose the source system you want to connect.",
  "Wizard_Module_CRM": "Microsoft Dataverse / Dynamics 365 CRM",
  "Wizard_Module_BC": "Microsoft Dynamics 365 Business Central",
  "Wizard_Module_SQL": "SQL Server / Azure SQL",
  "Wizard_Source_Title": "Configure source",
  "Wizard_Source_TenantId": "Tenant ID",
  "Wizard_Source_CRM_Url": "Environment URL",
  "Wizard_Source_BC_Environment": "Environment",
  "Wizard_Source_BC_CompanyId": "Company ID (optional)",
  "Wizard_Source_SQL_Server": "Server",
  "Wizard_Source_SQL_Database": "Database",
  "Wizard_Auth_Title": "Configure authentication",
  "Wizard_Auth_FabricConnection": "Fabric Connection (Recommended)",
  "Wizard_Auth_KeyVault": "Azure Key Vault Reference",
  "Wizard_Auth_ServicePrincipal": "Service Principal",
  "Wizard_Auth_ConnectionId": "Fabric Connection ID",
  "Wizard_Auth_KV_Uri": "Key Vault URI",
  "Wizard_Auth_KV_SecretName": "Client Secret Name",
  "Wizard_Auth_SP_TenantId": "Tenant ID",
  "Wizard_Auth_SP_ClientId": "Client ID",
  "Wizard_Auth_SP_SecretHint": "Client secret must be stored in a Fabric Connection or Key Vault — not entered here.",
  "Wizard_Entities_Title": "Select entities to ingest",
  "Wizard_Entities_ManualNote": "Entity configuration for this module is set during the review step.",
  "Wizard_Storage_Title": "Configure Bronze Lakehouse",
  "Wizard_Storage_UseExisting": "Use an existing Lakehouse",
  "Wizard_Storage_LakehouseName": "Lakehouse Name",
  "Wizard_Storage_SchemaPolicy": "Schema Evolution Policy",
  "Wizard_Storage_Policy_Merge": "Merge (Recommended — adds new columns)",
  "Wizard_Storage_Policy_Strict": "Strict (Fail on any schema change)",
  "Wizard_Schedule_Title": "Configure ingestion schedule",
  "Wizard_Schedule_Cron": "Cron expression",
  "Wizard_Schedule_Interval": "Fixed interval",
  "Wizard_Schedule_CronExpr": "Cron Expression",
  "Wizard_Schedule_CronHint": "e.g. 0 2 * * * (daily at 02:00 UTC)",
  "Wizard_Schedule_IntervalMinutes": "Interval (minutes)",
  "Wizard_Schedule_IntervalHint": "Minimum 15 minutes",
  "Wizard_Schedule_Timezone": "Timezone",
  "Wizard_Review_Title": "Review & Activate",
  "Wizard_Review_Description": "Review your configuration. Click Activate to deploy the connector and start the first ingestion run.",
  "Wizard_Review_Module": "Module",
  "Wizard_Review_Source": "Source",
  "Wizard_Review_Auth": "Authentication",
  "Wizard_Review_Entities": "Entities",
  "Wizard_Review_Storage": "Storage",
  "Wizard_Review_Schedule": "Schedule",
  "Dashboard_Entities_Title": "Entities",
  "Dashboard_Loading": "Loading run history...",
  "Dashboard_LastRun": "Last Run",
  "Dashboard_NoRuns": "Never",
  "Dashboard_RecordsIngested": "Records (last run)",
  "RunHistory_Status": "Status",
  "RunHistory_Started": "Started",
  "RunHistory_Duration": "Duration",
  "RunHistory_Records": "Records",
  "RunHistory_TriggeredBy": "Triggered By",
  "RunDetail_Title": "Run Details",
  "RunDetail_Started": "Started",
  "RunDetail_Error": "Error",
  "RunDetail_NotFound": "Run not found.",
  "RunDetail_Entity": "Entity",
  "RunDetail_Status": "Status",
  "RunDetail_Records": "Records",
  "RunDetail_Duration": "Duration",
  "EntityList_Empty": "No entities configured.",
  "EntityDetail_NotFound": "Entity not found.",
  "EntityDetail_LastSuccess": "Last Success",
  "EntityDetail_Records": "Records (last run)",
  "EntityDetail_WatermarkType": "Watermark Type",
  "EntityDetail_InitialLoad": "Initial Load Complete"
}
```

---

## 18. STEP 16 — Item Barrel Export: index.ts

**File:** `Workload/app/items/ConnectorItem/index.ts`

```typescript
export { ConnectorItemEditor } from "./ConnectorItemEditor";
export type { ConnectorItemDefinition } from "./ConnectorItemDefinition";
```

This is what `App.tsx` imports: `import { ConnectorItemEditor } from "./items/ConnectorItem"`.

---

## 19. STEP 17 — CONTROLLERS

### NotebookDeploymentController.ts

**File:** `Workload/app/controller/NotebookDeploymentController.ts`

```typescript
import { WorkloadClientAPI } from "@ms-fabric/workload-client";
import { ModuleType } from "../items/ConnectorItem/ConnectorItemDefinition";

const CURRENT_WHEEL_VERSION = "1.0.0";

export interface NotebookDeploymentResult {
  notebookItemId: string;
  deployedAt: string;
  wheelVersion: string;
}

export async function deployConnectorNotebook(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  connectorItemId: string,
  moduleType: ModuleType
): Promise<NotebookDeploymentResult> {
  // Phase 1 placeholder — actual implementation in Phase 5
  // Will: 1) fetch notebook template content from /assets/notebooks/
  //        2) replace %%CONNECTOR_ITEM_ID%%, %%WORKSPACE_ID%%, %%WHEEL_VERSION%%
  //        3) POST to Fabric Items API to create Notebook item
  //        4) return the created notebook's item ID
  throw new Error("NotebookDeploymentController: not yet implemented — Phase 5 target");
}

export function buildNotebookDisplayName(moduleType: ModuleType, connectorItemId: string): string {
  const prefix = {
    crm: "FUC-CRM-Runtime",
    businesscentral: "FUC-BC-Runtime",
    sql: "FUC-SQL-Runtime",
  }[moduleType];
  return `${prefix}-${connectorItemId}`;
}
```

### LakehouseController.ts

**File:** `Workload/app/controller/LakehouseController.ts`

```typescript
import { WorkloadClientAPI } from "@ms-fabric/workload-client";

export interface LakehouseEnsureResult {
  lakeHouseId: string;
  lakeHouseName: string;
  wasCreated: boolean;
}

export async function ensureBronzeLakehouse(
  workloadClient: WorkloadClientAPI,
  workspaceId: string,
  lakeHouseName: string,
  useExisting: boolean
): Promise<LakehouseEnsureResult> {
  // Phase 1 placeholder — actual implementation in Phase 5
  // Will: 1) if useExisting: list Lakehouses and find by name
  //        2) if not found or !useExisting: POST to Fabric Items API to create Lakehouse
  //        3) return the Lakehouse item ID
  throw new Error("LakehouseController: not yet implemented — Phase 5 target");
}
```

---

## 20. STEP 18 — PYTHON WHEEL: DIRECTORY STRUCTURE + pyproject.toml

### pyproject.toml

**File:** `connector/runtime/pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "agic-fabric-connector"
version = "1.0.0"
description = "Fabric Universal Connector ingestion runtime"
authors = [{name = "Agic Technology srl", email = "support@agic.technology"}]
requires-python = ">=3.10"
license = {text = "Proprietary"}
dependencies = [
    "msal>=1.26",
    "requests>=2.31",
    "pandas>=2.0",
    "delta-spark>=3.0",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov",
    "pytest-mock",
    "ruff",
    "mypy",
]

[tool.setuptools.packages.find]
where = ["."]
include = ["agic_fabric_connector*"]

[tool.ruff]
line-length = 120
target-version = "py310"

[tool.mypy]
python_version = "3.10"
strict = true
```

### setup.cfg (for editable installs)

**File:** `connector/runtime/setup.cfg`

```ini
[options]
packages = find:
python_requires = >=3.10
```

### `__init__.py` files

Create empty `__init__.py` in every package directory:

```
connector/runtime/agic_fabric_connector/__init__.py          ← "from agic_fabric_connector import __version__\n__version__ = '1.0.0'"
connector/runtime/agic_fabric_connector/base/__init__.py     ← empty
connector/runtime/agic_fabric_connector/config/__init__.py   ← empty
connector/runtime/agic_fabric_connector/auth/__init__.py     ← empty
connector/runtime/agic_fabric_connector/modules/__init__.py  ← empty
connector/runtime/agic_fabric_connector/modules/crm/__init__.py          ← "from .crm_connector import CRMConnector"
connector/runtime/agic_fabric_connector/modules/businesscentral/__init__.py  ← "from .bc_connector import BusinessCentralConnector"
connector/runtime/agic_fabric_connector/modules/sql/__init__.py          ← "from .sql_connector import SQLConnector"
connector/runtime/agic_fabric_connector/utils/__init__.py    ← empty
```

---

## 21. STEP 19 — PYTHON WHEEL: CORE MODULE FILES (SKELETONS)

All Python files in this step are stubs that compile cleanly and raise `NotImplementedError`. Full implementation is Phase 5 (CRM only) and beyond.

### connector/runtime/agic_fabric_connector/base/connector_base.py

Full implementation per `.ai/contracts/ingestion-contracts.md` Section 2. Copy the `BaseConnector` class definition exactly. Imports reference local modules.

### connector/runtime/agic_fabric_connector/base/bronze_writer.py

```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    import pandas as pd
    from pyspark.sql import SparkSession
    from agic_fabric_connector.config.config_models import ConnectorItemDefinition, EntityConfig

WHEEL_VERSION = "1.0.0"

class BronzeWriter:
    def __init__(self, config: "ConnectorItemDefinition", spark: "SparkSession"):
        self.config = config
        self.spark = spark

    def write(self, df: "pd.DataFrame", entity: "EntityConfig") -> int:
        raise NotImplementedError("BronzeWriter.write — Phase 5 implementation target")
```

### connector/runtime/agic_fabric_connector/base/metadata_writer.py

```python
from __future__ import annotations
from agic_fabric_connector.base.run_result import RunResult, EntityResult
from agic_fabric_connector.base.metadata_models import ConnectorRunRecord

class MetadataWriter:
    def __init__(self, config, spark):
        self.config = config
        self.spark = spark

    def start_run(self) -> ConnectorRunRecord:
        raise NotImplementedError

    def complete_run(self, run: ConnectorRunRecord, results: list[EntityResult]) -> ConnectorRunRecord:
        raise NotImplementedError

    def fail_run(self, run: ConnectorRunRecord, message: str, code: str) -> None:
        raise NotImplementedError

    def log_error(self, entity, error: Exception) -> None:
        raise NotImplementedError
```

### connector/runtime/agic_fabric_connector/base/watermark.py

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from enum import Enum

class WatermarkType(str, Enum):
    DELTA_TOKEN = "delta_token"
    TIMESTAMP   = "timestamp"
    ROWVERSION  = "rowversion"

@dataclass
class Watermark:
    watermark_type: WatermarkType
    delta_token: Optional[str]
    watermark_value: Optional[str]
    watermark_column: Optional[str]

    def is_initial_load(self) -> bool:
        return self.delta_token is None and self.watermark_value is None

class WatermarkStore:
    def __init__(self, config, spark):
        self.config = config
        self.spark = spark

    def get(self, entity_name: str) -> Optional[Watermark]:
        raise NotImplementedError

    def upsert(self, entity, watermark: Watermark) -> None:
        raise NotImplementedError

    def reset(self, entity_name: str) -> None:
        raise NotImplementedError
```

### connector/runtime/agic_fabric_connector/base/run_result.py

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class EntityResult:
    entity_name: str
    status: str
    records_ingested: int
    records_failed: int
    duration_seconds: float
    new_watermark: Optional[str]
    error_message: Optional[str]

@dataclass
class RunResult:
    run_id: str
    status: str
    entity_results: List[EntityResult] = field(default_factory=list)
```

### connector/runtime/agic_fabric_connector/base/exceptions.py

Full exception taxonomy per `.ai/contracts/ingestion-contracts.md` Section 10:

```python
from typing import Optional

class ConnectorError(Exception):
    error_code: str = "UNKNOWN_ERROR"

class ConnectorFatalError(ConnectorError):
    def __init__(self, message: str, error_code: str):
        super().__init__(message)
        self.error_code = error_code

class AuthenticationError(ConnectorError):
    error_code = "AUTH_ERROR"

class ThrottlingError(ConnectorError):
    error_code = "THROTTLING_ERROR"
    def __init__(self, message: str, retry_after_seconds: Optional[float] = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds

class TransientError(ConnectorError):
    error_code = "TRANSIENT_ERROR"

class EntityExtractionError(ConnectorError):
    error_code = "EXTRACTION_ERROR"

class BronzeWriteError(ConnectorError):
    error_code = "BRONZE_WRITE_ERROR"

class SchemaConflictError(ConnectorError):
    error_code = "SCHEMA_CONFLICT_ERROR"

class ConfigValidationError(ConnectorError):
    error_code = "CONFIG_VALIDATION_ERROR"

class ConfigLoadError(ConnectorError):
    error_code = "CONFIG_LOAD_ERROR"
```

### connector/runtime/agic_fabric_connector/base/retry_policy.py

Full implementation per `.ai/contracts/ingestion-contracts.md` Section 9.

### connector/runtime/agic_fabric_connector/config/config_models.py

Dataclasses corresponding to `ConnectorItemDefinition` JSON Schema. Includes `CrmSourceConfiguration`, `BusinessCentralSourceConfiguration`, `SqlSourceConfiguration`, `AuthConfiguration`, `CrmEntityConfiguration`, `BusinessCentralEntityConfiguration`, `SqlEntityConfiguration`, `StorageConfiguration`, `SchedulingConfiguration`, `FeaturesConfiguration`, `RuntimeConfiguration`, `ConnectorMetadata`, `ConnectorItemDefinition` (with `moduleType` discriminator).

### connector/runtime/agic_fabric_connector/config/config_loader.py

Per `.ai/contracts/ingestion-contracts.md` Section 7. The `from_item_definition` static method uses `mssparkutils.credentials.getToken()` and the Fabric Items API. Full implementation in Phase 5.

### connector/runtime/agic_fabric_connector/modules/crm/crm_connector.py

Skeleton extending `BaseConnector` per `.ai/contracts/ingestion-contracts.md` Section 3.1.

### connector/runtime/agic_fabric_connector/modules/crm/entity_catalog.py

Full catalog of 5 Phase 1 entities per `.ai/contracts/ingestion-contracts.md` Section 3.1 `CRM_ENTITY_CATALOG`.

### connector/runtime/agic_fabric_connector/modules/businesscentral/bc_connector.py

Skeleton per Section 3.2.

### connector/runtime/agic_fabric_connector/modules/sql/sql_connector.py

Skeleton per Section 3.3.

---

## 22. STEP 20 — NOTEBOOK TEMPLATES

**Files:**
- `connector/runtime/notebooks/connector_runtime_crm.ipynb`
- `connector/runtime/notebooks/connector_runtime_bc.ipynb`
- `connector/runtime/notebooks/connector_runtime_sql.ipynb`

Each is a Jupyter notebook JSON file. Template per `.ai/contracts/ingestion-contracts.md` Section 13. The three cells are identical across modules except the import and class instantiation line.

```json
{
  "nbformat": 4,
  "nbformat_minor": 5,
  "metadata": {
    "kernelspec": { "display_name": "PySpark", "language": "python", "name": "synapse_pyspark" },
    "language_info": { "name": "python" }
  },
  "cells": [
    {
      "cell_type": "code",
      "source": ["%pip install agic-fabric-connector==%%WHEEL_VERSION%%"],
      "metadata": { "collapsed": false },
      "outputs": []
    },
    {
      "cell_type": "code",
      "source": [
        "from agic_fabric_connector.config.config_loader import ConfigLoader\n",
        "from agic_fabric_connector.modules.crm import CRMConnector\n",
        "\n",
        "CONNECTOR_ITEM_ID = '%%CONNECTOR_ITEM_ID%%'\n",
        "WORKSPACE_ID      = '%%WORKSPACE_ID%%'\n",
        "\n",
        "config = ConfigLoader.from_item_definition(\n",
        "    item_id=CONNECTOR_ITEM_ID,\n",
        "    workspace_id=WORKSPACE_ID,\n",
        "    spark=spark\n",
        ")"
      ],
      "metadata": {},
      "outputs": []
    },
    {
      "cell_type": "code",
      "source": [
        "connector = CRMConnector(config, spark)\n",
        "result = connector.run()\n",
        "print(f'Run complete: {result.status} | Entities: {len(result.entity_results)} | Records: {sum(r.records_ingested for r in result.entity_results)}')"
      ],
      "metadata": {},
      "outputs": []
    }
  ]
}
```

For `connector_runtime_bc.ipynb`: replace `CRMConnector` with `BusinessCentralConnector` and adjust import.  
For `connector_runtime_sql.ipynb`: replace with `SQLConnector`.

---

## 23. STEP 21 — ASSET PLACEHOLDERS

The following image/SVG files must exist for the workload to build without errors. Create placeholder files (can be 1x1 px transparent PNG or simple SVG):

```
Workload/Manifest/assets/images/ConnectorItem_Icon.png    ← 32x32 PNG icon
Workload/app/assets/items/ConnectorItem/EditorEmpty.svg   ← empty state illustration SVG
```

Placeholder SVG for `EditorEmpty.svg`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <rect width="200" height="200" fill="#f5f5f5" rx="16"/>
  <text x="100" y="110" text-anchor="middle" font-size="48" fill="#bbb">⚡</text>
</svg>
```

Placeholder PNG: copy from `Workload/Manifest/assets/images/HelloWorldItem_Icon.png` as a temporary stand-in.

---

## 24. DEPENDENCY GRAPH

```
[Step 1] ConnectorItem.xml
[Step 2] ConnectorItem.json
[Step 3] Product.json ← depends on Step 2 (itemType "Connector" must exist in manifest)
[Step 4] translations.json (manifest i18n)
         │
         ▼
[Step 6] ConnectorItemDefinition.ts
[Step 7] wizardState.ts ← imports ConnectorItemDefinition.ts
[Step 8] wizardValidation.ts ← imports wizardState.ts
[Step 9] ConnectorItem.scss
         │
         ▼
[Step 10] ConnectorItemEmptyView.tsx ← imports ConnectorItemDefinition.ts, ConnectorItem.scss
[Step 11] ribbonActionFactory.ts + ConnectorItemRibbon.tsx ← imports ConnectorItemDefinition.ts
[Step 12] WizardModuleStep ... WizardReviewStep ← all import wizardState.ts, wizardValidation.ts
[Step 13] Dashboard components ← import ConnectorItemDefinition.ts
          │
          ▼
[Step 14] ConnectorItemEditor.tsx ← imports ALL above components
[Step 16] index.ts ← re-exports ConnectorItemEditor
          │
          ▼
[Step 5]  App.tsx ← imports index.ts
[Step 15] translation.json ← used by all components via t()
[Step 17] Controllers ← imported by ConnectorItemEditor Activate handler
```

---

## 25. VALIDATION CHECKLIST

Before declaring scaffold complete, verify every item:

### Manifest Checks

- [ ] `Workload/Manifest/items/ConnectorItem/ConnectorItem.xml` exists with `TypeName="{{WORKLOAD_NAME}}.Connector"`
- [ ] `Workload/Manifest/items/ConnectorItem/ConnectorItem.json` exists with `"name": "Connector"` and `"editor.path": "/ConnectorItem-editor"`
- [ ] `Workload/Manifest/Product.json` has `"Connector"` in `recommendedItemTypes`
- [ ] `Workload/Manifest/Product.json` has a second card in `createExperience.cards` with `"itemType": "Connector"`
- [ ] `Workload/Manifest/assets/locales/en-US/translations.json` has `ConnectorItem_DisplayName`, `ConnectorItem_DisplayName_Plural`, `ConnectorItem_Description`

### Frontend Checks

- [ ] `Workload/app/App.tsx` has `import { ConnectorItemEditor } from "./items/ConnectorItem"`
- [ ] `Workload/app/App.tsx` has `<Route path="/ConnectorItem-editor/:itemObjectId">` inside `<Switch>`
- [ ] `Workload/app/items/ConnectorItem/index.ts` exports `ConnectorItemEditor`
- [ ] `ConnectorItemDefinition.ts` has the `ConnectorItemDefinition` discriminated union type
- [ ] `wizardState.ts` exports `INITIAL_WIZARD_STATE`, `WIZARD_STEPS`, `WIZARD_STEP_ORDER`, `WizardState`
- [ ] `wizardValidation.ts` exports `validateStep` covering all 7 wizard steps
- [ ] `ConnectorItemEditor.tsx` exports `VIEWS` constant (used by `ConnectorItemRibbon.tsx`)
- [ ] `ConnectorItemEditor.tsx` static `views` array has exactly 11 entries
- [ ] `ConnectorItemRibbon.tsx` imports `VIEWS` from `ConnectorItemEditor` (not re-defined)
- [ ] All 7 wizard step components have `WizardStepProps` interface
- [ ] Dashboard components compile without TypeScript errors
- [ ] `Workload/app/assets/locales/en-US/translation.json` has all 60+ new keys
- [ ] `Workload/app/assets/items/ConnectorItem/EditorEmpty.svg` exists

### TypeScript Compilation Check

```powershell
cd Workload
npx tsc --noEmit
```

Expected: zero errors.

### Build Check

```powershell
cd Workload
npm run build
```

Expected: build succeeds. Verify `Connector` appears in manifest output.

### Python Wheel Check

```powershell
cd connector/runtime
pip install -e ".[dev]"
python -c "from agic_fabric_connector.base.exceptions import ConnectorFatalError; print('OK')"
python -m pytest connector/tests/unit/ -v
```

Expected: package imports successfully. Unit tests (when written) pass.

### Controller Check

- [ ] `NotebookDeploymentController.ts` compiles and exports `deployConnectorNotebook`
- [ ] `LakehouseController.ts` compiles and exports `ensureBronzeLakehouse`
- [ ] Both controllers raise `NotImplementedError` equivalents (not silently return wrong data)

### Asset Check

- [ ] `Workload/Manifest/assets/images/ConnectorItem_Icon.png` exists (placeholder OK)
- [ ] `Workload/app/assets/items/ConnectorItem/EditorEmpty.svg` exists
