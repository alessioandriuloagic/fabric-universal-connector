# Authentication & MSAL (Production)

This document explains how to configure MSAL-based authentication for the backend and how the code uses MSAL for application tokens and OBO flows. It also covers the frontend-to-backend token delegation flow.

## Environment variables
- ENTRA_CLIENT_ID: the backend application's client id (also BACKEND_APPID may be used for audience checks)
- ENTRA_CLIENT_SECRET: client secret for the backend app (store in Key Vault in production)
- ENTRA_TENANT_ID: tenant id to target (use 'common' for multi-tenant)
- BACKEND_APPID: used as JWT audience for incoming tokens (optional)
- USE_MSAL_FOR_SOURCE_AUTH: set to 'true' to prefer MSAL for source system client credentials
- DISABLE_AUTH: 'true' for local development only (DO NOT use in production)

## MSAL helpers (Backend)
- acquire_app_token(scopes): acquire application token using client credentials.
- acquire_token_on_behalf_of(user_assertion, scopes): exchange user token for downstream API token.
- acquire_token_on_behalf_of_async(user_assertion, scopes): async wrapper (runs blocking MSAL call in thread) for use from async code.

## Frontend-to-Backend Token Delegation (OBO Flow)

### Frontend: Obtaining and Passing User Token

The frontend uses the `useFabricAuth` hook to obtain a user access token from the Fabric Workload Client:

```typescript
import { useFabricAuth } from "./components/useFabricAuth";

export const SourceConfig: React.FC<SourceConfigProps> = ({ workloadClient, onConfigReady }) => {
  const { getUserToken, isLoading, error } = useFabricAuth(workloadClient);

  const handleObtainUserToken = async () => {
    try {
      const token = await getUserToken();
      setUserToken(token);
      // Token is now available to pass in config.secrets["user_assertion"]
    } catch (err) {
      console.error("Failed to get user token:", err);
    }
  };

  // When saving configuration, pass the user_assertion in secrets:
  const config = {
    base_url: baseUrl,
    company_id: company,
    entities: entities.split(",").map(e => e.trim()),
    secrets: {
      client_id: "...",
      client_secret: "...",
      user_assertion: userToken  // <-- User token for OBO delegation
    }
  };
};
```

**Key points:**
- Call `useFabricAuth(workloadClient)` to get the `getUserToken` function.
- Call `await getUserToken()` to obtain a user access token interactively (may trigger browser authentication).
- Pass the user token in `config.secrets["user_assertion"]` when saving the connector item.
- Clear the user token from state immediately after saving—do not persist it long-term.

### Backend: Using User Assertion for OBO

When the backend receives a connector configuration with `user_assertion`:

1. The ConnectorBase or specific connector adapter checks if `credentials.get("user_assertion")` is present.
2. If present, the connector calls `acquire_obo_token_for_scopes()` to exchange the user token for a delegated token.
3. The delegated token is used to call the source API on behalf of the user.
4. The original user token is not persisted; it is used only during the authentication handshake.

Example (Business Central adapter):
```python
async def _refresh_token(self):
    """Refresh or obtain an access token for calling the Business Central API."""
    user_assertion = self.credentials.get("user_assertion")
    
    if user_assertion:
        # OBO flow: exchange user token for delegated BC token
        logger.info("Using OBO flow with user_assertion", extra={"tenant_id": self.tenant_id})
        return await acquire_obo_token_for_scopes(
            user_assertion=user_assertion,
            scopes=self.bc_scopes
        )
    
    # Otherwise, use MSAL client credentials or fallback token endpoint
    ...
```

## Backend Code Usage

Connectors which call source APIs (e.g., Business Central, Dynamics 365, Salesforce, SAP) now:
1. Prefer MSAL (if `USE_MSAL_FOR_SOURCE_AUTH=true`) for application-level authentication.
2. Support OBO flows: if a connector's credentials blob contains a `user_assertion` field (a user access token), the connector will exchange it for a delegated token to call the source API on behalf of that user.

## Security Notes

### Frontend
- Do NOT persist `user_assertion` tokens in localStorage or sessionStorage.
- Request user tokens only when needed (e.g., when user clicks "Obtain User Token").
- Clear the token from state immediately after successful configuration save.
- Treat user tokens as short-lived credentials; do not cache them for extended periods.

### Backend
- Never commit secrets (ENTRA_CLIENT_SECRET) into source control. Use Key Vault and managed identities.
- Use DISABLE_AUTH only for local testing.
- Always validate incoming JWT tokens using JWKS and check tenant isolation (`assert_item_belongs_to_tenant`).
- When receiving a `user_assertion`, verify it is from the same tenant as the item.

## Deployment Checklist

- [ ] Register backend Entra application with proper app roles and permissions for source systems.
- [ ] Store ENTRA_CLIENT_SECRET in Key Vault.
- [ ] Configure Key Vault access for the backend service (managed identity or app registration).
- [ ] Set USE_MSAL_FOR_SOURCE_AUTH=true in production.
- [ ] Register source system applications (BC, D365, Salesforce, SAP) in Entra with appropriate permissions.
- [ ] Test OBO flow locally with DISABLE_AUTH=true first.
- [ ] Enable JWKS-based token validation for production.

