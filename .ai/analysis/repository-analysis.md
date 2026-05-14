# PHASE 1 — REPOSITORY ANALYSIS

**Project:** Fabric Universal Connector  
**Author:** Principal Architect Review  
**Date:** 2026-05-14  
**Status:** COMPLETE — Awaiting Phase 2 instruction

---

## 1. REPOSITORY IDENTITY

| Property | Value |
|---|---|
| Repository name | fabric-universal-connector |
| Origin | Fork of `microsoft/Microsoft-Fabric-workload-development-sample` |
| Remote | `AlessioAndriuloAGIC/fabric-universal-connector` |
| Active branch | `alessio-fabric-custom-workload` |
| Latest release | v2026.03 — Remote Hosting & Job Scheduling |
| Workload name | `Org.FabricUniversalConnector` |
| Workload version | `1.100` |
| Hosting type | `FERemote` (frontend-only, ISV-hosted) |

---

## 2. FULL DIRECTORY STRUCTURE

```
fabric-universal-connector/
│
├── .ai/                              # AI agent context and automation commands
│   ├── AGENTS.md                     # Architectural principles for agents
│   ├── commands/
│   │   ├── item/
│   │   │   ├── createItem.md         # Step-by-step item scaffolding spec
│   │   │   ├── deleteItem.md
│   │   │   └── renameItem.md
│   │   └── workload/
│   │       ├── runWorkload.md
│   │       ├── deployWorkload.md
│   │       ├── publishworkload.md
│   │       ├── updateWorkload.md
│   │       └── cleanWorkload.md
│   └── context/
│       ├── fabric.md                 # Fabric platform knowledge base
│       ├── fabric-workload.md        # Extensibility toolkit patterns
│       └── markdown-formatting.md
│
├── .github/
│   ├── copilot/                      # Copilot agent configuration
│   ├── instructions/                 # GitHub workflow instructions
│   ├── ISSUE_TEMPLATE/
│   ├── copilot-instructions.md
│   └── mcp-quick-start.md
│
├── .devcontainer/                    # Codespace / dev container config
│   ├── devcontainer.json
│   ├── Dockerfile
│   └── README.md
│
├── .vscode/                          # VSCode editor settings
│   └── settings.json
│
├── .claude/                          # Claude Code local settings
│   └── settings.local.json
│
├── Workload/                         # ★ MAIN APPLICATION — entire React SDK workload
│   ├── .env.dev                      # Development environment variables
│   ├── .env.test                     # Staging/test environment variables
│   ├── .env.prod                     # Production environment variables
│   ├── .env.template                 # Documented variable reference
│   ├── package.json                  # NPM config, dependencies, build scripts
│   ├── tsconfig.json                 # TypeScript strict config
│   ├── webpack.config.js             # Webpack 5 bundler configuration
│   │
│   ├── app/                          # React/TypeScript source code
│   │   ├── index.ui.tsx              # SDK entry point: initialize(), WorkloadClient
│   │   ├── index.ts                  # Module re-exports
│   │   ├── index.worker.ts           # Web worker entry point
│   │   ├── App.tsx                   # React Router + route definitions
│   │   ├── constants.ts              # Application constants
│   │   ├── theme.tsx                 # Fluent UI brand theme (teal)
│   │   ├── i18n.js                   # i18next configuration
│   │   │
│   │   ├── clients/                  # ★ Fabric API thin wrappers
│   │   │   ├── FabricPlatformTypes.ts      # All TypeScript interfaces (1087 lines)
│   │   │   ├── FabricPlatformClient.ts     # Base HTTP client (auth + retry)
│   │   │   ├── FabricPlatformAPIClient.ts  # High-level API wrapper
│   │   │   ├── FabricAuthenticationService.ts  # Token acquisition service
│   │   │   ├── FabricPlatformScopes.ts     # OAuth scopes (SCOPE_PAIRS)
│   │   │   ├── ItemClient.ts               # Item CRUD REST calls
│   │   │   ├── JobSchedulerClient.ts       # Full job scheduling client
│   │   │   ├── WorkspaceClient.ts          # Workspace management
│   │   │   ├── CapacityClient.ts           # Capacity management
│   │   │   ├── ConnectionClient.ts         # Connections & gateways
│   │   │   ├── OneLakeStorageClient.ts     # OneLake file operations
│   │   │   ├── OneLakeStorageClientItemWrapper.ts  # Item-scoped OneLake
│   │   │   ├── OneLakeShortcutClient.ts    # OneLake shortcuts
│   │   │   ├── OneLakeDataAccessSecurityClient.ts  # Data access roles
│   │   │   ├── SparkClient.ts              # Spark job management
│   │   │   ├── SparkLivyClient.ts          # Spark Livy sessions
│   │   │   ├── LongRunningOperationsClient.ts  # Async operation polling
│   │   │   ├── ExternalDataSharesProviderClient.ts
│   │   │   ├── ExternalDataSharesRecipientClient.ts
│   │   │   ├── FolderClient.ts
│   │   │   ├── GatewayClient.ts
│   │   │   ├── TagsClient.ts
│   │   │   ├── README.md
│   │   │   └── index.ts
│   │   │
│   │   ├── controller/               # ★ Business logic — async call* functions
│   │   │   ├── ItemCRUDController.ts       # getWorkloadItem, saveItemDefinition
│   │   │   ├── AuthenticationController.ts # callAcquireFrontendAccessToken
│   │   │   ├── NavigationController.ts     # navigateToItem, FabricItemMappings
│   │   │   ├── NotificationController.ts   # callNotificationOpen
│   │   │   ├── DialogController.ts         # callDialogOpen, callDialogOpenMsgBox
│   │   │   ├── PanelController.ts          # callPanelOpen
│   │   │   ├── SettingsController.ts       # callOpenSettings, callSettingsGet
│   │   │   ├── ActionController.ts         # callActionOnAction, callActionExecute
│   │   │   ├── DataHubController.ts        # callDatahubWizardOpen
│   │   │   ├── ConfigurationController.ts
│   │   │   ├── ErrorHandlingController.ts
│   │   │   ├── PageController.ts
│   │   │   └── ThemeController.ts
│   │   │
│   │   ├── components/               # ★ SHARED BASE COMPONENTS — NEVER MODIFY
│   │   │   ├── index.ts
│   │   │   ├── ItemEditor/
│   │   │   │   ├── ItemEditor.tsx          # Root container: fixed ribbon + scroll
│   │   │   │   ├── ItemEditor.scss
│   │   │   │   ├── ItemEditorDefaultView.tsx  # Left+center resizable split
│   │   │   │   ├── ItemEditorDetailView.tsx   # L2 drill-down, auto back-nav
│   │   │   │   ├── ItemEditorEmptyView.tsx    # Standard empty state
│   │   │   │   ├── ItemEditorLoadingView.tsx  # Loading skeleton (internal)
│   │   │   │   ├── Ribbon.tsx                 # Ribbon container + tab system
│   │   │   │   ├── RibbonToolbar.tsx          # Action rendering (Tooltip+Button)
│   │   │   │   ├── RibbonToolbarAction.tsx    # Single action renderer
│   │   │   │   ├── RibbonStandardActions.tsx  # createSaveAction, createSettingsAction
│   │   │   │   ├── RibbonActionButton.tsx
│   │   │   │   └── index.ts
│   │   │   ├── OneLakeView/
│   │   │   │   ├── OneLakeView.tsx            # File/table explorer control
│   │   │   │   ├── OneLakeView.scss
│   │   │   │   ├── OneLakeViewController.ts
│   │   │   │   ├── OneLakeViewModel.ts
│   │   │   │   ├── FileTree.tsx
│   │   │   │   ├── TableTreeWithSchema.tsx
│   │   │   │   ├── TableTreeWithoutSchema.tsx
│   │   │   │   └── index.ts
│   │   │   ├── Wizard/
│   │   │   │   ├── Wizard.tsx                 # Multi-step wizard control
│   │   │   │   ├── Wizard.scss
│   │   │   │   └── index.ts
│   │   │   └── Dialog/
│   │   │       ├── DialogControl.tsx
│   │   │       ├── Dialog.scss
│   │   │       └── index.ts
│   │   │
│   │   ├── items/                    # ★ WORKLOAD ITEMS — custom implementations
│   │   │   └── HelloWorldItem/       # Reference implementation (only item)
│   │   │       ├── HelloWorldItemDefinition.ts   # { message?: string }
│   │   │       ├── HelloWorldItemEditor.tsx       # Main editor component
│   │   │       ├── HelloWorldItemEmptyView.tsx    # Empty state
│   │   │       ├── HelloWorldItemDefaultView.tsx  # Default content view
│   │   │       ├── HelloWorldItemRibbon.tsx       # Toolbar
│   │   │       ├── HelloWorldItem.scss            # Item-specific styles
│   │   │       ├── GettingStartedSection.tsx      # Custom sub-component
│   │   │       ├── ItemDetailsSection.tsx         # Custom sub-component
│   │   │       └── index.ts
│   │   │
│   │   ├── playground/               # Dev-only SDK exploration (ENABLE_PLAYGROUND=true)
│   │   │   ├── ClientSDKPlayground/  # Full API testing ground with Redux store
│   │   │   ├── DataPlayground/
│   │   │   └── ConditionalPlaygroundRoutes.tsx
│   │   │
│   │   ├── samples/                  # Reference sample views (DO NOT COPY)
│   │   │   └── views/
│   │   │       ├── SampleEventhouseExplorer/
│   │   │       ├── SampleOneLakeItemExplorer/
│   │   │       └── SampleOneLakeShortcutCreator/
│   │   │
│   │   └── assets/
│   │       ├── locales/en-US/translation.json   # React component i18n strings
│   │       ├── items/HelloWorldItem/             # Empty state SVG assets
│   │       ├── components/OneLakeView/           # Component-specific assets
│   │       └── fabric-icon.png
│   │
│   ├── Manifest/                     # Workload + item registration manifests
│   │   ├── WorkloadManifest.xml      # Workload registration (schema 2.0.0)
│   │   ├── Product.json              # Create experience + home page config
│   │   ├── ManifestPackage.nuspec    # NuGet package definition
│   │   ├── CommonTypesDefinitions.xsd
│   │   ├── ItemDefinition.xsd
│   │   ├── WorkloadDefinition.xsd
│   │   ├── items/HelloWorldItem/
│   │   │   ├── HelloWorldItem.json   # Item editor path, icons, actions, lifecycle
│   │   │   └── HelloWorldItem.xml    # Type registration (TypeName, Category)
│   │   └── assets/
│   │       ├── images/               # Workload + item icon assets
│   │       └── locales/en-US/translations.json  # Manifest-level i18n strings
│   │
│   └── devServer/                    # Webpack dev server configuration
│
├── backend/                          # ★ EMPTY — placeholder directory only
│   └── src/connectors/               # No files exist
│
├── backend_2/                        # ★ EMPTY — placeholder directory only
│   └── python/modules/               # No files exist
│
├── build/                            # Generated artifacts (not committed)
│   └── Manifest/
│       └── ManifestPackage.nupkg     # Compiled NuGet package
│
├── scripts/                          # PowerShell automation
│   ├── Build/
│   │   ├── BuildManifestPackage.ps1  # NuGet generation from templates
│   │   ├── BuildRelease.ps1          # Full release pipeline
│   │   └── Manifest/ValidationScripts/  # 5 manifest validators
│   ├── Deploy/
│   │   └── DeployToAzureWebApp.ps1   # Azure App Service deployment
│   ├── Run/
│   │   ├── StartDevServer.ps1        # Webpack dev server launcher
│   │   └── StartDevGateway.ps1       # DevGateway launcher
│   └── Setup/
│       ├── Setup.ps1                 # Main setup entry point
│       ├── SetupWorkload.ps1
│       ├── SetupDevEnvironment.ps1
│       ├── SwitchToRemoteHosting.ps1 # FERemote → Remote migration script
│       ├── CreateDevAADApp.ps1       # Entra ID app creation
│       ├── CreateNewItem.ps1         # Item scaffold helper
│       ├── CreateJob.ps1             # Job scaffold helper
│       ├── DownloadDevGateway.ps1    # DevGateway binary download
│       ├── SetupConfiguration.md     # Configuration guide
│       ├── remote/                   # Node.js remote operation helpers
│       │   ├── index.js, authentication.js, tokenBuilder.js
│       │   ├── fabricApiClient.js, itemCrudApi.js
│       │   ├── oneLakeClientService.js, jobsApi.js
│       │   ├── permissionsApi.js, tokenExchangeService.js
│       │   ├── endpointResolutionApi.js, itemLogger.js
│       │   ├── jobsLogger.js, permissions.js, utils.js
│       └── job/
│           ├── JobSchedulerController.ts
│           └── jobUtils.ts
│
├── tools/
│   └── DevGateway/                   # Pre-built .NET 8 binary for local dev
│       └── (runtime files, XML docs)
│
└── docs/
    ├── Project_Structure.md
    ├── Project_Setup.md
    ├── FabricUX_MCP_Server.md
    ├── components/
    │   ├── ItemEditor.md, OneLakeView.md, Wizard.md, README.md
    └── items/HelloWorldItem/
```

