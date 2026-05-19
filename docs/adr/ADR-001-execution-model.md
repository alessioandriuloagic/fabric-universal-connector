# ADR-001 — Modello di esecuzione: ISV Python Backend + Azure Functions

| Campo | Valore |
|---|---|
| **ID** | ADR-001 |
| **Titolo** | Modello di esecuzione dell'ingestion runtime |
| **Stato** | Accettato |
| **Data** | 2026-05-19 |
| **Autori** | Alessio Andriulo — Agic Technology srl |
| **Revisori** | — |
| **Sostituisce** | — |
| **Collegato a** | `.ai/architecture/target-architecture.md`, `.ai/contracts/ingestion-contracts.md` |

---

## 1. Contesto

Il progetto **Fabric Universal Connector** è un Custom Workload per Microsoft Fabric distribuito come prodotto ISV su AppSource / Workload Hub. Il workload deve estrarre dati da sorgenti esterne (Dynamics 365 CRM, Business Central, SQL Server) e scriverli in tabelle Delta Lake nel Lakehouse Bronze del cliente (OneLake).

Il componente frontend (React, FERemote) è già definito e si occupa di configurazione, wizard di onboarding e monitoring. La decisione da prendere riguarda **dove e come eseguire il codice Python di ingestion** — ovvero quale componente esegue la pipeline di estrazione dei dati.

### Vincoli non negoziabili

- Il codice di ingestion è scritto in **Python** (scelta di progetto confermata).
- Le sorgenti dati usano API REST sequenziali (Dataverse OData, BC OData v4, JDBC). Non vi è parallelismo nativo da sfruttare.
- I volumi tipici per cliente sono **10K–500K record** per run, con incrementali giornalieri nell'ordine di migliaia di record.
- Il prodotto deve essere commercialmente sostenibile: i costi operativi ISV devono rimanere bassi a prescindere dal numero di tenant.
- La Fabric Capacity del cliente deve essere preservata per i workload di analytics e Power BI — l'ingestion non deve competere con essi.

---

## 2. Opzioni valutate

### Opzione A — Fabric Notebook (Python wheel deployato nel workspace cliente)

Il frontend deploya un file `.ipynb` nel workspace del cliente durante l'onboarding. Fabric Job Scheduler avvia il notebook sulla Spark session del cliente. Il notebook installa il wheel `agic-fabric-connector` via `%pip install` e lo esegue.

**Pro:**
- Nessuna infrastruttura ISV da gestire
- Il cliente paga il proprio compute
- I dati non escono mai dal tenant del cliente

**Contro:**
- Ogni run comporta l'avvio di una Spark session: 2–5 minuti di overhead fisso, indipendente dal volume dei dati
- Per volumi CRM tipici, il 70–80% del costo CU è startup Spark — non lavoro reale
- Il Notebook è uno strumento interattivo usato come job batch: pattern non nativo
- Il cliente percepisce item aggiuntivi nel workspace (il notebook deployato)
- Ogni aggiornamento del wheel richiede gestione della versione nel notebook

**Impatto capacity (F4, scheduling orario):** ~200–300 CU-min/giorno solo per gli avvii Spark.

---

### Opzione B — Fabric Spark Job Definition (Python script deployato nel workspace cliente)

Variante dell'opzione A. Anziché un notebook, si deploya uno **Spark Job Definition** item nel workspace del cliente. Esegue un file `.py`, non un `.ipynb` — pattern più pulito per job di produzione.

**Pro rispetto a Opzione A:**
- Niente celle: struttura più solida per automazione
- Pattern Fabric nativo per job batch su Spark
- Stessa logica Python, stesso wheel

**Contro (identici a Opzione A):**
- Il motore di esecuzione è identico: stesso Spark, stesso overhead CU, stesso cold start
- Il cliente vede ancora un item secondario nel workspace

**Impatto capacity:** identico a Opzione A. La differenza è operativa, non di capacity.

---

### Opzione C — ISV Python Backend + Azure Functions ✅ SCELTA ADOTTATA

Il frontend ConnectorItem è l'unico item nel workspace del cliente. L'esecuzione avviene nel cloud ISV (Agic Technology). Quando Fabric Job Scheduler triggera un job, chiama l'endpoint HTTP ISV (`POST /api/jobs/run`) secondo il contratto del Fabric Workload Development Kit (`IJobsController`). L'Azure Function Python esegue l'ingestion e scrive i dati direttamente su OneLake del cliente via ABFS (Azure Blob File System — protocollo nativo OneLake).

---

## 3. Decisione: ISV Python Backend + Azure Functions

### Architettura dell'esecuzione

