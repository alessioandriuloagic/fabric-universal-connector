# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Fabric Universal Connector** — a Microsoft Fabric Extensibility Toolkit workload for enterprise data ingestion. It is a multi-tenant, modular, metadata-driven platform that ingests data from Dataverse/Dynamics 365 CRM, Business Central, and SQL Server into Fabric Lakehouses.

The workload includes:
- **Frontend**: React/TypeScript UI running in Fabric portal (FERemote iframe)
- **Backend**: FastAPI Python service for job orchestration
- **Runtime**: Python connector library deployed as Fabric notebooks
- **Manifest**: XML/JSON configuration for Fabric integration

## Repository Layout (top-level)

| Path | Purpose |
|------|---------|
| `Workload/` | Frontend — React/TypeScript, Fabric SDK, Fluent UI |
| `backend/` | FastAPI job-orchestration service |
| `connector/runtime/` | Python package `agic-fabric-connector` (Spark notebook runtime) |
| `scripts/` | PowerShell DevOps scripts (Setup/, Build/, Run/, Deploy/) |
| `.ai/` | AI context & automation commands for Copilot/Claude |
| `Start-Workload.ps1` | One-command local launcher (dev server + DevGateway) |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Redux Toolkit, Fluent UI (v8 + v9), webpack 5, i18next |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, Pydantic |
| **Data** | Delta Lake, PyArrow, Pandas, SQLAlchemy |
| **Auth** | Entra ID (OAuth 2.0), JWT validation, MSAL Python |
| **Cloud** | Azure Storage (OneLake), Azure App Service, Azure Container Apps, Azure Key Vault |
| **Build** | PowerShell 7+, Node.js, .NET (NuGet), webpack, env-cmd |

## Build & Development Commands

### Frontend (Workload/)

```powershell
# Start local dev server (webpack dev server on http://localhost:3000)
npm start
# or from repo root:
.\scripts\Run\StartDevServer.ps1

# Build for environment
npm run build:test     # Test/staging build
npm run build:prod     # Production build (minified, optimized)

# Type-check only (no ESLint config in project)
npx tsc --noEmit

# Build manifest package (generates NuGet from templates)
.\scripts\Build\BuildManifestPackage.ps1 -Environment prod

# Full release (manifest + frontend)
.\scripts\Build\BuildRelease.ps1 -WorkloadName "Org.YourWorkload" -FrontendAppId "{guid}" -Environment prod
```

### Backend (backend/)

```bash
# Install dependencies
pip install -r requirements.txt

# Run local FastAPI server (development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Build Docker container
docker build -t fabric-connector:latest .

# Run tests (if test suite exists)
pytest tests/
```

### Connector Runtime (connector/runtime/)

```bash
# Build Python package (agic-fabric-connector wheel)
pip install build
python -m build

# Install locally for development
pip install -e .
```

### Initial Setup

```powershell
# First-time project setup (creates .env files, Entra apps)
.\scripts\Setup\SetupWorkload.ps1 -WorkloadName "Org.YourWorkload" -WorkloadDisplayName "Your Display Name"

# Developer environment setup (configures local DevGateway)
.\scripts\Setup\SetupDevEnvironment.ps1

# Start both dev server and DevGateway (one-command local launch)
.\Start-Workload.ps1
```

## Architecture Patterns

### Frontend Item Structure (Microsoft Fabric SDK Convention)

**HelloWorldItem** (`Workload/app/items/HelloWorldItem/`) is the canonical reference sample. It follows the minimal 4-file pattern:

| File | Role |
| --- | --- |
| `HelloWorldItemDefinition.ts` | Data model/state interface |
| `HelloWorldItemEditor.tsx` | Main container (uses `ItemEditorDefaultView`) |
| `HelloWorldItemRibbon.tsx` | Toolbar (mandatory `homeToolbarActions` + optional `additionalToolbars`) |
| `HelloWorldItemEmptyView.tsx` | First-run onboarding (no config yet) |