---

## 3. TECHNOLOGY STACK

### Frontend (Primary Codebase)

| Technology | Version | Role |
|---|---|---|
| React | 18.x | UI framework |
| TypeScript | 5.x (strict) | Type safety, compiler |
| @ms-fabric/workload-client | 3.1.1 | Fabric SDK — core integration layer |
| @fluentui/react-components | v9 | UI component library |
| @fluentui/react | v8 | Legacy (Stack, etc.) — still used in some items |
| React Router | v5 | Client-side routing |
| Redux Toolkit | Latest | State management (Playground only currently) |
| i18next | Latest | Internationalization |
| Webpack | 5 | Module bundler |
| SASS | Latest | Styling |

### Build and Deployment

| Technology | Role |
|---|---|
| PowerShell | Build, deploy, setup automation |
| NuGet | Manifest package distribution |
| Azure App Service | Frontend hosting target |
| Docker (optional) | Containerized DevGateway |

### Development Tooling

| Tool | Role |
|---|---|
| DevGateway (.NET 8) | Local manifest serving + Fabric proxy |
| webpack-dev-server | HMR development server |
| ESLint | Code linting |
| TypeScript compiler | Type checking |

### Absent Technologies (Gaps)

- **No CI/CD pipelines** (no `.github/workflows/` directory)
- **No unit test framework** (no Jest config, no spec files)
- **No backend runtime** (backend/ and backend_2/ are empty)
- **No infrastructure-as-code** (no Terraform / Bicep)
- **No Python ingestion runtime** (notebooks not written)

