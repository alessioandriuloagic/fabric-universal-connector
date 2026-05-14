"""
Simple Key Vault client wrapper for storing and retrieving JSON secrets per tenant/item.

This module uses DefaultAzureCredential to authenticate. The environment should provide
either:
- AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID for a service principal, or
- Managed Identity / Developer login for DefaultAzureCredential to work.

Secrets are stored with a stable name pattern: "{tenant_id}-{item_id}-credentials".
The secret value is the JSON-serialized credentials blob (e.g. OneLake and source creds).

Note: This is a minimal helper used in development. In production you may want
additional encryption, versioning, or secret rotation policies.
"""

import os
import json
from typing import Optional, Dict, Any

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def _get_secret_client() -> SecretClient:
    """Create a SecretClient for the configured Key Vault URL.

    Environment variables:
    - KEY_VAULT_URL (required)
    - DefaultAzureCredential uses AZURE_* env vars if set, otherwise managed identity.
    """
    key_vault_url = os.getenv("KEY_VAULT_URL")
    if not key_vault_url:
        raise RuntimeError("KEY_VAULT_URL not set in environment")
    credential = DefaultAzureCredential()
    return SecretClient(vault_url=key_vault_url, credential=credential)


def set_secret_json(tenant_id: str, item_id: str, payload: Dict[str, Any]) -> None:
    """Store a JSON-serializable payload as a secret for the given tenant/item.

    The secret name uses the pattern: {tenant_id}-{item_id}-credentials
    """
    secret_name = f"{tenant_id}-{item_id}-credentials"
    client = _get_secret_client()
    client.set_secret(secret_name, json.dumps(payload))


def get_secret_json(tenant_id: str, item_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve and parse the JSON secret for the given tenant/item.

    Returns None if the secret is not found.
    """
    secret_name = f"{tenant_id}-{item_id}-credentials"
    try:
        client = _get_secret_client()
        secret = client.get_secret(secret_name)
        return json.loads(secret.value)
    except Exception:
        return None
