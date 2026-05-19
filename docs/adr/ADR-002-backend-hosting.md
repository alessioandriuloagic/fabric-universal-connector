# ADR-002 — Hosting del backend ISV: Azure Container Apps

| Campo | Valore |
|---|---|
| **ID** | ADR-002 |
| **Titolo** | Scelta della piattaforma di hosting per il backend Python |
| **Stato** | Accettato |
| **Data** | 2026-05-19 |
| **Autori** | Alessio Andriulo — Agic Technology srl |
| **Revisori** | — |
| **Sostituisce** | Proposta iniziale in ADR-001 §3 (Azure Functions) |
| **Collegato a** | `docs/adr/ADR-001-execution-model.md`, `backend/Dockerfile`, `backend/requirements.txt` |

---

## 1. Contesto

ADR-001 ha deciso che l'ingestion runtime è un backend Python ISV ospitato nel cloud Agic Technology, che riceve le chiamate di Fabric Job Scheduler tramite il contratto HTTP `IJobsController` del Fabric Workload Development Kit.

ADR-001 indicava Azure Functions come piattaforma candidata principale, ma la scelta definitiva era rinviata a dopo la costruzione del backend. Il backend Python è ora completo (`backend/app/`) e la valutazione può essere fatta su dati concreti anziché su stime astratte.

### Caratteristiche del backend costruito

| Proprietà | Valore |
|---|---|
| Framework | FastAPI (ASGI) + uvicorn |
| Dipendenze principali | `delta-rs`, `pyarrow`, `pyodbc`, `msodbcsql18`, `msal`, `azure-identity` |
| Peso immagine Docker stimato | ~600–800 MB (include ODBC Driver 18) |
| Modello di esecuzione | HTTP request → background task asincrono → polling GET status |
| Timeout massimo per job | Nessun limite architetturale (dipende dal volume dati del cliente) |
| Background tasks | `fastapi.BackgroundTasks` — esecuzione asincrona nel processo uvicorn |

---

## 2. Opzioni valutate

### Opzione A — Azure Functions (Consumption Plan)

Il piano originariamente citato in ADR-001.

**Problema emerso durante lo sviluppo:**

Il backend richiede `msodbcsql18` (Microsoft ODBC Driver 18 for SQL Server) installato a livello di sistema operativo, e le librerie `delta-rs` + `pyarrow` portano un peso complessivo di ~600–800 MB. Il piano Consumption di Azure Functions ha un limite di 250 MB per il pacchetto di deployment ZIP e non supporta immagini Docker custom di dimensioni arbitrarie.

**Ulteriori vincoli tecnici:**

- Azure Functions v2 (Python) non supporta nativamente `fastapi.BackgroundTasks` in modo affidabile: la Function restituisce la risposta HTTP e il processo può essere ucciso prima che il background task completi.
- Il contratto WDK richiede che il job continui a girare dopo che il POST restituisce `InProgress` — questo pattern è nativo in ASGI + uvicorn, non in Functions.
- Il timeout di 10 minuti del piano Consumption è insufficiente per initial load su grandi dataset (potenzialmente 30–60 minuti per 500K record).

**Per ovviare a questi limiti servirebbe il Piano Premium** (~€50+/mese fissi), che annulla completamente il vantaggio di costo rispetto alle alternative.

**Verdict: ❌ Scartata** — incompatibilità strutturale con il modello di esecuzione asincrona e i requisiti di dipendenze.

---

### Opzione B — Azure Container Apps ✅ SCELTA ADOTTATA

Piattaforma serverless container-based con scaling a zero.

**Compatibilità con il codice costruito:**

Il backend gira invariato con `docker run` o `uvicorn app.main:app` — zero modifiche al codice applicativo. Il `Dockerfile` già presente in `backend/Dockerfile` è l'unico artefatto di deployment aggiuntivo necessario.

**Modello di scaling:**

```
Idle (nessun job attivo):     0 repliche → costo zero
Job in esecuzione:            1–N repliche (autoscale su HTTP queue depth)
Job completato:               scala a zero dopo il cooldown (default 300s)
```

**Stima costi per 100 clienti** (ogni cliente esegue 24 job/giorno × 30 giorni):

| Voce | Calcolo | Costo stimato |
|---|---|---|
| vCPU-s (0.5 vCPU × 30s/job × 72.000 job/mese) | 1.080.000 vCPU-s | ~€2.50 |
| GiB-s (1 GiB × 30s/job × 72.000 job/mese) | 2.160.000 GiB-s | ~€2.40 |
| Richieste HTTP | 216.000 (3 req/job) | ~€0.01 |
| **Totale** | | **~€5/mese** |

I primi 180.000 vCPU-s e 360.000 GiB-s/mese sono gratuiti — il costo reale per i primi ~15 clienti è **zero**.

---

### Opzione C — Azure App Service (B1/B2)

Piano always-on con VM dedicata.

- Costo fisso ~€15–30/mese indipendentemente dal numero di job eseguiti.
- Nessun scaling a zero — inappropriato per un workload batch con picchi sporadici.
- Nessun vantaggio tecnico rispetto a Container Apps per questo caso d'uso.

**Verdict: ❌ Scartata** — costo fisso non giustificato, nessun vantaggio tecnico.

---

## 3. Decisione: Azure Container Apps

### Architettura di deployment

```
Azure Container Registry (ISV)
  └── fabric-universal-connector-backend:1.0.0
        ↑ pushed da CI/CD GitHub Actions

Azure Container Apps Environment (ISV — West Europe)
  └── Container App: fuc-backend
        ├── Image: acr.azurecr.io/fuc-backend:1.0.0
        ├── CPU: 0.5 vCPU, Memory: 1 GiB
        ├── Min replicas: 0 (scala a zero)
        ├── Max replicas: 10
        ├── Scale rule: HTTP — 10 concurrent requests per replica
        └── Ingress: HTTPS external, port 8000

        Secrets (Azure Key Vault reference):
          FABRIC_TENANT_ID
          BACKEND_APP_ID
          AZURE_STORAGE_CONNECTION_STRING (Phase 2)
```

