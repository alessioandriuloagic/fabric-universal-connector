# GitHub Copilot Instructions for Microsoft Fabric Extensibility Toolkit

## 📋 Overview

This file contains **GitHub Copilot-specific** instructions that extend the generic AI guidance found in the `.ai/` folder. All AI tools should first reference the generic instructions, then apply the Copilot-specific enhancements below.

## 🔗 Base AI Instructions

**REQUIRED**: Before using these instructions, always reference the generic AI guidance:

- **Primary Context**: `.ai/context/fabric-workload.md` - Project structure and conventions
- **Platform Knowledge**: `.ai/context/fabric.md` - Microsoft Fabric platform understanding  
- **Available Commands**: `.ai/commands/` - All automation tasks and procedures
  - Item Operations: `.ai/commands/item/` (createItem.md, deleteItem.md)
  - Workload Operations: `.ai/commands/workload/` (runWorkload.md, updateWorkload.md, deployWorkload.md, publishworkload.md)

## 🤖 GitHub Copilot Enhanced Features

### Agent Activation
Use `@fabric` or these keywords for specialized GitHub Copilot assistance:
- `fabric workload` - Extensibility Toolkit-specific development help with autocomplete
- `fabric item` - Item creation with intelligent code generation
- `fabric auth` - Authentication patterns with secure defaults
- `fabric api` - API integration with type inference
- `fabric deploy` - Deployment automation with validation

### Enhanced Capabilities
GitHub Copilot provides additional features beyond generic AI tools:
- 🔮 **Predictive Coding**: Auto-completion for Fabric patterns and TypeScript interfaces
- 🧠 **Context-Aware Suggestions**: Smart suggestions based on current file and cursor position
- ⚡ **Real-time Validation**: Immediate feedback on code quality and Fabric compliance
- 🎯 **Pattern Recognition**: Learns from existing codebase patterns for consistent suggestions
- 📚 **Inline Documentation**: Generates JSDoc comments following Fabric conventions

## 🎯 GitHub Copilot Integration

### Command Reference System
GitHub Copilot integrates with the generic `.ai/commands/` structure:

| **Generic Command** | **GitHub Copilot Enhancement** |
|-------------------|-------------------------------|
| `.ai/commands/item/createItem.md` | Auto-generates 4-file structure with intelligent TypeScript interfaces |
| `.ai/commands/item/deleteItem.md` | Validates dependencies before suggesting removal |
| `.ai/commands/workload/runWorkload.md` | Provides environment validation and startup optimization |
| `.ai/commands/workload/updateWorkload.md` | Suggests configuration updates with impact analysis |
| `.ai/commands/workload/deployWorkload.md` | Validates deployment readiness with security checks |
| `.ai/commands/workload/publishworkload.md` | Ensures production-ready manifest compliance |

### Context Enhancement
Beyond the generic `.ai/context/` files, GitHub Copilot provides:
- **Real-time IntelliSense**: Auto-completion for Fabric APIs and TypeScript definitions
- **Error Prevention**: Immediate feedback on common Fabric development pitfalls
- **Pattern Matching**: Suggests code based on similar implementations in the workspace
- **Dependency Tracking**: Understands relationships between manifest and implementation files

## 🧠 GitHub Copilot Behavioral Enhancements

### Smart Suggestions
- **File Creation**: When creating items, automatically suggests the 4-file pattern structure
- **Import Resolution**: Auto-imports Fabric platform types and client libraries
- Prefer components from `@fluentui/react-components` (v9) over `@fluentui/react` (v8). Replace imports like `import { DefaultButton } from '@fluentui/react'` with `import { Button } from '@fluentui/react-components'`. Verify API and prop differences (appearance, tokens, and shorthands) when migrating components.
- **Ribbon Pattern**: ALWAYS suggests `homeToolbarActions` (mandatory) + optional `additionalToolbars` pattern. Use `createSaveAction()`, `createSettingsAction()` factories from components/ItemEditor
- **Toolbar Components**: ALWAYS suggests `Tooltip` + `ToolbarButton` pattern for toolbar actions. Auto-imports both from `@fluentui/react-components` and wraps ToolbarButtons in Tooltips with proper accessibility attributes
- **OneLakeStorageClient**: ALWAYS use `createItemWrapper()` when working with OneLake storage in an item context. Never use direct OneLakeStorageClient methods with manual path construction
- **OneLakeView**: ALWAYS use component from `components/OneLakeView`, not sample code. Initialize with `initialItem` config for content display
- **Error Recovery**: Provides specific fixes for common Fabric authentication and manifest issues
- **Code Completion**: Understands Fabric-specific patterns like `callNotificationOpen()` and `saveItemDefinition()`