---

## 4. SDK ARCHITECTURE ANALYSIS

### Entry Point and Initialization

The SDK entry point is `Workload/app/index.ui.tsx`. The mandatory `initialize(params: InitParams)` function:

1. Creates `WorkloadClientAPI` via `createWorkloadClient()`
2. Registers navigation handler (`workloadClient.navigation.onNavigate`)
3. Registers action handler (`workloadClient.action.onAction`) for tab lifecycle
4. Renders React application with `FluentProvider` wrapper

**Current action handlers registered:**
- `item.tab.onInit` → fetches item display name
- `item.tab.canDeactivate` → always returns `{ canDeactivate: true }`
- `item.tab.onDeactivate`, `canDestroy`, `onDestroy`, `onDelete` → stub returns

**Gap:** No item-specific validation logic in `canDeactivate` / `canDestroy`. For a connector item, these should check for unsaved configuration changes.

### SDK Capability Inventory

The SDK (v3.1.1) exposes the following namespaces, all of which have client wrappers implemented:

| SDK Namespace | Controller | Client | Status |
|---|---|---|---|
| `workloadClient.itemCrud` | ItemCRUDController | ItemClient | ✅ Fully implemented |
| `workloadClient.auth` | AuthenticationController | FabricAuthenticationService | ✅ Implemented |
| `workloadClient.navigation` | NavigationController | — | ✅ Implemented (40+ item type mappings) |
| `workloadClient.notification` | NotificationController | — | ✅ Implemented |
| `workloadClient.dialog` | DialogController | — | ✅ Implemented |
| `workloadClient.panel` | PanelController | — | ✅ Implemented |
| `workloadClient.settings` | SettingsController | — | ✅ Implemented |
| `workloadClient.action` | ActionController | — | ✅ Implemented |
| `workloadClient.page` | PageController | — | ✅ Implemented |
| `workloadClient.dataHub` | DataHubController | — | ✅ Implemented |
| `workloadClient.theme` | ThemeController | — | ✅ Implemented |
| Fabric Job Scheduler REST | — | JobSchedulerClient | ✅ Full implementation |
| Fabric Spark REST | — | SparkClient, SparkLivyClient | ✅ Implemented |
| OneLake REST | — | OneLakeStorageClient + Wrapper | ✅ Implemented |
| Fabric Workspace REST | — | WorkspaceClient | ✅ Implemented |
| Fabric Connection REST | — | ConnectionClient | ✅ Implemented |
| Fabric Gateway REST | — | GatewayClient | ✅ Implemented |