### Endpoint pubblico

```
https://fuc-backend.{environment}.azurecontainerapps.io
```

Registrato in `WorkloadManifest.xml`:

```xml
<CloudServiceConfiguration>
  <Service Name="Frontend"
           Url="https://connector.agic.technology" />
  <Service Name="Workload"
           Url="https://fuc-backend.{environment}.azurecontainerapps.io" />
</CloudServiceConfiguration>
```

### Flusso chiamata da Fabric Job Scheduler

```
Fabric Job Scheduler
  │
  │  POST /workload/jobs/instances/{jobInstanceId}
  │  Authorization: Bearer {SubjectAndApp token}
  ▼
Azure Container Apps (scala da 0 → 1 replica in ~2-5s)
  │
  ├── Valida token Bearer
  ├── Crea JobRecord (status=InProgress)
  ├── Risponde HTTP 200 { "status": "InProgress" }   ← Fabric smette di aspettare
  │
  └── BackgroundTask:
        ├── Legge item definition da Fabric Items API
        ├── Risolve credenziali (Fabric Connection / Key Vault)
        ├── Esegue connector (CRM / BC / SQL)
        ├── Scrive Bronze Delta su OneLake (ABFS + delta-rs)
        └── Aggiorna JobRecord (status=Completed/Failed)

Fabric Job Scheduler (polling)
  │  GET /workload/jobs/instances/{jobInstanceId}
  └── Riceve { "status": "Completed" } → job terminato
```

---

## 4. Conseguenze e implicazioni

### Cosa si guadagna rispetto ad Azure Functions

| Aspetto | Azure Functions (Piano Premium) | Azure Container Apps |
|---|---|---|
| Costo fisso | ~€50/mese | ~€0/mese in idle |
| Background tasks | Workaround necessario | Nativo (uvicorn) |
| Timeout massimo | 60 min (Premium) | Illimitato |
| ODBC Driver 18 | Richiede configurazione custom | Nel Dockerfile standard |
| Dimensione immagine | Limite 250 MB (Consumption) | Nessun limite |
| Modifiche al codice | Wrapper `function_app.py` | Zero |

### Trade-off accettati

- **Cold start di ~2–5 secondi** quando la replica scala da zero. Accettabile perché Fabric Job Scheduler non ha un SLA di latenza stringente per l'avvio del job — il polling GET arriverà comunque dopo che il job è già partito.
- **Gestione del container registry**: richiede un Azure Container Registry ISV. Costo ACR Basic: ~€5/mese. Alternativa: GitHub Container Registry (gratuito per immagini pubbliche, ma non raccomandato per IP protection).
- **Dipendenza da Docker build pipeline**: il CI/CD deve costruire e pushare l'immagine ad ogni release. Aggiunge ~3–5 minuti alla pipeline.

### Implicazioni architetturali

- Il `WORKLOAD_HOSTING_TYPE` rimane `FERemote` per il frontend — invariato.
- Il `WorkloadManifest.xml` deve essere aggiornato con l'URL del Container App dopo il primo deployment.
- Il `BACKEND_APPID` in `.env.dev` / `.env.prod` deve essere popolato con l'app registration Entra ID del backend.
- Il job state è in-memory (Phase 1). Con più repliche attive contemporaneamente, job avviati su replica A non sono visibili dalla replica B. **Soluzione Phase 2:** abilitare `USE_TABLE_STORAGE=true` e configurare `AZURE_STORAGE_CONNECTION_STRING` — il `job_tracker.py` supporta già entrambe le modalità senza modifiche al codice applicativo.

---

## 5. Path di migrazione verso Azure Functions (se necessario)

Se in futuro i vincoli cambiano (es. rimozione del SQL connector che non richiede ODBC, riduzione del peso delle dipendenze), la migrazione ad Azure Functions richiede:

1. Aggiungere `function_app.py` come thin wrapper ASGI → Functions custom handler
2. Aggiungere `host.json` con `customHandler` configuration
3. Nessuna modifica al codice applicativo in `app/`

Il backend è progettato per essere hosting-agnostic esattamente per questo motivo.

---

## 6. Domande aperte

| # | Domanda | Responsabile | Scadenza |
|---|---|---|---|
| 1 | Azure Container Registry creato nel tenant ISV? | Alessio | — |
| 2 | URL definitivo del Container App Environment? (`{environment}`) | Alessio | — |
| 3 | `WorkloadManifest.xml` aggiornato con URL backend? | — | Dopo primo deploy |
| 4 | `BACKEND_APP_ID` registrato in Entra ID? | Alessio | — |
| 5 | Phase 2: Azure Storage Account per job state multi-replica? | Team | Phase 2 |

---

## 7. Riferimenti

- [Azure Container Apps — documentazione](https://learn.microsoft.com/en-us/azure/container-apps/)
- [Azure Container Apps — pricing](https://azure.microsoft.com/en-us/pricing/details/container-apps/)
- [Fabric WDK — IJobsController spec](https://learn.microsoft.com/en-us/fabric/workload-development-kit/extensibility-back-end)
- `docs/adr/ADR-001-execution-model.md` — decisione sul modello di esecuzione (ISV backend)
- `backend/Dockerfile` — immagine container del backend
- `backend/requirements.txt` — dipendenze Python (motivazione dei 600–800 MB)
- `backend/app/services/job_tracker.py` — supporto dual-mode in-memory / Table Storage