### Workspace Intelligence
- **Manifest Sync**: Detects when implementation changes require manifest updates
- **Environment Awareness**: Suggests appropriate `.env` configurations based on current context
- **Build Validation**: Predicts build issues before they occur
- **Routing Updates**: Automatically suggests route additions when new items are created

## 🚀 GitHub Copilot Quick Actions

### Smart Code Generation
Instead of manual file creation, GitHub Copilot can generate complete structures:

```typescript
// Type "fabric item create MyCustom" to generate:
// - MyCustomItemModel.ts with intelligent interface
// - MyCustomItemEditor.tsx with Fluent UI components
// - MyCustomItemEditorEmpty.tsx with onboarding flow
// - MyCustomItemEditorRibbon.tsx with action buttons
```

### Enhanced Development Commands
GitHub Copilot understands context-aware shortcuts:

```powershell
# Smart environment detection with .env-based configuration
fabric dev start    # Automatically uses .env.dev configuration

# Intelligent build with validation
fabric build check  # Pre-validates templates and manifest generation

# Context-aware deployment
fabric deploy prod   # Uses .env.prod for environment-specific manifests
```

### Auto-completion Patterns
GitHub Copilot recognizes Fabric patterns and suggests:
- **API Calls**: Complete authentication and error handling
- **Component Structure**: Fluent UI patterns with proper TypeScript
- **Ribbon Components**: Always creates `homeToolbarActions` array (mandatory) with `createSaveAction()`, `createSettingsAction()` factories, plus optional `additionalToolbars` array for complex items
- **Toolbar Integration**: Mandatory `Tooltip` + `ToolbarButton` patterns for all toolbar implementations
- **OneLake Storage**: Always creates `itemWrapper = oneLakeClient.createItemWrapper({id, workspaceId})` for item-scoped operations
- **OneLake Explorer**: Always use component from `components/OneLakeView`, not sample code
- **ItemEditor View Registration**: ALWAYS use static view registration pattern with `useViewNavigation()` hook. Define views as static array like ribbon actions
- **ItemEditor Initial View**: ALWAYS use `getInitialView` function for data-dependent view determination instead of static `initialView`. Called automatically when loading completes
- **ItemEditor Scrolling**: NEVER implement scrolling in item views. ItemEditor center panel handles ALL overflow with automatic vertical scrolling. Items should use `height: auto` for natural growth
- **ItemEditor Notification Registration**: ALWAYS use static messageBar registration pattern. Define messageBar as static array with `showInViews` to control visibility
- **View Navigation**: ALWAYS suggests `const { setCurrentView, goBack } = useViewNavigation()` in view wrapper components for navigation between views (hook is part of ItemEditorDefaultView module)
- **ItemEditorDefaultView**: Always suggests two-panel layouts with proper `left`/`center` panel configurations, resizable splitters, and collapsible panels when appropriate
- **Panel Usage Patterns**: 
  - **Left Panel (Optional)**: For navigation trees, OneLakeView, file explorers, and secondary views (list views, catalog browsers, workspace explorers)
  - **Center Panel (Required)**: For main content, editors, and primary workspace
- **Detail View Navigation**: Always use ItemEditorDetailView component with `isDetailView: true` for L2 drill-down pages (detail records, item properties, configuration screens)
- **Empty View Pattern**: Use ItemEditorEmptyView for items used for the first time (no definition/state) with initial call-to-action buttons to guide users through setup
- **Item Properties & Configuration**: Use ItemSettings pattern for general item properties (version, endpoint configuration, descriptions). This creates a separate section in the settings flyout opened through the settings ribbon action. Item names and descriptions are managed there by default.
- **Panel Configuration**: Suggests `collapsible: true`, proper panel titles, min/max width constraints, and accessibility labels for complex layouts
- **Manifest Updates**: Template processing with placeholder replacement
- **Route Configuration**: Automatic route registration
- **Environment Management**: .env-based configuration patterns

