"""
Credential resolution service.

Handles all three authentication modes from ConnectorItemDefinition:
  1. fabric_connection   — calls Fabric Connections API to retrieve secret
  2. keyvault_reference  — resolves secret from Azure Key Vault (Managed Identity)
  3. service_principal   — uses inline tenantId/clientId + secret from (1) or (2)

Output: ResolvedCredentials — plain Python object with the actual values needed
by each connector module to call the source system.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import msal
from azure.identity.aio import ManagedIdentityCredential, DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient

from app.exceptions import AuthenticationError, ConnectorFatalError
from app.models.connector_item_definition import (
    AuthConfiguration,
    FabricConnectionAuth,
    KeyVaultReferenceAuth,
    ServicePrincipalAuth,
)

log = logging.getLogger(__name__)

FABRIC_CONNECTIONS_API = "https://api.fabric.microsoft.com"


@dataclass(frozen=True)
class ResolvedCredentials:
    """
    Resolved credential values for a source system.
    Only the fields relevant to the chosen auth mode are populated.
    """
    tenant_id: Optional[str]
    client_id: Optional[str]
    client_secret: Optional[str]
    connection_string: Optional[str] = None

    def has_client_credentials(self) -> bool:
        return bool(self.tenant_id and self.client_id and self.client_secret)


async def resolve_credentials(
    auth_config: Optional[AuthConfiguration],
    fabric_token: str,
) -> ResolvedCredentials:
    """
    Resolves the actual credentials from the auth configuration.

    fabric_token: the SubjectAndApp token forwarded from the Fabric job request —
                  used to call Fabric Connections API when mode=fabric_connection.
    """
    if auth_config is None:
        raise ConnectorFatalError(
            "No authentication configuration in item definition",
            "CONFIG_VALIDATION_ERROR",
        )

    if isinstance(auth_config, FabricConnectionAuth):
        return await _resolve_fabric_connection(auth_config, fabric_token)

    if isinstance(auth_config, KeyVaultReferenceAuth):
        return await _resolve_keyvault(auth_config)

    if isinstance(auth_config, ServicePrincipalAuth):
        secret_ref = auth_config.secret_ref
        if isinstance(secret_ref, FabricConnectionAuth):
            conn_creds = await _resolve_fabric_connection(secret_ref, fabric_token)
            client_secret = conn_creds.client_secret
        elif isinstance(secret_ref, KeyVaultReferenceAuth):
            kv_creds = await _resolve_keyvault(secret_ref)
            client_secret = kv_creds.client_secret
        else:
            raise ConnectorFatalError(
                "service_principal secretRef must be fabric_connection or keyvault_reference",
                "CONFIG_VALIDATION_ERROR",
            )
        return ResolvedCredentials(
            tenant_id=auth_config.tenant_id,
            client_id=auth_config.client_id,
            client_secret=client_secret,
        )

    raise ConnectorFatalError(
        f"Unknown auth mode: {type(auth_config).__name__}",
        "CONFIG_VALIDATION_ERROR",
    )


async def acquire_msal_token(
    creds: ResolvedCredentials,
    scope: str,
) -> str:
    """
    Acquires an OAuth2 access token using MSAL client credentials flow.
    Used by CRM and BC connectors to call source APIs.
    """
    if not creds.has_client_credentials():
        raise AuthenticationError(
            "Cannot acquire MSAL token: credentials are incomplete"
        )

    msal_app = msal.ConfidentialClientApplication(
        client_id=creds.client_id,
        client_credential=creds.client_secret,
        authority=f"https://login.microsoftonline.com/{creds.tenant_id}",
    )

    result = await asyncio.to_thread(msal_app.acquire_token_for_client, [scope])

    if "access_token" not in result:
        error_desc = result.get("error_description", result.get("error", "unknown"))
        log.warning("MSAL token acquisition failed: %s", error_desc)
        raise AuthenticationError(f"MSAL token acquisition failed: {error_desc}")

    log.debug("MSAL token acquired for scope %s", scope)
    return result["access_token"]


# ── Private helpers ────────────────────────────────────────────────────────────

async def _resolve_fabric_connection(
    auth: FabricConnectionAuth,
    fabric_token: str,
) -> ResolvedCredentials:
    """
    Calls Fabric Connections API to retrieve the credentials stored in a
    Fabric Connection item.

    Fabric Connections API:
      GET /v1/connections/{connectionId}/getSecrets
      Authorization: Bearer {fabric_token}
    """
    import httpx

    url = (
        f"{FABRIC_CONNECTIONS_API}/v1/connections"
        f"/{auth.fabric_connection_id}/getSecrets"
    )
    headers = {"Authorization": f"Bearer {fabric_token}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers)

        if resp.status_code == 404:
            raise ConnectorFatalError(
                f"Fabric Connection {auth.fabric_connection_id} not found",
                "CONFIG_VALIDATION_ERROR",
            )
        if resp.status_code in (401, 403):
            raise AuthenticationError(
                f"No access to Fabric Connection {auth.fabric_connection_id}"
            )
        if resp.status_code != 200:
            raise AuthenticationError(
                f"Fabric Connections API returned {resp.status_code}: {resp.text[:200]}"
            )

        data = resp.json()
        credentials = data.get("value", data)

        tenant_id = _extract_field(credentials, ["tenantId", "tenant_id"])
        client_id = _extract_field(credentials, ["clientId", "client_id", "username"])
        client_secret = _extract_field(
            credentials, ["clientSecret", "client_secret", "password"]
        )

        return ResolvedCredentials(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise AuthenticationError(
            f"Network error calling Fabric Connections API: {exc}"
        ) from exc


async def _resolve_keyvault(auth: KeyVaultReferenceAuth) -> ResolvedCredentials:
    """
    Resolves credentials from Azure Key Vault using Managed Identity.
    """
    try:
        async with DefaultAzureCredential() as azure_cred:
            async with SecretClient(
                vault_url=auth.key_vault_uri, credential=azure_cred
            ) as kv:
                client_secret_obj = await kv.get_secret(auth.client_secret_name)
                client_secret = client_secret_obj.value

                client_id: Optional[str] = None
                if auth.client_id_secret_name:
                    client_id_obj = await kv.get_secret(auth.client_id_secret_name)
                    client_id = client_id_obj.value

                tenant_id: Optional[str] = None
                if auth.tenant_id_secret_name:
                    tenant_id_obj = await kv.get_secret(auth.tenant_id_secret_name)
                    tenant_id = tenant_id_obj.value

        return ResolvedCredentials(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

    except Exception as exc:
        raise AuthenticationError(
            f"Key Vault secret resolution failed ({auth.key_vault_uri}): {exc}"
        ) from exc


def _extract_field(data: dict, keys: list[str]) -> Optional[str]:
    for k in keys:
        if k in data and data[k]:
            return str(data[k])
    return None
