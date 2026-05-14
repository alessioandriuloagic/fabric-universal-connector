# Key Vault and OneLake configuration

This document explains how secrets should be stored in Key Vault and how the backend reads them to construct a OneLakeManager.

Secret naming
- Secrets are stored with name pattern: `{tenant_id}-{item_id}-credentials`
- The secret value MUST be a JSON blob containing at least the keys required by OneLake.

Recommended secret JSON shape
```json
{
  "FABRIC_TENANT_ID": "<fabric-tenant-id>",
  "FABRIC_CLIENT_ID": "<fabric-client-id>",
  "FABRIC_CLIENT_SECRET": "<fabric-client-secret>",
  "FABRIC_WORKSPACE_ID": "<workspace-guid>",
  "FABRIC_LAKEHOUSE_ID": "<lakehouse-guid>",
  "FABRIC_STATE_FILE": "open-mirroring/state.json"
}
```

How the backend uses the secret
1. `onelake_bridge.get_onelake_manager(item)` calls `keyvault_client.get_secret_json(tenant_id, item_id)`
2. If the secret exists, keys prefixed with `FABRIC_` are used to build `onelake_cfg` and passed to `build_onelake_manager`
3. If secret is missing, `load_onelake_config()` (env-based) is used as fallback

Deploy notes
- Store the `ENTRA_CLIENT_SECRET` (backend app secret) in Key Vault and load into the deployment environment or configure a managed identity with access to the Key Vault.
- Grant the backend's service principal (or managed identity) the `get` and `list` permissions for secrets in Key Vault.

Testing locally
- For local testing you can set env var `KEY_VAULT_URL` to a running Azure Key Vault and authenticate via `az login` or set `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID`.
- Alternatively set the required FABRIC_* env vars to simulate the secret-based configuration.

Security
- Rotate secrets regularly and avoid long-lived client secrets when possible.
- Consider using certificates for production instead of client secrets.