### Workspace-Aware Features
- **File Relationships**: Understands manifest template ↔ implementation dependencies
- **Environment Detection**: Suggests appropriate configurations for dev/test/prod
- **Template Processing**: Recognizes placeholder patterns like `{{WORKLOAD_NAME}}`
- **Error Resolution**: Provides specific fixes for Fabric development issues
- **Pattern Learning**: Adapts suggestions based on existing codebase patterns

---

## � Reference Architecture

For complete understanding, GitHub Copilot users should reference:
- **Generic Foundation**: All files in `.ai/context/` and `.ai/commands/`
- **Copilot Enhancements**: This file's specific GitHub Copilot features
- **Live Workspace**: Current implementation patterns and recent changes

This dual approach ensures consistency across all AI tools while providing GitHub Copilot users with enhanced, context-aware development assistance.

## Response Guidelines
- Add a timestamp (format: `YYYY-MM-DD HH:MM UTC`) at the end of each response
- Clean up unsuccessful code attempts immediately when finding the correct solution
- Only leave changes that actually contribute to the working solution


# Fabric Universal Connector — GitHub Copilot Instructions

> **File location in repo:** `.github/copilot-instructions.md`
> Works also as `AGENTS.md` (root) for multi-agent support and `CLAUDE.md` for Claude Code.

---

## Project Overview

This repository contains the **Fabric Universal Connector**, a Microsoft Fabric Custom Workload (ISV)
that enables no-code integration from ERP/CRM systems (Business Central, Dynamics 365, Salesforce, SAP)
into Microsoft Fabric via Open Mirroring and OneLake.

The product is distributed via the **Microsoft Fabric Workload Hub** and follows the
**Microsoft Fabric Extensibility Toolkit** architecture.

---

## Repository Structure

```
/
├── .github/
│   ├── copilot-instructions.md       ← YOU ARE HERE
│   └── instructions/
│       ├── backend.instructions.md
│       ├── frontend.instructions.md
│       └── connectors.instructions.md
├── backend/                          ← Python FastAPI (Workload Backend)
│   ├── src/
│   │   ├── main.py
│   │   ├── api/                      ← Fabric Item Lifecycle endpoints (MANDATORY)
│   │   │   └── item_lifecycle.py
│   │   ├── connectors/               ← Connector Framework
│   │   │   ├── base.py               ← ConnectorBase abstract class
│   │   │   ├── business_central.py
│   │   │   ├── dynamics365.py
│   │   │   ├── salesforce.py
│   │   │   └── sap.py
│   │   ├── open_mirroring/           ← Open Mirroring Writer
│   │   │   ├── writer.py
│   │   │   └── schema_mapper.py
│   │   ├── auth/                     ← Entra ID multi-tenant token validation
│   │   │   └── token_validator.py
│   │   ├── scheduler/                ← Webhook renewal + fallback poll jobs
│   │   │   └── jobs.py
│   │   └── models/                   ← Pydantic v2 models
│   │       ├── change_event.py
│   │       └── connector_config.py
│   ├── tests/
│   └── requirements.txt
├── frontend/                         ← React + Fluent UI (Workload Frontend)
│   ├── src/
│   │   ├── index.tsx
│   │   ├── components/
│   │   │   ├── SourceConfig/         ← Step 1: source system + credentials
│   │   │   ├── TableMapping/         ← Step 2: entity/table selection
│   │   │   ├── ScheduleConfig/       ← Step 3: sync mode + frequency
│   │   │   └── SyncMonitor/          ← Monitoring dashboard
│   │   └── hooks/
│   │       ├── useFabricHost.ts      ← Workload Client SDK wrapper
│   │       └── useBackendApi.ts      ← ISV backend API calls
│   ├── package.json
│   └── vite.config.ts
├── manifest/                         ← Fabric Workload Manifest
│   └── manifest.json
└── docs/
    └── architecture.md
```

---

## Architecture Principles — Never Violate These

### 1. Connector Framework — Always Extend `ConnectorBase`