**ConnectorItem** (`Workload/app/items/ConnectorItem/`) is more complex and adds subdirectories:

- `wizard/` — 8-step configuration wizard: `WizardSourceStep` → `WizardModuleStep` → `WizardAuthStep` → `WizardConfigStep` → `WizardEntityStep` → `WizardScheduleStep` → `WizardStorageStep` → `WizardReviewStep`
- `ribbon/` — ribbon actions factory (`ribbonActionFactory.ts` + `ConnectorItemRibbon.tsx`)
- `dashboard/` — post-config dashboard: `ConnectorDashboard`, `RunHistoryTable`, `RunDetailView`, `EntityStatusList`, `EntityDetailView`

**Adding a new connector type** requires only one change: push a new `ConnectorDefinition` into `CONNECTOR_REGISTRY` in `Workload/app/items/ConnectorItem/wizard/connectorRegistry.ts`. The wizard UI, validation pipeline, and state management are entirely data-driven from that registry.

**Key Constraints:**
- Use Fluent UI v9 components (`@fluentui/react-components`) preferentially; v8 only as fallback
- Ribbon MUST have `homeToolbarActions` array with Save + Settings actions
- Toolbar buttons wrapped in `Tooltip + ToolbarButton` from Fluent v9
- `ItemEditorDefaultView` handles scrolling — never implement scrolling in views
- `ItemEditorDetailView` for L2 drill-down (with automatic back navigation)
- `ItemSettings` pattern for general item properties (separate flyout from editor)
- Use `oneLakeClient.createItemWrapper()` for OneLake operations, never direct path construction
- Item views registered as static array with `getInitialView()` for data-dependent initialization

### Frontend Initialization (index.ts → index.worker.ts → index.ui.tsx)

- **index.ts**: Bootstrap entry point, handles OAuth redirect URI, initializes worker + UI threads
- **index.worker.ts**: Background tasks, action handlers (`item.onCreationSuccess`, `getItemSettings`)
- **index.ui.tsx**: React rendering, navigation, item CRUD operations

### Backend Module Architecture

The connector has independent, pluggable modules for each source system:

```python
# Base abstraction (shared by all modules)
class BaseConnector(ABC):
    def load_config(self, item_definition: ConnectorItemDefinition) -> None
    async def authenticate(self) -> None
    async def ingest(self) -> RunResult
    # ... retry logic, error handling, metadata tracking

# CRM module — Dataverse/Dynamics 365 (Change Tracking API + OData)
class CRMConnector(BaseConnector)

# Business Central module — OData v4 API
class BCConnector(BaseConnector)

# SQL module — JDBC / Fabric Connection / CDC
class SQLConnector(BaseConnector)
```

**Module Isolation Rules:**
- Each module is independently deployable
- Shared infrastructure: config loading, auth, retry, Bronze writer, metadata tracking
- No module-specific logic bleeds into shared base
- Adding a new module requires: new subclass in `connectors/`, new entity catalog (if needed), new notebook template

### Data Flow & Storage

```
USER (Fabric Portal)
  ↓
  ConnectorItem (Item Definition: JSON config Base64-encoded)
  ↓
  Fabric Job Scheduler
  ↓
  Fabric Notebook: connector_runtime_{module}.ipynb (in customer workspace)
  ↓
  agic-fabric-connector Python module
  ├─ Load config from item definition
  ├─ Authenticate (Fabric Connection / Key Vault reference)
  ├─ Connect to source (Dataverse API / BC OData / SQL JDBC)
  ├─ Extract incrementally (Change Tracking / pagination)
  └─ Append to Bronze Lakehouse (Delta Lake)
  ↓
  Bronze Layer (OneLake — customer's own storage)
  ├─ bronze_crm/ → contact, lead, msdynmkt_*, _meta/
  ├─ bronze_bc/ → customers, _meta/
  └─ bronze_sql/ → user-defined tables, _meta/
  
Metadata tracked in _meta/:
  ├─ _connector_runs     (run audit log)
  ├─ _watermarks         (incremental sync checkpoints)
  ├─ _schema_evolution   (schema change history)
  └─ _error_log          (error tracking for observability)
```

