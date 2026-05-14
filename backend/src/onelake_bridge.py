"""
Bridge module that loads the OneLake modules from backend_2 and exposes a
helper to create a configured OneLakeManager for a given item.

This module performs a best-effort import of the backend_2 modules by adding
its "modules" folder to sys.path at runtime. It then uses the provided
onelake_config factory to build a OneLakeManager instance.

The function get_onelake_manager(item, fallback_source_creds=None) attempts to
read Fabric credentials from Key Vault first; if not present, it falls back to
environment variables or provided source credentials.
"""

import os
import sys
import json
from typing import Optional, Dict, Any

# Compute path to backend_2 modules relative to this file
MODULES_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend_2", "python", "modules")
)
if os.path.isdir(MODULES_PATH) and MODULES_PATH not in sys.path:
    sys.path.insert(0, MODULES_PATH)

# Import factories from backend_2 modules
try:
    from onelake_config import load_onelake_config, build_onelake_manager
except Exception as e:
    # Import failure will be surfaced when caller tries to build a manager
    load_onelake_config = None
    build_onelake_manager = None

# Local keyvault helper
try:
    from keyvault_client import get_secret_json
except Exception:
    # If local keyvault helper isn't available, define a no-op
    def get_secret_json(tenant_id: str, item_id: str) -> Optional[Dict[str, Any]]:
        return None


def get_onelake_manager(item: Dict[str, Any], fallback_source_creds: Optional[Dict[str, Any]] = None):
    """Return a configured OneLakeManager for the provided item.

    Strategy:
    1. Try to get secrets JSON from Key Vault for tenant/item. If found and it
       contains FABRIC_* keys, use them to build the manager.
    2. Otherwise call load_onelake_config() which reads environment variables.
       As a last resort, try to construct minimal onelake_cfg from fallback_source_creds
       (e.g., if the same SP is used for source and OneLake).

    The returned manager is the backend_2 OneLakeManager instance.
    """
    # 1) Try Key Vault
    tenant_id = item.get("tenant_id")
    item_id = item.get("id") or item.get("item_id")
    secret = None
    try:
        secret = get_secret_json(tenant_id, item_id)
    except Exception:
        secret = None

    if secret:
        # Expect secret to contain FABRIC_* keys or onelake credential keys
        onelake_cfg = {
            "tenant_id": secret.get("FABRIC_TENANT_ID") or secret.get("tenant_id"),
            "client_id": secret.get("FABRIC_CLIENT_ID") or secret.get("client_id"),
            "client_secret": secret.get("FABRIC_CLIENT_SECRET") or secret.get("client_secret"),
            "workspace_id": secret.get("FABRIC_WORKSPACE_ID"),
            "lakehouse_id": secret.get("FABRIC_LAKEHOUSE_ID"),
            "mirrored_db_id": secret.get("FABRIC_MIRRORED_DB_ID"),
            "state_file": secret.get("FABRIC_STATE_FILE"),
        }
        # Fill missing values from env via load_onelake_config when available
        if load_onelake_config:
            cfg_env = load_onelake_config(fallback_tenant_id=tenant_id,
                                          fallback_client_id=onelake_cfg.get("client_id"),
                                          fallback_client_secret=onelake_cfg.get("client_secret"))
            for k, v in cfg_env.items():
                onelake_cfg.setdefault(k, v)

        if build_onelake_manager is None:
            raise RuntimeError("OneLake build factory not available (backend_2 modules missing)")
        return build_onelake_manager(onelake_cfg)

    # 2) No secret in Key Vault — try env-based factory
    if load_onelake_config and build_onelake_manager:
        onelake_cfg = load_onelake_config(
            fallback_tenant_id=(fallback_source_creds or {}).get("tenant_id"),
            fallback_client_id=(fallback_source_creds or {}).get("client_id"),
            fallback_client_secret=(fallback_source_creds or {}).get("client_secret"),
        )
        return build_onelake_manager(onelake_cfg)

    # 3) Can't build a manager
    raise RuntimeError("Unable to construct OneLakeManager: missing backend_2 modules and no Key Vault secrets")