Every new source system MUST implement the abstract interface in `backend/src/connectors/base.py`.
Never add source-specific logic directly to the API handlers or the Open Mirroring writer.

```python
# CORRECT — implement the interface
class NewSystemAdapter(ConnectorBase):
    async def authenticate(self) -> bool: ...
    async def discover_entities(self) -> list[EntityMetadata]: ...
    async def subscribe_changes(self, entities: list[str]) -> None: ...
    async def handle_incoming_event(self, raw_payload: dict) -> list[ChangeEvent]: ...
    async def fetch_record(self, entity: str, record_id: str) -> dict: ...
    async def initial_load(self, entity: str) -> AsyncIterator[list[dict]]: ...
    async def renew_subscriptions(self) -> None: ...

# WRONG — never do this
@app.post("/webhook/newsystem")
async def handle_newsystem(payload: dict):
    # inline source-specific logic here ← forbidden
```

### 2. ChangeEvent — The Only Internal Currency

All connectors normalize their events to `ChangeEvent` before anything else touches the data.
The Open Mirroring Writer only accepts `list[ChangeEvent]` — it never knows which source system produced them.

```python
# models/change_event.py — do not add source-specific fields here
@dataclass
class ChangeEvent:
    source_system: str      # "bc" | "d365" | "salesforce" | "sap"
    tenant_id: str
    item_id: str
    entity_type: str
    record_id: str
    change_type: str        # "insert" | "update" | "delete"
    timestamp: datetime
    payload: dict | None    # None = must be fetched via fetch_record()
```

### 3. Fabric Item Lifecycle — All 4 Endpoints Are Mandatory

The backend MUST implement these endpoints exactly as specified by the Fabric OpenAPI contract.
Do not rename, remove, or restructure them. Fabric will call them — if they are missing, the workload breaks.

```
POST   /workload/item/create
GET    /workload/item/{itemId}
PUT    /workload/item/{itemId}
DELETE /workload/item/{itemId}
```

When an item is deleted, the handler MUST: cancel all active webhook subscriptions on the source system,
delete secrets from Key Vault, and clean up any scheduled jobs. Never leave orphan subscriptions.

### 4. Secrets Never in Item Payload

Configuration stored in the Fabric item payload (via Fabric Item API) must NEVER contain secrets.
Credentials (client secrets, API keys, passwords) go to Azure Key Vault only.

```python
# CORRECT
item_payload = {
    "bc_url": config.bc_url,           # OK — not a secret
    "company_id": config.company_id,   # OK — not a secret
    "tables": config.selected_tables,  # OK — not a secret
    "sync_mode": config.sync_mode      # OK — not a secret
}
await key_vault.set_secret(
    f"{tenant_id}/{item_id}/credentials",
    config.credentials.model_dump_json()  # secrets go here only
)

# WRONG
item_payload = {
    "client_secret": "abc123",  # ← NEVER
    "api_key": "xyz789"         # ← NEVER
}
```

### 5. Auth — Always Validate Entra Token, Always Check Tenant Isolation

Every backend endpoint (except the public webhook receiver validation handshake) MUST:
1. Validate the Bearer token from the Fabric host (MSAL, multi-tenant).
2. Extract `tid` (tenant ID) from the token.
3. Verify that the `itemId` in the request belongs to that `tid`. Never serve cross-tenant data.

```python
# CORRECT
@app.get("/connector/{item_id}/status")
async def get_status(item_id: str, token: EntraToken = Depends(validate_token)):
    await assert_item_belongs_to_tenant(item_id, token.tid)  # mandatory
    ...

# WRONG — no auth check
@app.get("/connector/{item_id}/status")
async def get_status(item_id: str):
    ...
```

### 6. Webhook Subscriptions Expire — Always Schedule Renewal

Business Central webhook subscriptions expire after 3 days if not renewed.
Dynamics 365 subscriptions also have expiry. The scheduler MUST renew all active subscriptions
every 2 days. Never assume a subscription persists indefinitely.

```python
# scheduler/jobs.py — this job must always exist and be running
@scheduler.scheduled_job("interval", days=2, id="renew_bc_subscriptions")
async def renew_all_bc_subscriptions():
    for customer in await get_all_active_customers():
        adapter = BCAdapter(customer.config)
        await adapter.renew_subscriptions()
```

