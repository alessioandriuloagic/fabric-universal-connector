"""
backend/src/token_validator.py

Token validation and MSAL production helpers.

This module provides:
- JWT verification using JWKS (signature + claims checks)
- A development fallback (DISABLE_AUTH) for local testing
- MSAL ConfidentialClientApplication helpers for acquiring application tokens
- On-Behalf-Of (OBO) support helper for exchanging user tokens if backend needs to call downstream APIs

Security notes:
- In production, set ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET, ENTRA_TENANT_ID and BACKEND_APPID appropriately.
- KEEP SECRETS OUT OF SOURCE CONTROL. Use Key Vault and environment variables.
"""
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Request, status
from pydantic import BaseModel
import os
import logging
import requests
import jwt
import msal
import asyncio

logger = logging.getLogger(__name__)


class EntraToken(BaseModel):
    """Structured token info extracted from validated JWT."""
    tid: str
    oid: Optional[str] = None
    upn: Optional[str] = None
    scopes: Optional[list[str]] = None
    raw: dict = {}


JWKS_CACHE: dict = {}


def _get_openid_config(tenant: str = 'common') -> dict:
    """Fetch OpenID configuration for the given tenant (caches upstream responses)."""
    url = f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json()


def _get_jwks(jwks_uri: str) -> dict:
    """Fetch JWKS JSON and cache it for reuse."""
    if jwks_uri in JWKS_CACHE:
        return JWKS_CACHE[jwks_uri]
    r = requests.get(jwks_uri, timeout=5)
    r.raise_for_status()
    jwks = r.json()
    JWKS_CACHE[jwks_uri] = jwks
    return jwks


def get_msal_app() -> msal.ConfidentialClientApplication:
    """Create or return an MSAL ConfidentialClientApplication using env-configured credentials.

    Expects environment variables:
    - ENTRA_CLIENT_ID
    - ENTRA_CLIENT_SECRET (or ENTRA_CERTIFICATE)  # certificate not implemented here
    - ENTRA_TENANT_ID

    Returns an MSAL app instance which caches tokens internally.
    """
    client_id = os.getenv('ENTRA_CLIENT_ID') or os.getenv('BACKEND_APPID')
    client_secret = os.getenv('ENTRA_CLIENT_SECRET')
    tenant = os.getenv('ENTRA_TENANT_ID') or 'common'
    if not client_id or not client_secret:
        logger.debug('MSAL client_id/secret not fully configured; get_msal_app may be used only for non-production.')
    authority = f"https://login.microsoftonline.com/{tenant}"
    # MSAL will cache tokens to memory by default for the process lifetime
    app = msal.ConfidentialClientApplication(client_id, authority=authority, client_credential=client_secret)
    return app


def acquire_app_token(scopes: list[str]) -> Dict[str, Any]:
    """Acquire an application token (client credentials flow) for the given scopes.

    Returns the MSAL token response dict. Raises HTTPException on failure.
    """
    app = get_msal_app()
    if not app:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='MSAL app not configured')
    result = app.acquire_token_for_client(scopes=scopes)
    if 'access_token' not in result:
        logger.error('MSAL client credentials token acquisition failed: %s', result)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Failed to acquire app token')
    return result


def acquire_token_on_behalf_of(user_assertion: str, scopes: list[str]) -> Dict[str, Any]:
    """Perform OBO exchange to get a token to call downstream APIs on behalf of the user.

    Requires that the backend app has the proper delegated permissions and consent.
    """
    app = get_msal_app()
    if not app:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='MSAL app not configured')
    result = app.acquire_token_on_behalf_of(user_assertion=user_assertion, scopes=scopes)
    if 'access_token' not in result:
        logger.error('MSAL OBO token acquisition failed: %s', result)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Failed to acquire OBO token')
    return result


async def acquire_token_on_behalf_of_async(user_assertion: str, scopes: list[str]) -> Dict[str, Any]:
    """Async wrapper for OBO acquisition. Runs blocking MSAL call in a thread.

    Use this from async code paths (connectors, request handlers) to avoid
    blocking the event loop.
    """
    return await asyncio.to_thread(acquire_token_on_behalf_of, user_assertion, scopes)


def _verify_jwt(token: str) -> dict:
    """Verify JWT signature and claims using JWKS. Falls back to DISABLE_AUTH mode for local dev.

    Audience resolution order:
      1. BACKEND_APPID
      2. ENTRA_CLIENT_ID
      3. FRONTEND_APPID

    Returns the decoded token claims on success.
    """
    try:
        # Decode without verification first to discover tenant (tid)
        unverified = jwt.decode(token, options={"verify_signature": False})
        tid = unverified.get('tid', 'common')
        openid = _get_openid_config(tid)
        jwks = _get_jwks(openid['jwks_uri'])
        public_keys = {}
        for key in jwks.get('keys', []):
            kid = key.get('kid')
            try:
                public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            except Exception:
                continue
        headers = jwt.get_unverified_header(token)
        kid = headers.get('kid')
        key = public_keys.get(kid)
        if not key:
            raise Exception('Unable to find public key for kid')
        audience = os.getenv('BACKEND_APPID') or os.getenv('ENTRA_CLIENT_ID') or os.getenv('FRONTEND_APPID')
        decoded = jwt.decode(token, key=key, algorithms=['RS256'], audience=audience, options={"verify_exp": True})
        return decoded
    except Exception as e:
        # Development fallback: allow local testing when DISABLE_AUTH is enabled
        if os.getenv('DISABLE_AUTH', 'false').lower() in ('1', 'true'):
            logger.warning('DISABLE_AUTH enabled — decoding token without verification: %s', e)
            return jwt.decode(token, options={"verify_signature": False})
        logger.exception('JWT verification failed: %s', e)
        raise


async def validate_token(request: Request) -> EntraToken:
    """FastAPI dependency to validate incoming Bearer tokens and return EntraToken.

    Usage:
      token: EntraToken = Depends(validate_token)

    In production this performs JWKS verification. For advanced scenarios where a token
    needs to be validated via MSAL/OBO flows, combine this with acquire_token_on_behalf_of.
    """
    auth = request.headers.get('authorization') or request.headers.get('Authorization')
    if not auth:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing Authorization header')
    if not auth.lower().startswith('bearer '):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authorization header must be Bearer token')
    token = auth.split(' ', 1)[1].strip()
    try:
        decoded = _verify_jwt(token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')
    tid = decoded.get('tid') or decoded.get('tenant') or 'unknown'
    ente = EntraToken(
        tid=tid,
        oid=decoded.get('oid'),
        upn=decoded.get('upn') or decoded.get('preferred_username'),
        scopes=decoded.get('scp', '').split() if decoded.get('scp') else [],
        raw=decoded,
    )
    return ente


async def assert_item_belongs_to_tenant(item_id: str, tid: str) -> None:
    """Ensure the Fabric item belongs to the tenant extracted from the token."""
    try:
        from storage import get_item
    except Exception:
        from storage import storage as _s
        def get_item(i):
            return _s.get_item(i)
    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Item not found')
    if item.get('tenant_id') != tid:
        logger.warning('Tenant mismatch: token.tid=%s item.tenant=%s', tid, item.get('tenant_id'))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Item does not belong to tenant')
