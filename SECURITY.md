<!-- BEGIN MICROSOFT SECURITY.MD V0.0.8 BLOCK -->

## Security

Microsoft takes the security of our software products and services seriously, which includes all source code repositories managed through our GitHub organizations, which include [Microsoft](https://github.com/microsoft), [Azure](https://github.com/Azure), [DotNet](https://github.com/dotnet), [AspNet](https://github.com/aspnet), [Xamarin](https://github.com/xamarin), and [our GitHub organizations](https://opensource.microsoft.com/).

If you believe you have found a security vulnerability in any Microsoft-owned repository that meets [Microsoft's definition of a security vulnerability](https://aka.ms/opensource/security/definition), please report it to us as described below.

## Reporting Security Issues

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them to the Microsoft Security Response Center (MSRC) at [https://msrc.microsoft.com/create-report](https://aka.ms/opensource/security/create-report).

If you prefer to submit without logging in, send email to [secure@microsoft.com](mailto:secure@microsoft.com).  If possible, encrypt your message with our PGP key; please download it from the [Microsoft Security Response Center PGP Key page](https://aka.ms/opensource/security/pgpkey).

You should receive a response within 24 hours. If for some reason you do not, please follow up via email to ensure we received your original message. Additional information can be found at [microsoft.com/msrc](https://aka.ms/opensource/security/msrc). 

Please include the requested information listed below (as much as you can provide) to help us better understand the nature and scope of the possible issue:

  * Type of issue (e.g. buffer overflow, SQL injection, cross-site scripting, etc.)
  * Full paths of source file(s) related to the manifestation of the issue
  * The location of the affected source code (tag/branch/commit or direct URL)
  * Any special configuration required to reproduce the issue
  * Step-by-step instructions to reproduce the issue
  * Proof-of-concept or exploit code (if possible)
  * Impact of the issue, including how an attacker might exploit the issue

This information will help us triage your report more quickly.

If you are reporting for a bug bounty, more complete reports can contribute to a higher bounty award. Please visit our [Microsoft Bug Bounty Program](https://aka.ms/opensource/security/bounty) page for more details about our active programs.

## Preferred Languages

We prefer all communications to be in English.

## Policy

Microsoft follows the principle of [Coordinated Vulnerability Disclosure](https://aka.ms/opensource/security/cvd).

<!-- END MICROSOFT SECURITY.MD BLOCK -->

## Security Model

This section describes the actual security architecture of the Fabric Universal Connector.

### Authentication & Authorization

- **Frontend ↔ Fabric**: OAuth 2.0 managed by the Fabric SDK (Entra ID). The frontend never handles tokens directly.
- **Fabric Scheduler ↔ Backend**: Every job request from Fabric carries a signed JWT. The backend validates it via PyJWT + Microsoft JWKS endpoint (`login.microsoftonline.com/{FABRIC_TENANT_ID}/discovery/v2.0/keys`). Required env vars: `FABRIC_TENANT_ID`, `BACKEND_APP_ID`. When these are absent the service logs a warning and skips validation (local dev only).
- **Backend ↔ Source Systems**: Credentials are resolved at runtime via Fabric Connections (never stored in code or environment variables). Azure Key Vault references are supported as an alternative.
- **JWKS Key Rotation**: The JWKS client uses a 300-second key TTL (`lifespan=300`) — keys are automatically refreshed without restarting the service.

### Credential Isolation

Secrets are **never** stored in source code, image layers, or environment variables. The resolution chain is:

1. Fabric Connection (preferred) — credential stored in the customer's Fabric workspace
2. Azure Key Vault reference — URI resolved at job runtime
3. No plaintext credentials are accepted

### Tenant Isolation

Each customer's data is written to their own OneLake workspace. The backend uses per-job Fabric tokens (scoped to the customer's workspace) and never mixes data between tenants.

### Workload Scope Enforcement

Each scoped workload (`customer-insight-journey`, `sales-crm`, `business-central`) enforces an entity allowlist at the backend. Even if a connector is misconfigured with out-of-scope entities, only the entities defined in the workload config are ingested. SQL DB is user-defined and has no pre-set allowlist.

### CORS

The backend allows only explicitly listed origins. The default list covers Fabric platform endpoints and known ISV subdomains. Override with `CORS_ORIGINS` (comma-separated); append extras with `CORS_EXTRA_ORIGINS`. Wildcards are not used.

### Rate Limiting

All job endpoints are rate-limited via `slowapi` (60 requests/minute per IP). This prevents automated abuse and reduces the impact of token replay attacks.

### Health Endpoint Security

The `/health/detailed` endpoint is protected by the `X-Health-Token` header. If the `HEALTH_TOKEN` environment variable is not set, the endpoint returns 403 unconditionally (fail-safe). The `/health` liveness probe remains public.

### Dependency Management

- Python: `bandit -r app/ -ll` runs in CI and blocks merges on medium/high severity findings.
- Node.js: `npm audit --audit-level=high` runs in CI and blocks merges on high severity findings.