---

## Backend — Python Conventions

- **Python version:** 3.11+
- **Framework:** FastAPI with Uvicorn. Use `async`/`await` everywhere — no blocking calls.
- **Models:** Pydantic v2. Use `model_dump()` not `dict()`. Use `model_validate()` not `parse_obj()`.
- **HTTP client:** `httpx.AsyncClient` only. Never use `requests` (it is blocking).
- **Dependency injection:** Use FastAPI `Depends()` for auth, config, and adapter resolution.
- **Error handling:** Always raise `HTTPException` with meaningful status codes. Log errors with context (tenant_id, item_id). Never swallow exceptions silently.
- **Logging:** Use Python `logging` with structured fields. Always include `tenant_id` and `item_id` in log records.
- **Tests:** `pytest` + `pytest-asyncio`. Mock external HTTP calls with `respx`. Minimum coverage for connector adapters: 80%.

```python
# CORRECT async pattern
async with httpx.AsyncClient() as client:
    response = await client.get(url, headers=headers)
    response.raise_for_status()

# WRONG — blocking
import requests
response = requests.get(url)  # ← never use in FastAPI handlers
```

---

## Frontend — React + Fluent UI Conventions

- **Framework:** React 18 with TypeScript. Strict mode enabled.
- **UI library:** Fluent UI v9 (`@fluentui/react-components`) only. Do not introduce other UI libraries.
- **State management:** React `useState` and `useReducer` for local state. No Redux. No Zustand.
- **Fabric integration:** All Fabric host interactions go through `useFabricHost.ts` hook only.
  Never call `window.parent.postMessage` directly — use the Workload Client SDK.
- **Backend calls:** All ISV backend calls go through `useBackendApi.ts` hook only.
  Never call `fetch()` or `axios` directly from components.
- **No forms tag:** Never use HTML `<form>` elements. Use button `onClick` handlers instead.
- **Wizard pattern:** The configuration UI is a multi-step wizard. Each step is an independent component
  in its own folder under `src/components/`. Steps do not import from each other.
- **Error states:** Every async operation must have a loading state and an error state rendered in the UI.
  Never leave the user staring at a spinner with no feedback on failure.

```tsx
// CORRECT — Fluent UI components, no form tag
<Field label="Environment URL" required>
  <Input
    value={url}
    onChange={(_, data) => setUrl(data.value)}
    placeholder="https://api.businesscentral.dynamics.com/..."
  />
</Field>
<Button appearance="primary" onClick={handleTestConnection} disabled={isTesting}>
  {isTesting ? <Spinner size="tiny" /> : "Test Connection"}
</Button>

// WRONG
<form onSubmit={handleSubmit}>   {/* ← never */}
  <input type="text" />
  <button type="submit">Test</button>
</form>
```

---

## Open Mirroring — File Format Rules

These rules come from the Fabric Open Mirroring spec. Violating them silently breaks replication.

- Initial load files: do NOT include `__rowMarker__` column. Fabric treats the whole file as INSERT.
- Incremental files: `__rowMarker__` column MUST be the LAST column in the Parquet schema.
- `__rowMarker__` values: `0` = Insert, `1` = Update, `2` = Delete, `4` = Upsert.
- File names: 20-digit zero-padded sequential integers (`00000000000000000001.parquet`).
- File sequence must be monotonically increasing. Never reuse or skip numbers.
- For delete rows: only key columns are required; data columns can be NULL.
- Updated rows must contain ALL columns (full row), not just changed fields.

```python
# CORRECT incremental file — __rowMarker__ last
schema = pa.schema([
    pa.field("CustomerId", pa.string()),
    pa.field("Name", pa.string()),
    pa.field("Email", pa.string()),
    pa.field("__rowMarker__", pa.int32()),  # ← always last
])

# WRONG — __rowMarker__ not last
schema = pa.schema([
    pa.field("__rowMarker__", pa.int32()),  # ← breaks replication
    pa.field("CustomerId", pa.string()),
])
```

---

## Connector-Specific Rules

### Business Central
- Use API v2.0 endpoints only. API v1.0 is legacy — do not use it.
- Discover webhook-supported entities via `GET .../webhookSupportedResources?$filter=resource eq 'v2.0*'`
  before registering subscriptions. Never hardcode entity lists.