**Key finding:** The client layer is extremely well-developed. All major Fabric APIs have typed client implementations. This is significantly ahead of what a vanilla Microsoft sample provides. The SDK surface is fully ready to support the ConnectorItem.

### JobSchedulerClient — Detailed Assessment

The `JobSchedulerClient` is a complete, production-grade implementation:
- `listItemSchedules`, `createItemSchedule`, `updateItemSchedule`, `deleteItemSchedule`
- `runOnDemandItemJob` — correctly extracts Job Instance ID from `Location` header
- `cancelItemJobInstance` — implements fallback for legacy URL pattern (robustness)
- `getJobInstancesByStatus`, `getRunningJobInstances`, `getFailedJobInstances`
- `toggleSchedule` — enable/disable with config preservation
- `cancelAllRunningJobs` — bulk operation with `Promise.allSettled`
- Full pagination support via inherited `getAllPages<T>`

This client is **ready to use without modification** for the ConnectorItem's scheduling feature.

### ItemCRUDController — Detailed Assessment

Complete implementation covering all lifecycle stages:
- `callGetItem` → metadata only
- `getWorkloadItem<T>` → metadata + definition in one call
- `saveItemDefinition<T>` → single-part save (simplest path)
- `saveWorkloadItem<T>` → multi-part save (handles `additionalDefinitionParts`)
- `callUpdateItemDefinition` → raw multi-part update
- `convertGetItemResultToWorkloadItem<T>` → deserializes `payload.json` from Base64
- `buildPublicAPIPayloadWithParts` → utility for multi-part construction
- `convertGetDefinitionResponseToItemDefinition` → handles raw HTTP response parsing

**Important implementation detail:** Item definitions are stored as Base64-encoded JSON in `payload.json`. Multi-part definitions are supported via `additionalDefinitionParts`. The `.platform` part carries Fabric metadata (type, displayName, description).

**Item reload optimization is implemented:** `HelloWorldItemEditor.tsx` checks `item.id === pageContext.itemObjectId` before triggering a reload. This pattern must be preserved in the ConnectorItem.

---

## 5. COMPONENT ARCHITECTURE ANALYSIS

### ItemEditor Component

