# Fabric Universal Connector

**Publisher:** Agic Technology srl  
**Version:** v2026.03  
**Category:** Data Integration · Microsoft Fabric Workload

> A production-ready, metadata-driven data ingestion workload for Microsoft Fabric. Connect Dataverse / Dynamics 365 CRM, Business Central, and SQL Server to your Fabric Lakehouse with a guided 7-step wizard — no code required.

---

## Overview

The **Fabric Universal Connector** is an enterprise-grade Microsoft Fabric workload that brings multi-source data ingestion natively into the Fabric experience. It eliminates the need for custom pipelines, external ETL tools, or bespoke notebooks by providing a unified, configuration-driven connector that runs directly in your Fabric workspace.

Once configured, the connector deploys a Python runtime notebook into your workspace and schedules it via the Fabric Job Scheduler. All raw data lands in an append-only Bronze Lakehouse (Delta format) — ready for downstream Silver/Gold transformations.

---

## Supported Data Sources

| Source | Protocol | Incremental Strategy |
|--------|----------|----------------------|
| **Dataverse / Dynamics 365 CRM** | OData v4 (Dataverse Web API) | Change Tracking delta links |
| **Microsoft Dynamics 365 Business Central** | OData v4 | Timestamp / delta watermarks |
| **SQL Server / Azure SQL** | ODBC / JDBC | Watermark column (datetime, rowversion, integer) |

---

## Key Features

### Guided Configuration Wizard
A 7-step wizard walks users through the full setup:
1. **Module** — choose the source system (CRM, Business Central, or SQL)
2. **Source** — enter connection parameters (URL, server, environment)
3. **Authentication** — select credentials strategy (Fabric Connection, Key Vault, or Service Principal)
4. **Entities** — pick tables / entities to ingest with per-entity extraction settings
5. **Storage** — choose or create the destination Bronze Lakehouse
6. **Schedule** — configure automated runs (cron expression or fixed interval)
7. **Review** — validate the full configuration before activating

### Incremental Extraction
- CRM: uses Dataverse **Change Tracking** to extract only new and modified records since the last run
- Business Central: timestamp-based watermarks to track new records per endpoint
- SQL: configurable watermark column (supports `datetime`, `rowversion`, and `integer` types)
- Watermarks are persisted in Delta tables (`_meta/watermarks`) and survive connector restarts

### Schema Evolution Handling
Three policies to handle source schema changes between runs:
- **Merge** (default) — new columns are added automatically; existing data is preserved
- **Strict** — schema changes cause the run to fail; safe for tightly controlled pipelines
- **Overwrite** — full table recreation with the new schema; use with caution

### Authentication Strategies
- **Fabric Connection** — credentials stored in the Fabric Connection manager; no secrets in item definition
- **Key Vault Reference** — secrets resolved from Azure Key Vault at runtime; zero-secret architecture
- **Service Principal** — direct Entra ID service principal with secret resolved via Fabric Connection or Key Vault

### Run Dashboard
The item editor includes a live dashboard with:
- Run history list with status, duration, and record counts
- Per-entity drill-down showing records ingested, failed, and current watermark
- Run detail view with full entity-level breakdown and error messages
- Ribbon actions: **Run Now**, **Pause / Resume schedule**, **Reconfigure**

### Bronze Lakehouse Structure
All data lands in Delta format under predictable paths:

```
bronze_crm/
  contact/          ← CRM entity data (append-only)
  lead/
  ...
  _meta/
    _connector_runs     ← run audit log
    _watermarks         ← incremental sync checkpoints
    _schema_evolution   ← schema change history
    _error_log          ← per-record error tracking

bronze_bc/
  customers/
  _meta/

bronze_sql/
  {schema}_{table}/
  _meta/
```

### Error Handling & Partial Runs
- Configurable **error threshold** (% of failed records) before a run is marked as failed
- **Partial run mode** allows a run to succeed even when some entities fail
- All extraction errors are logged to `_meta/_error_log` with full context for diagnosis

---

## Architecture

```
Fabric Portal (browser)
  └─ ConnectorItem UI (React / TypeScript — FERemote iframe)
       └─ 7-step wizard → item definition saved as Base64 JSON in OneLake

Fabric Job Scheduler
  └─ Triggers on schedule or on-demand
       └─ FastAPI Backend (Azure Container Apps / App Service)
            └─ Validates JWT, loads item definition, routes to module connector
                 ├─ CRMConnector    → Dataverse Web API (MSAL auth)
                 ├─ BCConnector     → Business Central OData v4
                 └─ SQLConnector    → SQL Server / Azure SQL (ODBC)
                      └─ Writes Delta tables to Bronze Lakehouse via OneLake SDK
```

**Key architectural decisions:**
- Frontend hosted on ISV infrastructure (FERemote pattern) — no code runs in customer compute at UI time
- Ingestion executes in the customer's Fabric workspace via deployed notebooks (Spark / Python)
- All raw data is **append-only** — source records are never modified or deleted in the Bronze layer
- Item definition stored as **Base64 JSON** in OneLake — no database dependency for configuration
- **Zero-trust credential model** — no secrets are stored in the item definition or backend code

---

## Getting Started

### Prerequisites