- BC webhook notifications do NOT include record data — they include only the entity ID and change type.
  Always fetch the full record via a subsequent OData GET after receiving a notification.
- BC debounces notifications by 30 seconds. Do not expect real-time delivery — design accordingly.
- Micro-batch: buffer incoming BC events for 30–60 seconds, then write a single Parquet file to the
  landing zone. Never write one file per notification.

### Dynamics 365 / Dataverse
- Use Dataverse webhooks. They include full record payload (`PostEntityImages`) — no subsequent fetch needed.
- Register webhooks via the Dataverse Plugin Registration Tool API, not manually.
- Use `MessageName` from the payload for change type: `Create`, `Update`, `Delete`.

### Salesforce
- Use Salesforce Change Data Capture (CDC) via Streaming API (CometD protocol).
- CDC is a persistent streaming connection, not a webhook endpoint. The backend maintains a long-lived
  async listener loop — do not confuse this with HTTP webhook handling.
- Enable CDC per object via Salesforce setup before subscribing to `/data/{Object}ChangeEvent` channels.
- Salesforce CDC events include the full changed fields only (not full row). Fetch the full record
  before writing to Open Mirroring to guarantee complete rows on UPDATE events.

### SAP
- SAP S/4HANA Cloud: use SAP Event Mesh (Business Events) with webhook delivery if available.
- SAP Business One / SAP on-premise: no native push — use scheduled pull with watermark.
  Store watermark per entity in a persistent store (not in-memory). Use `lastModifiedDateTime` or
  equivalent audit field. Always handle the case where the source has no audit timestamp.
- Never assume SAP versions are consistent across customers. Always check capabilities at connection time.

---

## Multi-Tenancy Rules — Critical for SaaS

- Every database/storage key must be prefixed with `{tenant_id}/{item_id}/`.
- Every log line must include `tenant_id` and `item_id` as structured fields.
- Webhook endpoints receive events from all customers. Always resolve the customer context from the
  URL path (`/webhook/{source}/{item_id}`) and validate the `clientState` secret before processing.
- Key Vault secret names: `{tenant_id}/{item_id}/credentials` — never use flat names.
- Never share connection pools, caches, or scheduler state between tenants.

---

## What NOT to Generate

- Do not generate Spark notebooks or PySpark code. The Open Mirroring engine handles Delta conversion.
  This project does not own any Spark jobs.
- Do not generate Azure Data Factory pipelines. This project does not use ADF.
- Do not generate AL (Business Central extension) code. The product works with standard BC APIs only.
- Do not generate any SQL that targets the Fabric Warehouse or SQL endpoint directly.
  Data lands via Open Mirroring — downstream transformations are the customer's responsibility.
- Do not use `localStorage` or `sessionStorage` in the frontend. The workload runs in an iFrame
  with strict sandboxing — browser storage APIs are not available.
- Do not introduce new npm packages without checking compatibility with the Workload Client SDK iFrame sandbox.
- Do not add `<form>` elements in the frontend under any circumstances.

---

## Key External References

- Fabric Extensibility Toolkit: https://learn.microsoft.com/fabric/extensibility-toolkit/extensibility-toolkit-overview
- Fabric Extensibility Architecture: https://learn.microsoft.com/fabric/extensibility-toolkit/architecture
- Fabric Backend Setup (Python): https://learn.microsoft.com/fabric/workload-development-kit/back-end-set-up
- Open Mirroring Overview: https://learn.microsoft.com/fabric/mirroring/open-mirroring
- Open Mirroring Landing Zone Format: https://learn.microsoft.com/fabric/mirroring/open-mirroring-landing-zone-format
- BC Webhook API v2.0: https://learn.microsoft.com/dynamics365/business-central/dev-itpro/api-reference/v2.0/dynamics-subscriptions
- Fabric Workload Hub Publishing: https://learn.microsoft.com/fabric/workload-development-kit/publish-workload-flow
- Fabric Starter Kit (GitHub): https://aka.ms/fabric-extensibility-starter-kit
- Microsoft Graph API (for auth): https://learn.microsoft.com/azure/active-directory/develop/v2-oauth2-auth-code-flow 