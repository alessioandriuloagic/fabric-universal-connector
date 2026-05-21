# Per-Workload Deployment Guide

> This guide describes how to build, package, and publish each of the four focused workloads as a **separate entry** on the Microsoft Fabric AppSource / workload hub.  
> All workloads share the same FastAPI backend (single Azure deployment).

---

## Overview

| Workload ID | Display Name | Source | Frontend Subdomain |
|---|---|---|---|
| `customer-insight-journey` | Customer Insight Journey | Dynamics 365 CRM / Dataverse | `cij.connector.agic.technology` |
| `sales-crm` | Sales CRM | Dynamics 365 CRM / Dataverse | `sales.connector.agic.technology` |
| `business-central` | Business Central | BC OData v4 | `bc.connector.agic.technology` |
| `sql-db` | SQL DB Connector | Azure SQL / SQL Server | `sql.connector.agic.technology` |

---

## Prerequisites

- PowerShell 7+, Node.js 18+, .NET SDK 6+
- Azure CLI authenticated to the target subscription
- Access to the target Fabric tenant (ISV tenant for manifest upload)
- `.env.prod` file in `Workload/` populated with production values
- Azure Static Web Apps resource per workload (or a shared SWA with routing rules)

---

## 1. Build the Frontend Bundle

Each workload uses a dedicated npm script that sets `REACT_APP_WORKLOAD_ID`:

```powershell
cd Workload

# Customer Insight Journey
npm run build:customer-insight-journey:prod

# Business Central
npm run build:business-central:prod

# Sales CRM
npm run build:sales-crm:prod

# SQL DB
npm run build:sql-db:prod
```

Output is written to `build/Frontend/`. The bundle is workload-aware — it injects the correct `X-Workload-Id` header on every backend API call.

---

## 2. Generate the Manifest NuGet Package

Use `BuildRelease.ps1` with the `-Workload` parameter:

```powershell
# Customer Insight Journey
.\scripts\Build\BuildRelease.ps1 `
  -Workload "customer-insight-journey" `
  -WorkloadName "Agic.CustomerInsightJourney" `
  -FrontendAppId "<your-cij-app-registration-guid>" `
  -Environment prod

# Business Central
.\scripts\Build\BuildRelease.ps1 `
  -Workload "business-central" `
  -WorkloadName "Agic.BusinessCentral" `
  -FrontendAppId "<your-bc-app-registration-guid>" `
  -Environment prod

# Sales CRM
.\scripts\Build\BuildRelease.ps1 `
  -Workload "sales-crm" `
  -WorkloadName "Agic.SalesCRM" `
  -FrontendAppId "<your-sales-app-registration-guid>" `
  -Environment prod

# SQL DB
.\scripts\Build\BuildRelease.ps1 `
  -Workload "sql-db" `
  -WorkloadName "Agic.SqlDb" `
  -FrontendAppId "<your-sql-app-registration-guid>" `
  -Environment prod
```

Each command outputs a `.nupkg` file in `release/` named `{WorkloadName}.{Version}.nupkg`.

---

## 3. Deploy the Frontend to Azure Static Web Apps

Each workload is deployed independently to its own Azure Static Web Apps resource (or to a named path under a shared one).

```bash
# Example for Customer Insight Journey using Azure CLI
az staticwebapp deploy \
  --name "cij-connector-agic" \
  --resource-group "fabric-connectors-rg" \
  --source "build/Frontend" \
  --token "<SWA_DEPLOYMENT_TOKEN_CIJ>"
```

Repeat for each workload, using the corresponding SWA resource and token.

> **Custom domain**: configure the CNAME record for `cij.connector.agic.technology` → the SWA default hostname in Azure DNS / your DNS provider.

---

## 4. Deploy the Shared Backend

The backend is deployed **once** and serves all workloads. It identifies the calling workload via the `X-Workload-Id` request header.

```bash
# Build and push Docker image
docker build -t fabric-connector-backend:latest ./backend
docker tag fabric-connector-backend:latest <acr-name>.azurecr.io/fabric-connector-backend:latest
docker push <acr-name>.azurecr.io/fabric-connector-backend:latest

# Deploy to Azure Container Apps
az containerapp update \
  --name "fabric-connector-backend" \
  --resource-group "fabric-connectors-rg" \
  --image "<acr-name>.azurecr.io/fabric-connector-backend:latest"
```

Backend environment variables required:

| Variable | Description |
|---|---|
| `FABRIC_TENANT_ID` | ISV Entra tenant ID for JWT validation |
| `BACKEND_APP_ID` | Entra app registration ID |
| `USE_TABLE_STORAGE` | `true` to persist job state in Azure Tables |
| `ENABLE_SWAGGER` | `false` in production |
| `LOG_LEVEL` | `INFO` or `WARNING` in production |

---

## 5. Upload the Manifest to Fabric

For **direct tenant deployment** (non-AppSource):

```powershell
.\scripts\Deploy\DeployManifest.ps1 `
  -NuGetPackagePath "release/Agic.CustomerInsightJourney.2026.03.nupkg" `
  -TenantId "<fabric-tenant-id>"
```

For **AppSource / Fabric Marketplace** publication, follow the [Microsoft ISV guide](https://learn.microsoft.com/en-us/fabric/workload-development-kit/publish-workload-in-marketplace).  
Each workload is submitted as a **separate Partner Center offering** with its own `WorkloadManifest.xml` NuGet.

---

## 6. Verify the Deployment

1. Open the target Fabric workspace.
2. Click **+ New** and verify the workload entry appears with the correct display name and icon.
3. Create a new item — the wizard should show only the steps and entities scoped to that workload.
4. Trigger a **Run Now** from the ribbon and confirm the backend receives `X-Workload-Id` correctly (check Container Apps log stream).
5. Verify data lands in the Bronze Lakehouse under the correct `bronze_crm/`, `bronze_bc/`, or `bronze_sql/` path.

---

## CI/CD (GitHub Actions)

The repository includes a matrix workflow that builds and deploys all workloads automatically on push to `main`:

```yaml
# .github/workflows/deploy-workloads.yml
strategy:
  matrix:
    workload: [customer-insight-journey, business-central, sales-crm, sql-db]
```

See [`.github/workflows/`](../../.github/workflows/) for the full workflow definition.

---

*2026-05-21 UTC*