- Microsoft Fabric workspace with an assigned Fabric capacity
- One of the supported source systems (Dataverse, Business Central, or SQL Server)
- An Entra ID application registration (or existing Fabric Connection) with access to the source
- Contributor access to the target Fabric workspace

### Create a Connector Item

1. Open your Fabric workspace.
2. Click **+ New** → **Fabric Universal Connector**.
3. Give the item a name and click **Create**.
4. The item editor opens on the **empty state** screen — click **Configure Connector** to start the wizard.

### Step Through the Wizard

**Step 1 — Module**  
Select the data source module: *Dataverse / Dynamics 365 CRM*, *Business Central*, or *SQL Server*.

**Step 2 — Source**  
Enter the connection parameters specific to your module:
- CRM: Dataverse environment URL and tenant ID
- Business Central: tenant ID, environment name, optional company ID
- SQL: server hostname, database name, port

**Step 3 — Authentication**  
Choose how credentials are resolved at runtime:
- **Fabric Connection** (recommended): select a pre-registered Fabric Connection
- **Key Vault Reference**: provide your Key Vault URI and secret names
- **Service Principal**: enter tenant ID and client ID, then select the secret source

**Step 4 — Entities**  
Browse the available entities / tables and select which ones to ingest. For each entity you can configure:
- Extraction mode (incremental or full reload)
- Column selection (OData $select / SQL column list)
- Server-side filter (OData $filter / SQL WHERE clause)
- Batch / page size

**Step 5 — Storage**  
Choose the destination Bronze Lakehouse:
- Create a new Lakehouse automatically (default name: `FabricUniversalConnector-Bronze`)
- Attach to an existing Lakehouse in the same workspace
- Set the schema evolution policy

**Step 6 — Schedule**  
Configure when the connector runs automatically:
- **Cron** expression (e.g. `0 2 * * *` for daily at 02:00 UTC)
- **Interval** in minutes (e.g. every 60 minutes)
- Select timezone and optional start date

**Step 7 — Review & Activate**  
Inspect the full configuration summary. Click **Activate** to:
1. Deploy the connector runtime notebook into your workspace
2. Register the job schedule with the Fabric Job Scheduler
3. Transition the item to **configured** state

### Running the Connector

After activation, use the ribbon actions in the item editor:

| Action | Description |
|--------|-------------|
| **Run Now** | Trigger an immediate on-demand run |
| **Pause / Resume** | Temporarily disable the automated schedule |
| **Reconfigure** | Re-enter the wizard to change any setting |
| **Settings** | Edit display name, description, and tags |

Run history and per-entity results appear on the **Dashboard** view automatically after each run.

---

## Configuration Reference

The item definition is stored as a versioned JSON document (`schemaVersion: "1.0.0"`). Below is the full structure:

```json
{
  "schemaVersion": "1.0.0",
  "state": "configured",
  "moduleType": "crm | businesscentral | sql",
  "source": { ... },
  "entities": [ ... ],
  "authentication": { "mode": "fabric_connection | keyvault_reference | service_principal", ... },
  "storage": {
    "bronzeLakeHouseName": "FabricUniversalConnector-Bronze",
    "schemaEvolutionPolicy": "merge | strict | overwrite",
    "retentionDays": 90,
    "useExistingLakehouse": false
  },
  "scheduling": {
    "scheduleType": "cron",
    "cronExpression": "0 2 * * *",
    "timezone": "UTC",
    "enabled": true
  },
  "features": {
    "errorThresholdPercent": 5,
    "enablePartialRun": true,
    "enableDeltaLakeOptimize": true
  }
}
```

---

## Security & Compliance

- **No credentials in code or item definition** — all secrets resolved at runtime via Fabric Connections or Azure Key Vault
- **JWT-validated backend** — all API calls from Fabric are verified against your Entra tenant
- **Tenant isolation** — each customer's data is stored in their own OneLake workspace; no cross-tenant data access
- **Append-only Bronze layer** — source data is never modified; full audit trail of every ingested record
- **Rate limiting** — backend API protected with per-IP rate limiting (slowapi)
- **OWASP Top 10 mitigations** applied across frontend and backend

---

## Release Notes

### v2026.03 — Remote Hosting & Job Scheduling *(Current)*
- Production-ready remote hosting with `SwitchToRemoteHosting.ps1`
- Full Fabric Job Scheduler integration with run lifecycle management
- Soft delete and restore for connector items
- `CreateJob.ps1` for programmatic schedule registration

### v2026.01 — Connector Item GA
- Dataverse / Business Central / SQL connector modules
- 7-step configuration wizard
- Bronze Lakehouse with Delta format, watermarks, and _meta tables
- Incremental extraction with Change Tracking (CRM) and watermark columns (BC / SQL)
- Schema evolution policies (merge / strict / overwrite)
- Run dashboard with per-entity drill-down

[View all release notes →](docs/ReleaseNotes/)

---

## Support

- **Issues & Feedback**: open an issue on the [GitHub repository](https://github.com/agic-technology/fabric-universal-connector/issues)
- **Documentation**: [docs/](docs/) folder in this repository
- **Publisher**: [Agic Technology srl](https://agic.technology)

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft trademarks or logos is subject to and must follow [Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).

---

*2026-05-20 10:00 UTC*