The `ItemEditor` is the mandatory root container for all item editors. Its API:

```typescript
<ItemEditor
  isLoading={boolean}
  loadingMessage={string}
  ribbon={(context: ViewContext) => ReactNode}   // Function pattern — receives view context
  messageBar={RegisteredNotification[]}          // Declarative notification registration
  views={RegisteredView[]}                       // Static view registration array
  viewSetter={(setCurrentView) => void}          // Callback to expose view setter upward
/>
```

**Pattern observed in HelloWorldItemEditor:** The `viewSetter` callback is used to capture `setCurrentView` for use in async effects — necessary when view transitions depend on async data load completion. This is a non-obvious but correct pattern.

**Notification system:** `RegisteredNotification[]` is declarative — notifications are registered with `name` and `showInViews[]`. The `ItemEditor` handles showing/hiding based on current view. This avoids conditional JSX in view components.

### Ribbon Component

Correct pattern as enforced by `.ai/commands/item/createItem.md`:

```typescript
// MANDATORY: Use Ribbon + RibbonToolbar + createRibbonTabs
const tabs = createRibbonTabs(t("Home"));
const actions: RibbonAction[] = [
  createSaveAction(onSave, disabled, translate),
  createSettingsAction(onSettings, translate),
  { key: 'custom', icon: Icon24, label: 'Label', onClick: handler, testId: 'test-id' }
];
return <Ribbon tabs={tabs}><RibbonToolbar actions={actions} /></Ribbon>;
```

**HelloWorldItemRibbon.tsx** implements this correctly and serves as the definitive reference.

### View Navigation Pattern

Views are registered as a static array. Navigation uses `useViewNavigation()` hook inside child components, or `viewSetter` callback at the editor level. Detail views use `isDetailView: true` flag for automatic back navigation.

**The `EmptyViewWrapper` pattern in HelloWorldItemEditor:** A nested component uses the `useViewNavigation` hook to access `setCurrentView`. This is the correct approach since hooks cannot be called conditionally in the parent.

### OneLakeView Component

The `OneLakeView` control accepts:
- `config.mode` — "edit" or "view"
- `config.initialItem` — `{ id, workspaceId, displayName }`
- `config.allowItemSelection` — enables DataHub picker for item switching
- `config.allowedItemTypes` — filters item picker options
- `config.refreshTrigger` — forces re-fetch
- `callbacks.onFileSelected`, `onTableSelected`, `onItemChanged`

**Critical rule from `.ai/commands/item/createItem.md`:** Always use `createItemWrapper()` on `OneLakeStorageClient` — never construct OneLake paths manually.

### Wizard Component

Exists at `Workload/app/components/Wizard/Wizard.tsx`. It is a shared control but has not been used by any item yet — `HelloWorldItem` does not use it. Its API and capabilities must be read directly from source before use.

---

## 6. MANIFEST SYSTEM ANALYSIS

### Template Processing

All manifests use `{{PLACEHOLDER}}` syntax. The build scripts replace placeholders with values from environment `.env` files at build time. This enables multi-environment deployment from single source.

Active placeholders in use:
- `{{WORKLOAD_NAME}}` → `Org.FabricUniversalConnector`
- `{{WORKLOAD_VERSION}}` → `1.100`
- `{{FRONTEND_APPID}}` → **currently empty** (not configured)
- `{{FRONTEND_URL}}` → `http://localhost:3000` (dev)

**Gap:** `FRONTEND_APPID` is empty in all environment files. The workload cannot be registered with a real Fabric tenant without a valid Entra ID application ID.

### WorkloadManifest.xml

```xml
<WorkloadManifestConfiguration SchemaVersion="2.0.0">
  <Workload WorkloadName="{{WORKLOAD_NAME}}" HostingType="FERemote">
    <Version>{{WORKLOAD_VERSION}}</Version>
    <RemoteServiceConfiguration>
      <CloudServiceConfiguration>
        <Cloud>Public</Cloud>
        <AADFEApp><AppId>{{FRONTEND_APPID}}</AppId></AADFEApp>
        <EnableSandboxRelaxation>false</EnableSandboxRelaxation>
        <Endpoints>
          <ServiceEndpoint>
            <Name>Frontend</Name>
            <Url>{{FRONTEND_URL}}</Url>
          </ServiceEndpoint>
        </Endpoints>
      </CloudServiceConfiguration>
    </RemoteServiceConfiguration>
  </Workload>
</WorkloadManifestConfiguration>
```

**Observation:** `HostingType="FERemote"` — this is frontend-only. A backend service endpoint would require `HostingType="Remote"` and an additional `BackendServiceEndpoint`. The `SwitchToRemoteHosting.ps1` script exists to support this migration.

### Product.json — Current State

Currently references only `HelloWorldItem`:
- `createExperience.cards` → 1 card (HelloWorld)
- `recommendedItemTypes` → `["HelloWorld"]`
- Publisher: `"Name of publisher"` (placeholder)
- Support links: all point to `example.com` (placeholders)