### Configuration & Templating

- **Environment Variables**: `.env.dev`, `.env.test`, `.env.prod` (committed to repo)
- **Template Placeholders**: `{{WORKLOAD_NAME}}`, `{{WORKLOAD_VERSION}}` in manifest XML
- **Build-Time Replacement**: Manifest generation replaces placeholders from appropriate .env file
- **Item Configuration**: ConnectorConfig stored as Base64 JSON in item definition (no hardcoded values)
- **Secrets**: Never stored in code; resolved at runtime via Fabric Connections or Azure Key Vault references

### Security & Authentication

- **Frontend ↔ Fabric**: Entra ID OAuth 2.0 integration (SDK-managed)
- **Backend ↔ Fabric**: JWT validation (FABRIC_TENANT_ID + BACKEND_APP_ID environment variables)
- **Source System Auth**: 
  - Dataverse: OAuth via MSAL
  - Business Central: API key from Fabric Connection
  - SQL: Connection string from Fabric Connection or Key Vault
- **OneLake Access**: Azure managed identity (app-authenticated via FABRIC_TENANT_ID)
- **Rate Limiting**: Per-IP slowapi middleware on backend

## Key Coding Patterns

### Frontend Controller Pattern

Controllers encapsulate business logic for item operations:

```typescript
// controller/ItemCRUDController.ts
export async function callGetItem(workloadClient, id) { ... }
export async function callCreateItem(workloadClient, definition) { ... }
export async function callSaveItemDefinition(workloadClient, id, definition) { ... }

// controller/JobSchedulerController.ts
export async function callRunItemJob(workloadClient, itemId) { ... }

// controller/NotificationController.ts
export async function callNotificationOpen(workloadClient, notification) { ... }
```

### Backend Job Orchestration (FastAPI)

```python
# app/api/jobs.py — Jobs API (implements Fabric IJobsController)
@router.post("/v1/items/{itemId}/runJob")
async def run_job(itemId: str, job_request: JobRunRequest) -> JobRunResponse:
    # 1. Extract config from job_request (references item definition)
    # 2. Route to appropriate module connector (CRM/BC/SQL)
    # 3. Execute async ingestion
    # 4. Track run state (in-memory or Azure Table Storage)
    # 5. Return job ID for monitoring

# Job state persisted via JobTracker (in-memory dev / Azure Table Storage prod)
```

### Manifest Processing

The manifest is NOT static. It's processed at build time:

```xml
<!-- Workload/Manifest/WorkloadManifest.xml (template) -->
<Workload name="{{WORKLOAD_NAME}}" version="{{WORKLOAD_VERSION}}">
  <FrontendEndpoint>https://connector.agic.technology</FrontendEndpoint>
  <BackendEndpoint>https://backend-{environment}.azurewebsites.net</BackendEndpoint>
</Workload>

<!-- After build: becomes environment-specific manifest in build/Manifest/ -->
```

Item manifests similarly reference placeholders.

## Development Workflow

1. **Setup Once**:
   ```powershell
   .\scripts\Setup\SetupWorkload.ps1 -WorkloadName "Org.Dev"
   .\scripts\Setup\SetupDevEnvironment.ps1
   npm install  # Inside Workload/
   ```

2. **Daily Dev**:
   ```powershell
   .\Start-Workload.ps1  # Starts webpack dev server + DevGateway
   ```
   - Frontend hot-reloads on code changes
   - Manifest auto-regenerated on DevGateway startup

3. **Test Item Creation**:
   - Navigate to Fabric workspace
   - Create new ConnectorItem or HelloWorldItem
   - Item editor loads from http://localhost:3000

4. **Backend Development**:
   ```bash
   cd backend
   uvicorn app.main:app --reload  # Runs on http://localhost:8000
   ```

