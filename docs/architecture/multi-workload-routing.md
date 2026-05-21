# Multi-Workload Routing Architecture

> Describes how a single FastAPI backend routes requests from four separate frontend workloads using the `X-Workload-Id` HTTP header.

---

## Request Flow

```mermaid
flowchart TD
    subgraph FabricPortal["Fabric Portal (browser)"]
        CIJ["Customer Insight Journey\ncij.connector.agic.technology"]
        SALES["Sales CRM\nsales.connector.agic.technology"]
        BC["Business Central\nbc.connector.agic.technology"]
        SQL["SQL DB\nsql.connector.agic.technology"]
    end

    subgraph AzureSWA["Azure Static Web Apps (one per workload)"]
        FE_CIJ["Frontend Bundle\nX-Workload-Id: customer-insight-journey"]
        FE_SALES["Frontend Bundle\nX-Workload-Id: sales-crm"]
        FE_BC["Frontend Bundle\nX-Workload-Id: business-central"]
        FE_SQL["Frontend Bundle\nX-Workload-Id: sql-db"]
    end

    subgraph Backend["Azure Container Apps — Shared FastAPI Backend\nbackend.connector.agic.technology"]
        MW["WorkloadId Middleware\nvalidate X-Workload-Id header"]
        ROUTER["Workload Router\nload_workload_config(workload_id)"]
        CRM["CRMConnector"]
        BCC["BCConnector"]
        SQLC["SQLConnector"]
        OL["OneLake Writer\n(Bronze Delta tables)"]
    end

    CIJ --> FE_CIJ
    SALES --> FE_SALES
    BC --> FE_BC
    SQL --> FE_SQL

    FE_CIJ -->|"POST /v1/items/{id}/runJob\nX-Workload-Id: customer-insight-journey"| MW
    FE_SALES -->|"X-Workload-Id: sales-crm"| MW
    FE_BC -->|"X-Workload-Id: business-central"| MW
    FE_SQL -->|"X-Workload-Id: sql-db"| MW

    MW --> ROUTER
    ROUTER -->|source = crm| CRM
    ROUTER -->|source = businesscentral| BCC
    ROUTER -->|source = sql| SQLC

    CRM --> OL
    BCC --> OL
    SQLC --> OL
```

---

## Header Injection (Frontend)

Every workload frontend sets the `X-Workload-Id` header via the shared API client:

```typescript
// shared/utils/apiClient.ts
export function createWorkloadFetch(workloadId: WorkloadId) {
  return (url: string, init?: RequestInit) =>
    fetch(url, {
      ...init,
      headers: {
        ...init?.headers,
        "X-Workload-Id": workloadId,
      },
    });
}
```

The `workloadId` value is sourced from each workload's static config:

```typescript
// workloads/customer-insight-journey/frontend/config/workloadConfig.ts
export const WORKLOAD_CONFIG = {
  workloadId: "customer-insight-journey" as const,
  // ...
};
```

---

## Header Validation (Backend Middleware)

```python
# backend/app/api/workloads.py
class WorkloadId(str, Enum):
    CUSTOMER_INSIGHT_JOURNEY = "customer-insight-journey"
    SALES_CRM                = "sales-crm"
    BUSINESS_CENTRAL         = "business-central"
    SQL_DB                   = "sql-db"

def get_workload_id(request: Request) -> WorkloadId:
    wid = request.headers.get("X-Workload-Id")
    if not wid or wid not in WorkloadId._value2member_map_:
        raise HTTPException(400, detail="Missing or invalid X-Workload-Id header")
    return WorkloadId(wid)
```

Requests without a valid header are rejected with `HTTP 400` on all endpoints except `/health`.

---

## Workload Config Scoping (Backend)

Each workload has a config module that restricts which entities are allowed:

```python
# backend/app/workload_config/customer_insight_journey.py
WORKLOAD_METADATA = {
    "id":           "customer-insight-journey",
    "display_name": "Customer Insight Journey",
    "source":       "crm",
    "entities": [
        {"id": "contact",             "display_name": "Contact",              "table": "bronze_crm/contact"},
        {"id": "msdynmkt_journey",    "display_name": "Customer Journey",     "table": "bronze_crm/msdynmkt_journey"},
        {"id": "msdynmkt_email",      "display_name": "Marketing Email",      "table": "bronze_crm/msdynmkt_email"},
    ],
}
ALLOWED_ENTITY_NAMES = frozenset(e["id"] for e in WORKLOAD_METADATA["entities"])
```

The `jobs.py` endpoint uses `ALLOWED_ENTITY_NAMES` to filter the entity list from the item definition before passing it to the connector, so a malicious or misconfigured frontend can never trigger ingestion of out-of-scope entities.

---

## Sequence Diagram — runJob

```mermaid
sequenceDiagram
    participant UI as Frontend (CIJ)
    participant GW as Fabric DevGateway / APIM
    participant API as FastAPI Backend
    participant CFG as WorkloadConfig (CIJ)
    participant CRM as CRMConnector
    participant OL as OneLake (Bronze)

    UI->>GW: POST /v1/items/{id}/runJob\n[X-Workload-Id: customer-insight-journey]
    GW->>API: forward request + JWT
    API->>API: validate JWT (FABRIC_TENANT_ID)
    API->>API: extract X-Workload-Id header
    API->>CFG: load_workload_config("customer-insight-journey")
    CFG-->>API: WORKLOAD_METADATA + ALLOWED_ENTITY_NAMES
    API->>API: filter requested entities ∩ ALLOWED_ENTITY_NAMES
    API->>CRM: ingest(scoped_entities, item_definition)
    CRM->>OL: write Delta tables (bronze_crm/contact, ...)
    CRM-->>API: RunResult
    API-->>UI: { jobId, status: "in_progress" }
```

---

## Entity Scoping per Workload

| Workload | Source | Entities |
|---|---|---|
| `customer-insight-journey` | CRM | `contact`, `msdynmkt_journey`, `msdynmkt_email` |
| `sales-crm` | CRM | `lead`, `opportunity`, `account`, `quote`, `salesorder` |
| `business-central` | BC | `customers`, `vendors`, `items`, `salesorders`, `purchaseorders`, `generalledgerentries` |
| `sql-db` | SQL | User-defined (permissive — all table names allowed) |

---

*2026-05-21 UTC*