**Gap:** `ConnectorItem` is not registered in `Product.json`. Items missing from `createExperience.cards` cannot be created from the Fabric UI.

### Item Manifest Pattern (HelloWorldItem.json)

```json
{
  "name": "HelloWorld",
  "version": "1.100",
  "editor": { "path": "/HelloWorldItem-editor" },
  "icon": { "name": "assets/images/HelloWorldItem_Icon.png" },
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
    "onCreationFailure": { "action": "item.onCreationFailure" },
    "onCreationSuccess": { "action": "item.onCreationSuccess" }
  }
}
```

All item manifests must follow this exact pattern. The `name` field maps directly to the `itemType` in `Product.json` and must be consistent.

---

## 7. ENVIRONMENT CONFIGURATION ANALYSIS

### Current .env.dev Values

```
WORKLOAD_HOSTING_TYPE=FERemote
WORKLOAD_VERSION=1.100
WORKLOAD_NAME=Org.FabricUniversalConnector
ITEM_NAMES=HelloWorld,Connector          ← Connector listed, not implemented
FRONTEND_APPID=                          ← EMPTY — critical gap
FRONTEND_URL=http://localhost:3000
ENVIRONMENT_DISPLAY_NAME_SUFFIX= (dev)
ENABLE_PLAYGROUND=true
BACKEND_APPID=                           ← EMPTY — no backend yet
LOG_LEVEL=DEBUG
ENABLE_MEMORY_MONITORING=false
```

### ITEM_NAMES Critical Finding

`ITEM_NAMES=HelloWorld,Connector` is set in all three environment files (`.env.dev`, `.env.test`, `.env.prod`).

The `BuildManifestPackage.ps1` script uses this variable to determine which item manifests to include in the NuGet package. If `Connector` is listed but `Workload/Manifest/items/ConnectorItem/` does not exist, the build either fails or silently excludes the item.

**This is the single most critical implementation gap in the repository.**

---

## 8. CURRENT ITEMS ANALYSIS

### HelloWorldItem — Complete Implementation Review

| File | Status | Quality | Notes |
|---|---|---|---|
| `HelloWorldItemDefinition.ts` | ✅ Complete | Good | Simple `{ message?: string }` interface |
| `HelloWorldItemEditor.tsx` | ✅ Complete | High | Correct patterns, optimization implemented |
| `HelloWorldItemEmptyView.tsx` | ✅ Complete | Good | Uses `ItemEditorEmptyView` correctly |
| `HelloWorldItemDefaultView.tsx` | ✅ Complete | Good | Left+center layout, correct props |
| `HelloWorldItemRibbon.tsx` | ✅ Complete | High | Definitive ribbon pattern reference |
| `HelloWorldItem.scss` | ✅ Complete | Good | Item-specific styles only |
| `GettingStartedSection.tsx` | ✅ Complete | Good | Custom UI component within item |
| `ItemDetailsSection.tsx` | ✅ Complete | Good | Shows item metadata |
| `HelloWorldItem.json` | ✅ Complete | Good | All required manifest fields |
| `HelloWorldItem.xml` | ✅ Complete | Good | Correct TypeName pattern |
| Route in App.tsx | ✅ Registered | — | `/HelloWorldItem-editor/:itemObjectId` |
| Product.json | ✅ Registered | — | Both cards and recommendedItemTypes |
| Manifest translations | ✅ Present | — | `translations.json` |
| App translations | ✅ Present | — | `translation.json` |

**HelloWorldItemEditor key patterns to replicate in ConnectorItem:**
1. Item reload optimization check (compare `item.id === pageContext.itemObjectId`)
2. `viewSetter` callback for async view transitions post-load
3. `RegisteredNotification[]` declarative message bar pattern
4. `ribbon={(context) => ...}` function pattern (receives `ViewContext`)
5. `EmptyViewWrapper` nested component for `useViewNavigation` hook access

### ConnectorItem — Gap Summary

| Requirement | Status |
|---|---|
| `ConnectorItem/` folder in `items/` | ❌ Missing |
| `ConnectorItemDefinition.ts` | ❌ Missing |
| `ConnectorItemEditor.tsx` | ❌ Missing |
| `ConnectorItemEmptyView.tsx` | ❌ Missing |
| `ConnectorItemDefaultView.tsx` | ❌ Missing |
| `ConnectorItemRibbon.tsx` | ❌ Missing |
| `ConnectorItem.scss` | ❌ Missing |
| `Manifest/items/ConnectorItem/` folder | ❌ Missing |
| `ConnectorItem.json` | ❌ Missing |
| `ConnectorItem.xml` | ❌ Missing |
| Route in `App.tsx` | ❌ Missing |
| `Product.json` registration | ❌ Missing |
| Manifest translations | ❌ Missing |
| App translations | ❌ Missing |
| Ingestion notebook (CRM) | ❌ Missing |
| Ingestion notebook (BC) | ❌ Missing |
| Ingestion notebook (SQL) | ❌ Missing |
| Bronze metadata tables | ❌ Missing |
| CI/CD pipelines | ❌ Missing |

