# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Fabric Universal Connector** — a Microsoft Fabric Extensibility Toolkit workload for enterprise data ingestion. It is a multi-tenant, modular, metadata-driven platform that ingests data from Dataverse/Dynamics 365 CRM, Business Central, and SQL Server into Fabric Lakehouses.

The workload includes:
- **Frontend**: React/TypeScript UI running in Fabric portal (FERemote iframe)
- **Backend**: FastAPI Python service for job orchestration
- **Runtime**: Python connector library deployed as Fabric notebooks
- **Manifest**: XML/JSON configuration for Fabric integration

## Repository Structure

```
root/
├── Workload/                    # Frontend (React/TypeScript)
│   ├── app/
│   │   ├── items/               # Custom Fabric item implementations
│   │   │   ├── HelloWorldItem/  # Reference sample
│   │   │   └── ConnectorItem/   # Main data connector UI
│   │   ├── components/          # Reusable UI components
│   │   ├── clients/             # API clients
│   │   ├── controller/          # Business logic controllers (CRUD, Jobs, Notifications)
│   │   └── index.ts             # Bootstrap entry point
│   ├── Manifest/                # Workload manifest templates
│   │   ├── Product.json         # Workload metadata & create experience
│   │   ├── WorkloadManifest.xml # Workload configuration
│   │   └── items/               # Per-item JSON/XML configs
│   ├── devServer/               # Dev server configuration
│   ├── .env.dev, .env.test, .env.prod  # Environment configs (templated)
│   ├── package.json             # Frontend dependencies
│   ├── webpack.config.js        # Webpack build config
│   └── tsconfig.json            # TypeScript config
├── backend/                     # FastAPI backend (job orchestration)
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── api/jobs.py          # Jobs API controller
│   │   ├── models/              # Data models (job state, connector config)
│   │   ├── services/            # Business logic (auth, Fabric client, OneLake writer)
│   │   ├── connectors/          # Source connectors (CRM, BC, SQL)
│   │   └── exceptions.py        # Error handling
│   ├── requirements.txt         # Python dependencies
│   └── Dockerfile              # Container build
├── connector/
│   └── runtime/                 # Python package: agic-fabric-connector
│       ├── agic_fabric_connector/
│       │   ├── base/            # BaseConnector, metadata, bronze writer
│       │   ├── config/          # Config loading & models
│       │   ├── auth/            # Auth strategies
│       │   ├── modules/         # CRM, BC, SQL module implementations
│       │   └── utils/           # Shared utilities
│       └── notebooks/           # Fabric notebook templates (deployed at runtime)
├── scripts/                     # DevOps scripts (PowerShell)
│   ├── Setup/                   # Initial setup & environment configuration
│   ├── Build/                   # Build & packaging
│   ├── Run/                     # Local dev server startup
│   └── Deploy/                  # Deployment to cloud
├── .ai/                         # AI context & commands (Copilot/Claude guidance)
│   ├── context/                 # fabric-workload.md, fabric.md (SDK conventions)
│   ├── commands/                # Automated procedures (createItem, deployWorkload, etc.)
│   ├── AGENTS.md                # Product vision & architectural principles
│   └── architecture/            # target-architecture.md (Phase 2 blueprint)
├── .github/copilot-instructions.md  # GitHub Copilot rules (component patterns, manifest handling)
├── docs/                        # User documentation
├── Start-Workload.ps1           # Quick launcher for local dev
└── README.md                    # Project overview
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, TypeScript, Redux Toolkit, Fluent UI (v8 + v9), webpack 5 |
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
npm run build:dev      # Development build
npm run build:test     # Test/staging build
npm run build:prod     # Production build (minified, optimized)

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

Every custom item follows a rigid 4-file pattern (e.g., `ConnectorItem`):

```typescript
// 1. ConnectorItemDefinition.ts — Data model/state interface
export interface ConnectorItemDefinition {
  config: ConnectorConfig;
  runHistory: RunHistoryEntry[];
  // ...
}

// 2. ConnectorItemEditor.tsx — Main container component
// Uses ItemEditorDefaultView, handles state, navigation, ribbon
export function ConnectorItemEditor(props: ItemEditorProps) {
  return <ItemEditorDefaultView center={{...}} left={{...}} />;
}

// 3. ConnectorItemEditorRibbon.tsx — Toolbar with save/settings actions
// Always includes: homeToolbarActions (mandatory) + optional additionalToolbars
// Uses createSaveAction(), createSettingsAction() factories

// 4. ConnectorItemEditorEmptyView.tsx — Initial state (no configuration yet)
// Guides user through onboarding wizard
```

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

## Copilot & AI Guidelines

The repository includes AI-specific guidance:

- **.github/copilot-instructions.md**: GitHub Copilot enhanced features, code generation patterns, context awareness
- **.ai/context/fabric-workload.md**: SDK conventions for item development (4-file pattern, ribbon, views)
- **.ai/context/fabric.md**: Microsoft Fabric platform knowledge
- **.ai/commands/**: Automation procedures (createItem.md, deployWorkload.md, etc.)
- **.ai/AGENTS.md**: Long-term product vision, architectural principles, scalability model

**Critical Copilot Patterns:**
- Always use Fluent v9 components; migrate v8 imports to v9
- Ribbon MUST include `homeToolbarActions` (mandatory) + optional `additionalToolbars`
- Use `createItemWrapper()` for OneLake storage operations
- Use static view registration with `useViewNavigation()` hook
- ItemEditor center panel handles scrolling; views use `height: auto`
- Message bars use static registration with `showInViews` to control visibility

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