```
FABRIC JOB SCHEDULER (tenant cliente)
  │
  │  POST /api/jobs/run
  │  Authorization: Bearer {fabric_token}
  ▼
AZURE FUNCTION — Python (tenant ISV, Agic Technology)
  │
  ├── 1. Valida il token Fabric (Entra ID JWKS)
  ├── 2. Legge ConnectorItemDefinition da Fabric Items API
  │         GET /v1/workspaces/{ws}/items/{id}/definitions/files/payload.json
  ├── 3. Autentica alla sorgente
  │         CRM:  MSAL client credentials → token Dataverse
  │         BC:   MSAL client credentials → token BC API
  │         SQL:  credenziali da Azure Key Vault
  ├── 4. Estrae dati (paginazione OData / JDBC)
  ├── 5. Scrive su OneLake del cliente
  │         delta-rs + PyArrow → ABFS (abfs://onelake.dfs.fabric.microsoft.com/...)
  │         Append-only, partitioned by _ingestion_date
  ├── 6. Aggiorna watermark e metadata (_connector_runs, _entity_watermarks)
  └── 7. Risponde a Fabric con status del job (success / failed / partial_success)

ONELAKE (tenant cliente)
  └── Bronze Lakehouse
       ├── bronze_crm/contact, lead, msdynmkt_*
       ├── bronze_bc/customers, items, ...
       ├── bronze_sql/{schema}_{table}
       └── _meta/ (_connector_runs, _entity_watermarks, _error_log)
```

### Stack tecnico ISV

| Componente | Tecnologia | Motivazione |
|---|---|---|
| Runtime | Azure Functions v2 (Python 3.11) | Serverless, scala a zero, cold start < 1s |
| Delta write | `delta-rs` + `pyarrow` | Scrittura Delta Lake nativa da Python, senza Spark |
| Auth | `msal` (client credentials) | Acquisizione token per Dataverse, BC, Azure Key Vault |
| OneLake access | `azure-storage-file-datalake` (ABFS) | Protocollo nativo OneLake — nessun SDK Fabric proprietario |
| Fabric Job contract | HTTP endpoint REST (WDK `IJobsController`) | Contratto obbligatorio per l'integrazione con Fabric Job Scheduler |
| Segreti | Azure Key Vault + Managed Identity | Zero credenziali nel codice o nella configurazione |
| Monitoring ISV | Azure Application Insights | Telemetria aggregate anonimizzata (opt-in) |

---

## 4. Analisi dell'impatto sulla Fabric Capacity

### Perché Spark è inefficiente per questo caso d'uso

Le sorgenti target (Dataverse OData, Business Central OData) sono **API sequenziali**. Spark non porta alcun vantaggio di parallelismo — le pagine OData devono essere consumate in sequenza seguendo `@odata.nextLink`. Il cluster Spark viene avviato, fa chiamate HTTP sequenziali, scrive i risultati: non vi è mai un executor aggiuntivo che lavora in parallelo.

### Confronto CU stimato per run (F4 capacity)

| Metrica | Opzione A/B (Spark) | Opzione C (Azure Function) |
|---|---|---|
| Overhead avvio | 2–5 min CU (fissi) | 0 CU cliente |
| 10K record Dataverse | ~8–12 CU-min | ~0.1 CU-min (solo write ABFS) |
| 100K record Dataverse | ~15–20 CU-min | ~0.5 CU-min |
| Run orari (24/giorno) | ~200–300 CU-min/giorno | ~2–5 CU-min/giorno |
| Run ogni 15 min (96/giorno) | ~800–1200 CU-min/giorno | ~8–20 CU-min/giorno |

### Impatto commerciale per il cliente

Con scheduling ogni ora su una capacity F4 (240 CU-min/ora disponibili):
- **Opzione A/B:** l'ingestion consuma ~10–15% della capacity daily solo per gli avvii Spark
- **Opzione C:** l'ingestion consuma < 1% della capacity — il cliente ha tutta la capacity per analytics, Power BI e altri workload

### Costo ISV (Opzione C)

Azure Functions Consumption Plan:
- Primo 1M di esecuzioni/mese: **gratuito**
- Oltre: ~€0.17 per milione di esecuzioni
- Per 100 clienti × 24 run/giorno × 30 giorni = 72.000 esecuzioni/mese → **costo zero**
- Compute (GB-s): run medio ~30s × 512MB = 15 GB-s per run → ~€0.25/mese per 100 clienti

---

## 5. Conseguenze e implicazioni

### Cosa si guadagna

- **Capacity cliente preservata:** nessun overhead Spark — la capacity è disponibile per analytics
- **Workspace pulito:** un solo item per il cliente (ConnectorItem), nessun notebook/script deployato
- **Deploy centralizzato:** aggiornamenti del backend ISV non richiedono azioni nei workspace cliente
- **IP protetto:** il codice di ingestion non è visibile al cliente (non è un wheel installabile)
- **Debug semplificato:** Application Insights centralizzato, log per tenant
- **Cold start irrilevante:** Azure Functions Python < 1s — irrilevante per job batch

### Cosa si perde / trade-off accettati