---

## 9. SCRIPTS AND INFRASTRUCTURE ANALYSIS

### Build Scripts

| Script | Purpose | Status |
|---|---|---|
| `BuildManifestPackage.ps1` | Generates NuGet from templates + env vars | ✅ Present |
| `BuildRelease.ps1` | End-to-end release build | ✅ Present |
| `ManifestValidator.ps1` | Schema validation for manifest XML/JSON | ✅ Present |
| `ItemManifestValidator.ps1` | Per-item manifest validation | ✅ Present |
| `WorkloadManifestValidator.ps1` | Workload manifest validation | ✅ Present |

### Setup Scripts

| Script | Purpose |
|---|---|
| `SetupWorkload.ps1` | One-time project initialization |
| `CreateDevAADApp.ps1` | Creates Entra ID application automatically |
| `CreateNewItem.ps1` | Scaffolds new item (copies HelloWorld structure) |
| `CreateJob.ps1` | Scaffolds new job type |
| `SwitchToRemoteHosting.ps1` | Migrates FERemote → Remote hosting |

**Important:** `SwitchToRemoteHosting.ps1` already exists. This confirms the architects anticipated the need for a backend service and built the migration path before it was needed.

### Remote API Helpers (`scripts/Setup/remote/`)

Mature Node.js helper scripts for Fabric REST API operations:
- `authentication.js` + `tokenBuilder.js` + `tokenExchangeService.js` — auth flows
- `fabricApiClient.js` — base HTTP client
- `itemCrudApi.js` — item operations
- `jobsApi.js` + `jobsLogger.js` — job management
- `oneLakeClientService.js` — OneLake operations
- `permissionsApi.js` — permission management
- `endpointResolutionApi.js` — service discovery

These are script-level utilities, not application code. They demonstrate the token exchange flow for backend scenarios but are not structured as importable modules.

---

## 10. IDENTIFIED ARCHITECTURAL PATTERNS

### Pattern 1: Layered Separation of Concerns

```
clients/ → controllers/ → components/ → items/
```

Each layer has a strict responsibility boundary. Items never import from clients directly; they go through controllers. Components never hold business logic. This pattern is consistently enforced.

### Pattern 2: Static View Registration

Views are registered as a data array, not rendered conditionally:

```typescript
const views: RegisteredView[] = [
  { name: 'empty', component: <EmptyView /> },
  { name: 'default', component: <DefaultView /> },
  { name: 'detail', component: <DetailView />, isDetailView: true }
];
```

`ItemEditor` manages all view switching. This decouples navigation logic from view rendering.

### Pattern 3: Declarative Notification Registration

MessageBar notifications are declared as a list, not conditionally rendered:

```typescript
const notifications: RegisteredNotification[] = [
  {
    name: 'warning',
    showInViews: ['default'],
    component: showWarning ? <MessageBar /> : null
  }
];
```

### Pattern 4: Template-Driven Manifest

All manifest files use `{{VARIABLE}}` placeholders replaced at build time from `.env` files. This enables multi-environment promotion without code changes.

### Pattern 5: Function-Pattern Ribbon

```typescript
ribbon={(context: ViewContext) => (
  <MyRibbon viewContext={context} ... />
)}
```

The ribbon receives `ViewContext` as a function parameter, enabling ribbons to show/hide actions based on the current view without maintaining separate state.

### Pattern 6: Item Reload Guard

```typescript
if (pageContext.itemObjectId && item && item.id === pageContext.itemObjectId) {
  return; // Skip reload
}
```

Guards against unnecessary API calls when the same item is already loaded.

### Pattern 7: Multi-Part Item Definition

Item state is stored in multiple named parts:
- `payload.json` — primary configuration (Base64 JSON)
- `.platform` — Fabric metadata
- `{custom}` — additional parts (arbitrary named blobs)

The `convertGetItemResultToWorkloadItem` function handles deserialization of all parts.

---

## 11. IDENTIFIED ARCHITECTURAL GAPS

### Critical Gaps (Blockers)

| Gap | Impact | Priority |
|---|---|---|
| `ConnectorItem` entirely missing | No product value | P0 |
| `FRONTEND_APPID` empty | Cannot register with real Fabric tenant | P0 |
| No ingestion runtime (notebooks) | Core product capability absent | P0 |
| No CI/CD pipelines | Cannot automate delivery | P1 |

### Significant Gaps

| Gap | Impact | Priority |
|---|---|---|
| `backend/` and `backend_2/` empty | Future backend ready but not started | P1 |
| No unit test framework | Code quality risk | P1 |
| Product.json has placeholder content | Cannot submit to marketplace | P1 |
| No Bronze Lakehouse creation logic | Data layer absent | P1 |
| No metadata table initialization | Monitoring impossible | P1 |
| No Connector manifest files | Item cannot appear in Fabric UI | P0 |
| No ConnectorItem route in App.tsx | Router 404 on item open | P0 |