5. **Build & Release**:
   ```powershell
   .\scripts\Build\BuildRelease.ps1 -Environment prod -WorkloadName "Org.MyApp" -FrontendAppId "{guid}"
   # Outputs to release/ directory: manifest NuGet + frontend bundle
   ```

## Important Files & Configuration

### Critical Configuration Files

- **Workload/Manifest/Product.json**: Workload metadata, item types, create experience, publisher info
- **Workload/Manifest/WorkloadManifest.xml**: Workload endpoints, versions, integration points
- **Workload/Manifest/items/{Item}/*.json/.xml**: Per-item metadata
- **backend/requirements.txt**: Python dependencies (FastAPI, Pydantic, Azure SDKs, Delta Lake)
- **backend/.env.example**: Backend environment template
- **connector/runtime/pyproject.toml**: Python package metadata for agic-fabric-connector wheel

### Environment Variables

**Frontend (.env.dev, .env.test, .env.prod):**
```
WORKLOAD_NAME=Org.YourWorkload
ITEM_NAMES=HelloWorld,Connector
WORKLOAD_VERSION=1.0.0
LOG_LEVEL=DEBUG
ENABLE_PLAYGROUND=false
```

**Backend:**
```
FABRIC_TENANT_ID={ISV tenant ID for JWT validation}
BACKEND_APP_ID={Entra app registration ID}
LOG_LEVEL=INFO
USE_TABLE_STORAGE=false          # true = persist job state in Azure Tables
ENABLE_SWAGGER=false             # true = expose /docs endpoint
```

## Architectural Decision Records (ADRs)

Key decisions captured in `.ai/architecture/target-architecture.md`:

1. **FERemote Hosting**: Frontend served from ISV infrastructure (connector.agic.technology), not embedded
2. **Notebook Runtime**: Ingestion code runs in customer's Fabric Spark compute via deployed notebooks
3. **Bronze Immutability**: Raw source data never modified; all CDC operations append-only
4. **Config-Driven**: All behavior parameterized via item definition JSON; no hardcoded entity lists
5. **Module Isolation**: CRM, BC, SQL modules are independent and composable
6. **Tenant Isolation**: Each customer's data isolated in their own OneLake workspace
7. **Secret Management**: Zero trust — credentials never in code; resolved via Fabric Connections or Key Vault

## AI Context Files

Always reference these before implementing features:

- `.ai/AGENTS.md` — product vision and architectural principles
- `.ai/context/fabric-workload.md` — SDK conventions (item patterns, ribbon, views)
- `.github/copilot-instructions.md` — full code-generation patterns and constraints

## Testing & Debugging

### Frontend Debugging

- **DevTools**: Open browser DevTools (F12), inspect network requests to DevGateway
- **Console Logging**: All major operations log to console (bootstrap, navigation, actions, errors)
- **Playground Routes**: Development-only routes for testing components (conditionally enabled)
- **Environment Configs**: Change .env.dev to adjust log levels, enable Swagger, etc.

### Backend Debugging

- **Swagger UI**: Set `ENABLE_SWAGGER=true` to access `/docs` endpoint (FastAPI auto-generated)
- **Structured Logging**: All backend logs are JSON format (via python-json-logger) for easy parsing
- **Local Testing**: Run `uvicorn app.main:app --reload` for instant code reload on changes

### Common Issues

1. **"node_modules not found"**: Run `npm install` inside Workload/ directory
2. **Manifest build fails**: Verify .env.{dev|test|prod} files exist and contain required variables
3. **JWT validation fails**: Ensure FABRIC_TENANT_ID and BACKEND_APP_ID are set if testing backend auth
4. **OneLake access denied**: Verify Azure managed identity has "Contributor" role on target workspace
5. **Port conflicts**: Dev server uses 3000, DevGateway uses 6200+, backend uses 8000 — ensure available

## Release & Deployment

### Release Artifact

The `release/` directory contains:
- **{WorkloadName}.{Version}.nupkg**: NuGet package with manifest (deployed to Fabric tenant)
- **app/**: Bundled React frontend (deployed to Static Web Apps or similar)

### Deployment Targets

- **Frontend**: Azure Static Web Apps (connector.agic.technology)
- **Backend**: Azure Container Apps or App Service
- **Manifest**: Microsoft Fabric Marketplace (AppSource) or direct tenant deployment
- **Runtime Package**: Azure Artifacts Feed or PyPI (agic-fabric-connector wheel)

### Versioning

- Frontend & manifest versioned together (WORKLOAD_VERSION in .env)
- Backend versioned independently (Dockerfile tag)
- Connector runtime versioned in pyproject.toml (published to feed)

## Repository Context

- **Project Status**: MVP/Phase 2 (remote hosting ready, job scheduling in progress)
- **Latest Release**: v2026.03 (Remote Hosting & Job Scheduling)
- **Publisher**: Agic Technology srl
- **Target Customers**: Enterprise organizations needing multi-source data ingestion into Fabric
- **Geographic**: Global, multi-tenant, multi-region capable

---

**For Copilot/Claude Users**: Always reference `.ai/AGENTS.md` for product vision and `.github/copilot-instructions.md` for code generation patterns before implementing features. Consistency with existing item structure (HelloWorldItem, ConnectorItem) is mandatory.

---

## Active Task: Multi-Workload Decomposition (Opus Session)

> **Branch**: `feature/workload-decomposition` (created from `feature/multi-connector-selection`)
> **Status**: In progress
> **Owner**: Agic Technology srl
> **Model**: Claude Opus (claude.ai/code)

### Objective

Decompose the single **Universal Connector** workload into **3–5 focused Custom Workloads** that:

1. Each does exactly **one thing** — one data source / one business domain
2. Share the **same backend** (single FastAPI deployment on Azure)
3. Are published as **separate entries** on Fabric AppSource / workload hub
4. Live in **this same repository**, each in its own subfolder under `workloads/`
5. The **MVP** is `customer-insight-journey` — complete this first before the others

---

### Planned Workloads

| Priority | Workload ID | Display Name | Source | Entities |
|----------|-------------|--------------|--------|----------|
| 1 — MVP | `customer-insight-journey` | Customer Insight Journey | Dynamics 365 CRM / Dataverse | 3 tables already configured — **identify from `connectorRegistry.ts` and CRM module** |
| 2 | `sales-crm` | Sales CRM | Dynamics 365 CRM / Dataverse | Sales-specific entities |
| 3 | `business-central` | Business Central | BC OData v4 | All current BC entities |
| 4 | `sql-db` | SQL DB Connector | Azure SQL / SQL Server | User-defined tables |
| 5 | TBD | (identify from code) | (additional source if found) | — |

> Before implementing, **read `Workload/app/items/ConnectorItem/wizard/connectorRegistry.ts`** and **`backend/connectors/crm/`** to determine the exact 3 tables scoped to Customer Insight Journey.

---

### Target Repository Structure

Migrate from the current flat layout to this monorepo structure:

```
/
├── backend/                          # Shared FastAPI backend — single deployment
│   ├── app/
│   │   ├── api/
│   │   │   ├── jobs.py               # Existing — extend with workload routing
│   │   │   └── workloads.py          # NEW — workload identity resolution
│   │   ├── connectors/
│   │   │   ├── base.py               # BaseConnector (keep as-is)
│   │   │   ├── crm/                  # CRMConnector (keep as-is)
│   │   │   ├── bc/                   # BCConnector (keep as-is)
│   │   │   └── sql/                  # SQLConnector (keep as-is)
│   │   └── workload_config/          # NEW — per-workload entity/config scoping
│   │       ├── customer_insight_journey.py
│   │       ├── sales_crm.py
│   │       ├── business_central.py
│   │       └── sql_db.py
│   └── main.py
│   └── Dockerfile
│   └── requirements.txt
│
├── workloads/                        # One subfolder per published workload
│   ├── customer-insight-journey/     # MVP — DO THIS FIRST
│   │   ├── frontend/                 # React/TS frontend (stripped from ConnectorItem)
│   │   ├── manifest/                 # WorkloadManifest.xml + Product.json + icons
│   │   └── config/
│   │       └── workload.json         # Entity scope, display config, workload metadata
│   ├── sales-crm/
│   │   ├── frontend/
│   │   ├── manifest/
│   │   └── config/workload.json
│   ├── business-central/
│   │   ├── frontend/
│   │   ├── manifest/
│   │   └── config/workload.json
│   └── sql-db/
│       ├── frontend/
│       ├── manifest/
│       └── config/workload.json
│
├── shared/                           # Shared code — DO NOT DUPLICATE
│   ├── components/                   # Shared Fluent UI components
│   ├── types/                        # Shared TypeScript types
│   ├── hooks/                        # Shared React hooks
│   └── utils/                        # Shared utilities
│
├── connector/runtime/                # Keep as-is (agic-fabric-connector wheel)
├── scripts/                          # Keep as-is, extend for multi-workload builds
└── Workload/                         # LEGACY — migrate to workloads/ then deprecate
```

---

### Backend: Workload Identity & Routing

The single FastAPI backend must detect which workload is calling it and scope the response accordingly.

**Strategy — `X-Workload-Id` request header** (simplest, no path changes needed):

```python
# backend/app/api/workloads.py  (NEW FILE)
from enum import Enum

class WorkloadId(str, Enum):
    CUSTOMER_INSIGHT_JOURNEY = "customer-insight-journey"
    SALES_CRM = "sales-crm"
    BUSINESS_CENTRAL = "business-central"
    SQL_DB = "sql-db"

def get_workload_id(request: Request) -> WorkloadId:
    """Extract workload identity from request header."""
    wid = request.headers.get("X-Workload-Id")
    if not wid or wid not in WorkloadId._value2member_map_:
        raise HTTPException(status_code=400, detail=f"Missing or invalid X-Workload-Id header")
    return WorkloadId(wid)
```

```python
# backend/app/workload_config/customer_insight_journey.py  (NEW FILE)
# Defines which entities/tables this workload exposes — read from code analysis

WORKLOAD_METADATA = {
    "id": "customer-insight-journey",
    "display_name": "Customer Insight Journey",
    "source": "crm",
    "entities": [
        # TODO: populate from connectorRegistry.ts + CRM module analysis
        # Example:
        # {"id": "contact", "display_name": "Contact", "table": "bronze_crm/contact"},
        # {"id": "msdynmkt_journey", ...},
        # {"id": "msdynmkt_customerjourney", ...},
    ]
}
```

```python
# backend/app/api/jobs.py  (EXTEND existing)
@router.post("/v1/items/{itemId}/runJob")
async def run_job(
    itemId: str,
    job_request: JobRunRequest,
    workload_id: WorkloadId = Depends(get_workload_id)
):
    # Load workload-scoped config (restricts which entities are synced)
    workload_config = load_workload_config(workload_id)
    
    # Route to correct connector (CRM/BC/SQL) — unchanged from current logic
    connector = connector_factory(workload_config.source, job_request)
    
    # Scope ingestion to only this workload's entities
    connector.set_entity_scope(workload_config.entities)
    
    return await connector.ingest()
```

**API Contract** (all workloads, workload-id from header):

```
GET  /v1/workloads/config          → workload metadata + entity list
GET  /v1/items/{itemId}/runJob     → trigger ingestion (scoped by X-Workload-Id)
GET  /v1/items/{itemId}/jobs/{id}  → job status
GET  /v1/items/{itemId}/runs       → run history
```

---

### Frontend: Per-Workload Scope

Each workload frontend is a **stripped-down version of ConnectorItem** with:

1. **Wizard reduced** — remove `WizardModuleStep` (source is fixed, not user-selectable)
2. **Entity step locked** — show only this workload's entities, pre-checked, not editable
3. **Dashboard scoped** — only show tables relevant to this workload
4. **Workload ID injected** — set `X-Workload-Id` header on every backend call

```typescript
// workloads/customer-insight-journey/frontend/config/workloadConfig.ts
export const WORKLOAD_CONFIG = {
  workloadId: "customer-insight-journey",
  displayName: "Customer Insight Journey",
  source: "crm" as const,
  // Entities locked for this workload — no user selection
  entities: [
    // TODO: populate after backend analysis
  ],
  // Wizard steps enabled for this workload
  wizardSteps: ["auth", "schedule", "storage", "review"], // source + entities are pre-set
};
```

**Shared header injection** (add to all API calls):

```typescript
// shared/utils/apiClient.ts
export function getWorkloadHeaders(): Record<string, string> {
  return {
    "X-Workload-Id": WORKLOAD_CONFIG.workloadId,
  };
}
```

---

### Manifest per Workload

Each workload needs its own `WorkloadManifest.xml`. Key differences:

```xml
<!-- workloads/customer-insight-journey/manifest/WorkloadManifest.xml -->
<Workload 
  name="{{WORKLOAD_NAME}}"
  displayName="Customer Insight Journey"
  version="{{WORKLOAD_VERSION}}">
  
  <Description>Ingest Dynamics 365 Customer Journey data into your Fabric Lakehouse.</Description>
  <FrontendEndpoint>https://cij.connector.agic.technology</FrontendEndpoint>
  
  <!-- Shared backend — workload identified via X-Workload-Id header -->
  <BackendEndpoint>https://backend-{{ENV}}.azurewebsites.net</BackendEndpoint>
  
  <Items>
    <Item name="{{WORKLOAD_NAME}}.ConnectorItem" ... />
  </Items>
</Workload>
```

Each workload gets:
- Unique `displayName` and `Description`
- Its own frontend subdomain (e.g., `cij.connector.agic.technology`, `bc.connector.agic.technology`)
- Same `BackendEndpoint` (shared backend)

---

### Azure Deployment Architecture

**Recommendation: Azure Container Apps (shared backend) + Azure Static Web Apps (per workload frontend)**

```
┌─────────────────────────────────────────────────────────┐
│  Fabric Portal                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  CIJ     │ │  Sales   │ │   BC     │ │  SQL DB  │  │
│  │ Workload │ │  CRM     │ │Workload  │ │Workload  │  │
│  └──────┬───┘ └──────┬───┘ └──────┬───┘ └──────┬───┘  │
└─────────┼────────────┼────────────┼────────────┼────────┘
          │            │            │            │
          ▼            ▼            ▼            ▼
┌──────────────────────────────────────────────────────────┐
│  Azure Static Web Apps (per workload — separate deploy)  │
│  cij.connector.agic.technology                           │
│  sales.connector.agic.technology  ...                    │
└────────────────────────┬─────────────────────────────────┘
                         │ X-Workload-Id header
                         ▼
┌──────────────────────────────────────────────────────────┐
│  Azure Container Apps — Single Backend                   │
│  backend.connector.agic.technology                       │
│  FastAPI + all connectors (CRM / BC / SQL)               │
│  Scale-to-zero enabled                                   │
└──────────────────────────────────────────────────────────┘
```

**Rationale:**
- Container Apps: scale-to-zero saves cost, Docker already in repo, stateless FastAPI
- Static Web Apps: free tier viable per workload, independent deploy per frontend
- No Azure Functions needed (job orchestration is already FastAPI + Fabric Scheduler)

---

### Git Branching & PR Strategy

```bash
# Create working branch from the correct base
git checkout feature/multi-connector-selection
git pull origin feature/multi-connector-selection
git checkout -b feature/workload-decomposition

# Commit structure (one commit per logical unit):
# 1. Repo restructure (move files, create workloads/ and shared/)
# 2. Backend: workload routing + config files
# 3. Workload: customer-insight-journey (MVP — frontend + manifest + config)
# 4. Workload: business-central
# 5. Workload: sales-crm
# 6. Workload: sql-db
# 7. CI/CD: build scripts per workload
```

**PR Strategy:** One PR into `feature/multi-connector-selection` with the full decomposition. Review per-workload using PR file filters.

---

### Step-by-Step Implementation Order

Follow this exact order to avoid breaking existing functionality:

1. **Read before writing**
   - [ ] Read `Workload/app/items/ConnectorItem/wizard/connectorRegistry.ts` — identify Customer Insight Journey entities
   - [ ] Read `backend/connectors/crm/` — confirm entity list and field mappings
   - [ ] Read `Workload/Manifest/Product.json` and `WorkloadManifest.xml` — understand current manifest structure

2. **Create branch**
   ```bash
   git checkout feature/multi-connector-selection && git pull
   git checkout -b feature/workload-decomposition
   ```

3. **Restructure repo** (no logic changes yet)
   - [ ] Create `workloads/`, `shared/` directories
   - [ ] Copy (not move) `Workload/` content into `workloads/customer-insight-journey/frontend/` as starting point
   - [ ] Extract shared components into `shared/`

4. **Backend: add workload routing**
   - [ ] Create `backend/app/api/workloads.py`
   - [ ] Create `backend/app/workload_config/` with one file per workload
   - [ ] Extend `backend/app/api/jobs.py` with workload scoping
   - [ ] Add `X-Workload-Id` header validation

5. **MVP: Customer Insight Journey frontend**
   - [ ] Strip wizard to only: Auth → Schedule → Storage → Review (remove Module step)
   - [ ] Lock entity selection to the 3 CIJ tables (pre-checked, read-only)
   - [ ] Inject `X-Workload-Id: customer-insight-journey` on all API calls
   - [ ] Create `workloads/customer-insight-journey/manifest/` from existing manifest template

6. **MVP: Customer Insight Journey manifest**
   - [ ] Create `WorkloadManifest.xml` with CIJ-specific metadata
   - [ ] Create `Product.json` with CIJ display name/description
   - [ ] Update build scripts to support `--workload customer-insight-journey`

7. **Test MVP end-to-end**
   - [ ] Local: `.\Start-Workload.ps1` pointing to CIJ frontend
   - [ ] Verify `X-Workload-Id` header reaches backend
   - [ ] Verify only CIJ entities appear in UI and are ingested

8. **Repeat steps 5–7 for**: `business-central`, `sales-crm`, `sql-db`

9. **CI/CD**
   - [ ] GitHub Actions workflow: build + deploy per workload (matrix strategy)
   - [ ] Single backend workflow: Docker build + push to Container Apps

---

### Constraints (Non-Negotiable)

- **Do NOT modify** `feature/multi-connector-selection` directly — always work on `feature/workload-decomposition`
- **Backend stays one deployment** — no splitting connectors into separate services
- **No code duplication** — shared UI components go to `shared/`, never copied per workload
- **Existing HelloWorldItem untouched** — it is not part of this decomposition
- **Bronze layer naming preserved** — `bronze_crm/`, `bronze_bc/`, `bronze_sql/` paths unchanged
- **Customer Insight Journey is MVP** — fully working before starting other workloads
- **Manifest placeholders preserved** — `{{WORKLOAD_NAME}}`, `{{WORKLOAD_VERSION}}` pattern mandatory

---

### Definition of Done

A workload is complete when:
- [ ] Frontend builds independently with `npm run build:prod` from its own directory
- [ ] Manifest NuGet package generates correctly for this workload
- [ ] Backend routes correctly based on `X-Workload-Id` header
- [ ] Only the correct entities appear in the UI for this workload
- [ ] Local end-to-end test passes (create item → run job → data in Bronze Lakehouse)
- [ ] Published to Fabric AppSource (or direct tenant deployment) as a separate entry