- **I dati transitano per infrastruttura ISV:** il backend ISV chiama le API sorgente e scrive su OneLake. I dati "passano" per il cloud Agic Technology prima di arrivare su OneLake. Mitigazione: nessun dato viene persistito nel cloud ISV — solo in transito in memoria.
- **ISV paga il compute:** costo stimato < €1/mese per 100 clienti — accettabile.
- **Dipendenza da `delta-rs`:** scrivere Delta Lake senza Spark richiede la libreria Rust-based `delta-rs`. È matura (usata in produzione da Databricks, Polars, DuckDB) ma aggiunge una dipendenza non-Microsoft.
- **Implementazione contratto WDK:** il backend deve implementare gli endpoint HTTP del Fabric Workload Development Kit (`IJobsController`) in Python — non esiste un SDK Python ufficiale, il contratto va implementato manualmente seguendo la specifica OpenAPI.

### Implicazioni architetturali

- Il `WORKLOAD_HOSTING_TYPE` rimane `FERemote` per il frontend.
- Il backend Azure Functions implementa **solo** i job endpoint — non gestisce item lifecycle (quello rimane in Fabric).
- La configurazione del connector (payload.json) viene letta dal backend tramite Fabric Items API ad ogni run — source of truth sempre in Fabric.
- Le credenziali vengono risolte dal backend ISV: Key Vault per client secret, MSAL per token OBO.

---

## 6. Requisiti di implementazione

### Contratto HTTP obbligatorio (Fabric WDK — IJobsController)

Il backend deve esporre i seguenti endpoint per integrarsi con Fabric Job Scheduler:

```
POST   /workload/jobs/instances/{jobInstanceId}          ← avvia un job
GET    /workload/jobs/instances/{jobInstanceId}           ← stato del job
DELETE /workload/jobs/instances/{jobInstanceId}           ← cancella il job
POST   /workload/jobs/instances/{jobInstanceId}/cancel    ← richiesta di cancel
```

La specifica completa è nella documentazione ufficiale Microsoft Fabric Workload Development Kit.

### Struttura del backend Python

```
backend/
├── function_app.py                    ← entry point Azure Functions
├── routes/
│   └── jobs.py                        ← IJobsController endpoints
├── services/
│   ├── fabric_client.py               ← lettura item definition da Fabric API
│   ├── auth_service.py                ← MSAL token acquisition + Key Vault
│   ├── onelake_writer.py              ← scrittura Delta su ABFS via delta-rs
│   └── job_tracker.py                 ← stato job (Azure Table Storage)
├── connectors/
│   ├── base_connector.py              ← BaseConnector (da ingestion-contracts.md)
│   ├── crm/crm_connector.py           ← CRMConnector (Dataverse OData)
│   ├── businesscentral/bc_connector.py
│   └── sql/sql_connector.py
├── models/
│   ├── connector_item_definition.py   ← dataclass (mirror di ConnectorItemDefinition.ts)
│   └── job_models.py                  ← request/response models WDK
├── requirements.txt
└── host.json
```

### Dipendenze Python principali

```
azure-functions>=1.21
azure-identity>=1.19          # DefaultAzureCredential, Managed Identity
azure-keyvault-secrets>=4.8   # Key Vault secret resolution
azure-storage-file-datalake>=12.17  # ABFS write su OneLake
msal>=1.31                    # OAuth2 client credentials (CRM, BC)
deltalake>=0.19               # delta-rs: scrittura Delta Lake senza Spark
pyarrow>=16.0                 # columnar data → Delta
httpx>=0.27                   # HTTP client async per chiamate OData
pydantic>=2.7                 # validazione config
```

### WorkloadManifest.xml — aggiunta endpoint backend

```xml
<CloudServiceConfiguration>
  <Service Name="Frontend"
           Url="https://connector.agic.technology" />
  <Service Name="Workload"
           Url="https://connector-api.agic.technology" />
</CloudServiceConfiguration>
```

---

## 7. Domande aperte

| # | Domanda | Responsabile | Scadenza |
|---|---|---|---|
| 1 | Dominio custom verificato in Entra ID ISV? (`agic.technology`) | Alessio | — |
| 2 | App registration Entra ID multi-tenant creata? (`FRONTEND_APPID`, `BACKEND_APPID`) | Alessio | — |
| 3 | Permessi Fabric API definiti nell'app registration? | Alessio | — |
| 4 | Azure Key Vault creato nel tenant ISV? | — | — |
| 5 | Strategia di persistenza stato job (Azure Table Storage vs Redis Cache)? | Team | — |
| 6 | Compliance: accordo data processing per il transito dati via ISV? (GDPR) | Alessio | — |

---

## 8. Riferimenti

- [Fabric Workload Development Kit — IJobsController](https://learn.microsoft.com/en-us/fabric/workload-development-kit/extensibility-back-end)
- [OneLake ABFS endpoint](https://learn.microsoft.com/en-us/fabric/onelake/onelake-access-api)
- [delta-rs Python bindings](https://delta-io.github.io/delta-rs/python/)
- [Azure Functions Python developer guide](https://learn.microsoft.com/en-us/azure/azure-functions/functions-reference-python)
- `.ai/contracts/ingestion-contracts.md` — contratti Python BaseConnector, moduli, watermark
- `.ai/architecture/target-architecture.md` — architettura generale del sistema
- `architettura-fabric-workload-crm.md` — documento architetturale condiviso (v1, pre-ADR-001)