### Minor Gaps

| Gap | Impact | Priority |
|---|---|---|
| `canDeactivate` returns `true` unconditionally | No unsaved-changes guard | P2 |
| Manifest translations still reference "Hello Fabric!" | Wrong branding | P2 |
| No infrastructure-as-code | Manual ISV infra | P2 |
| No telemetry/analytics | Blind to product usage | P2 |
| Wizard component never used | Must validate API before use | P2 |

---

## 12. CONVENTIONS ENFORCED BY THE REPOSITORY

The following conventions are non-negotiable (enforced by `.ai/commands/item/createItem.md`):

1. **Never modify** `Workload/app/components/` — breaks all items
2. **Always use** `ItemEditor` as root container — no custom layouts
3. **Always use** `Ribbon` + `RibbonToolbar` + `createRibbonTabs` — no custom toolbars
4. **Item SCSS** — item-specific styles only, in `[ItemName]Item.scss`, prefixed `.item-name-*`
5. **Tooltip wrapping** — every `ToolbarButton` wrapped in `Tooltip` for accessibility
6. **Content padding** — `ItemEditor` panels have zero padding; view content adds its own
7. **Route naming** — `/{ItemName}Item-editor/:itemObjectId`
8. **Manifest version** — always `"1.100"` (copy exactly from HelloWorld)
9. **Two translation locations** — manifest strings in `Manifest/assets/locales/`; UI strings in `app/assets/locales/`
10. **OneLake** — always use `createItemWrapper()`, never manual path construction
11. **OneLakeView** — use control from `components/OneLakeView`, not sample code
12. **Product.json** — must update BOTH `createExperience.cards` AND `recommendedItemTypes`
13. **ITEM_NAMES** — must update all three `.env` files

---

## 13. READINESS ASSESSMENT

### What Is Production-Ready Today

| Component | Readiness | Notes |
|---|---|---|
| SDK client layer | ✅ Production | All Fabric APIs wrapped and typed |
| Job Scheduler client | ✅ Production | Full CRUD + pagination + helpers |
| ItemCRUD controller | ✅ Production | Multi-part support, optimized reload |
| Base UI components | ✅ Production | ItemEditor, Ribbon, OneLakeView |
| HelloWorldItem | ✅ Production | Complete reference implementation |
| Build scripts | ✅ Production | Template-based, multi-environment |
| Manifest system | ✅ Production | Schema validation included |

### What Must Be Built (Phase 2+)

| Component | Effort | Phase |
|---|---|---|
| ConnectorItem (full UI) | Large | Phase 2 |
| CRM ingestion notebook | Large | Phase 2 |
| Bronze Lakehouse initialization | Medium | Phase 2 |
| Metadata table schema | Small | Phase 2 |
| Business Central notebook | Medium | Phase 3 |
| SQL notebook | Medium | Phase 3 |
| CI/CD pipelines | Medium | Phase 2 |
| Unit test framework | Medium | Phase 2 |
| Marketplace content | Small | Phase 3 |
| Entra ID app registration | Small | Immediate |

---

## 14. SUMMARY OF FINDINGS

### Strengths

1. The SDK client and controller layer is mature, complete, and production-grade — well beyond the Microsoft sample baseline.
2. The base UI component system (ItemEditor, Ribbon, OneLakeView, Wizard) is well-designed and provides strong guardrails.
3. `JobSchedulerClient` is ready to drive automated ingestion scheduling without additional work.
4. The manifest template system cleanly supports multi-environment deployment.
5. The `.ai/commands/item/createItem.md` specification provides a precise, verifiable checklist for item creation that prevents architectural drift.
6. The `SwitchToRemoteHosting.ps1` script confirms the team anticipated the need for a backend service — the evolution path is pre-planned.

### Risks

1. **Zero ingestion capability.** The workload is a UI shell. The entire product value proposition requires implementation from scratch.
2. **`ConnectorItem` is the product.** Its complete absence means the workload currently does nothing marketable.
3. **`FRONTEND_APPID` is unset.** Cannot test against a real Fabric tenant without an Entra ID app registration.
4. **No tests.** Any regression in the UI layer is invisible until manual testing.
5. **No CI/CD.** All deployment is manual, which is a reliability and velocity risk at scale.

### Conclusion

The repository provides an **excellent foundation** with mature tooling and a clean architecture. However, it is currently **pre-product** — a configured and capable platform with no actual product features. Phase 2 must define the complete target architecture to guide implementation. The critical path runs through: ConnectorItem definition → CRM wizard UI → ingestion notebook → Bronze Lakehouse → scheduling → monitoring dashboard.

---

**PHASE 1 COMPLETE**

Output: `.ai/analysis/repository-analysis.md`

Awaiting Phase 2 instruction: Target Architecture
