"""Tests for credential resolution logic in auth_service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.auth_service import (
    ResolvedCredentials,
    acquire_msal_token,
    resolve_credentials,
)
from app.models.connector_item_definition import (
    FabricConnectionAuth,
    KeyVaultReferenceAuth,
    ServicePrincipalAuth,
)
from app.exceptions import AuthenticationError, ConnectorFatalError


# ── acquire_msal_token ─────────────────────────────────────────────────────────

async def test_acquire_msal_token_success():
    creds = ResolvedCredentials(tenant_id="t1", client_id="c1", client_secret="s1")
    token_response = {"access_token": "eyJ.test.token"}

    with patch("app.services.auth_service.msal.ConfidentialClientApplication") as MockApp:
        MockApp.return_value.acquire_token_for_client.return_value = token_response
        token = await acquire_msal_token(creds, "https://example.crm.dynamics.com/.default")

    assert token == "eyJ.test.token"
    MockApp.return_value.acquire_token_for_client.assert_called_once_with(
        ["https://example.crm.dynamics.com/.default"]
    )


async def test_acquire_msal_token_msal_error_raises():
    creds = ResolvedCredentials(tenant_id="t1", client_id="c1", client_secret="s1")
    error_response = {"error": "invalid_client", "error_description": "Bad credentials"}

    with patch("app.services.auth_service.msal.ConfidentialClientApplication") as MockApp:
        MockApp.return_value.acquire_token_for_client.return_value = error_response
        with pytest.raises(AuthenticationError, match="MSAL token acquisition failed"):
            await acquire_msal_token(creds, "scope")


async def test_acquire_msal_token_missing_credentials_raises():
    creds = ResolvedCredentials(tenant_id=None, client_id=None, client_secret=None)
    with pytest.raises(AuthenticationError, match="incomplete"):
        await acquire_msal_token(creds, "scope")


async def test_acquire_msal_token_partial_credentials_raises():
    creds = ResolvedCredentials(tenant_id="t1", client_id=None, client_secret="s1")
    with pytest.raises(AuthenticationError, match="incomplete"):
        await acquire_msal_token(creds, "scope")


# ── resolve_credentials: fabric_connection ────────────────────────────────────

async def test_resolve_credentials_fabric_connection_success():
    auth = FabricConnectionAuth(mode="fabric_connection", fabricConnectionId="conn-123")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "value": {"clientId": "cid", "tenantId": "tid", "clientSecret": "sec"}
    }

    with patch("app.services.auth_service.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        creds = await resolve_credentials(auth, "fabric-bearer-token")

    assert creds.client_id == "cid"
    assert creds.tenant_id == "tid"
    assert creds.client_secret == "sec"


async def test_resolve_credentials_fabric_connection_404_raises():
    auth = FabricConnectionAuth(mode="fabric_connection", fabricConnectionId="bad-id")
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("app.services.auth_service.httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        with pytest.raises(ConnectorFatalError, match="not found"):
            await resolve_credentials(auth, "token")


# ── resolve_credentials: keyvault_reference ───────────────────────────────────

async def test_resolve_credentials_keyvault_success():
    auth = KeyVaultReferenceAuth(
        mode="keyvault_reference",
        keyVaultUri="https://myvault.vault.azure.net",
        clientSecretName="my-secret",
        clientIdSecretName="my-client-id",
        tenantIdSecretName="my-tenant-id",
    )

    def _make_secret(value: str):
        m = MagicMock()
        m.value = value
        return m

    mock_kv = AsyncMock()
    mock_kv.get_secret.side_effect = [
        _make_secret("secret-value"),
        _make_secret("client-id-value"),
        _make_secret("tenant-id-value"),
    ]

    with patch("app.services.auth_service.DefaultAzureCredential") as MockCred, \
         patch("app.services.auth_service.SecretClient") as MockSecretClient:
        MockCred.return_value.__aenter__ = AsyncMock(return_value=MockCred.return_value)
        MockCred.return_value.__aexit__ = AsyncMock(return_value=False)
        MockSecretClient.return_value.__aenter__ = AsyncMock(return_value=mock_kv)
        MockSecretClient.return_value.__aexit__ = AsyncMock(return_value=False)

        creds = await resolve_credentials(auth, "token")

    assert creds.client_secret == "secret-value"
    assert creds.client_id == "client-id-value"
    assert creds.tenant_id == "tenant-id-value"


# ── resolve_credentials: none ─────────────────────────────────────────────────

async def test_resolve_credentials_none_raises():
    with pytest.raises(ConnectorFatalError, match="No authentication configuration"):
        await resolve_credentials(None, "token")
