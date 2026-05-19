"""
Dataverse Web API client (OData v4 + Change Tracking).

Implements full + incremental extraction with delta token pagination.
All calls are async via httpx.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlencode

import httpx

from app.exceptions import (
    AuthenticationError,
    EntityExtractionError,
    ThrottlingError,
    TransientError,
)

log = logging.getLogger(__name__)

ODATA_CONTEXT_DELETE = "#Microsoft.Dynamics.CRM.EntityList"


@dataclass
class DataversePage:
    records: List[Dict[str, Any]]
    next_link: Optional[str]
    delta_link: Optional[str]


class DataverseClient:
    """
    Stateless HTTP client for Dataverse Web API.
    Instances can be reused across entities within a single run.
    """

    def __init__(
        self,
        environment_url: str,
        api_version: str = "v9.2",
        page_size: int = 5000,
        http_timeout: float = 120.0,
    ):
        self.base_url = environment_url.rstrip("/")
        self.api_version = api_version
        self.page_size = page_size
        self.timeout = http_timeout

    def _entity_url(self, plural_name: str) -> str:
        return f"{self.base_url}/api/data/{self.api_version}/{plural_name}"

    def _headers(self, token: str, prefer_track_changes: bool = False) -> Dict[str, str]:
        h = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
        }
        prefer_parts = [f"odata.maxpagesize={self.page_size}"]
        if prefer_track_changes:
            prefer_parts.append("odata.track-changes")
        h["Prefer"] = ", ".join(prefer_parts)
        return h

    async def fetch_all(
        self,
        token: str,
        plural_name: str,
        select_columns: Optional[List[str]],
        filter_expression: Optional[str],
        delta_token: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Fetches all pages for an entity.

        If delta_token is set → incremental (Change Tracking) request.
        If delta_token is None → full extract (also initialises Change Tracking).

        Returns (records, new_delta_link).
        Deleted records are included with all fields null except the primary key,
        and a synthetic _operation='delete' added by this method.
        """
        if delta_token:
            url = delta_token  # The delta token IS the next delta link URL
            prefer_track = False
        else:
            url = self._entity_url(plural_name)
            prefer_track = True
            if select_columns:
                url += f"?$select={','.join(select_columns)}"
            if filter_expression:
                sep = "&" if "?" in url else "?"
                url += sep + urlencode({"$filter": filter_expression})

        all_records: List[Dict[str, Any]] = []
        final_delta_link: Optional[str] = None

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while url:
                headers = self._headers(token, prefer_track_changes=prefer_track)
                prefer_track = False  # only first request needs track-changes

                resp = await client.get(url, headers=headers)
                self._raise_for_status(resp)

                data = resp.json()
                records = data.get("value", [])

                for rec in records:
                    if "@removed" in rec or rec.get("@odata.context", "").endswith("$deletedEntity"):
                        rec["_operation"] = "delete"
                    else:
                        rec["_operation"] = "insert"
                    all_records.append(rec)

                final_delta_link = data.get("@odata.deltaLink")
                url = data.get("@odata.nextLink")

        log.debug(
            "Dataverse fetch complete: entity=%s records=%d delta_link=%s",
            plural_name, len(all_records), bool(final_delta_link)
        )
        return all_records, final_delta_link

    def _raise_for_status(self, resp: httpx.Response) -> None:
        if resp.status_code == 200:
            return
        if resp.status_code == 401:
            raise AuthenticationError(f"Dataverse 401: token rejected ({resp.text[:200]})")
        if resp.status_code == 403:
            raise EntityExtractionError(
                f"Dataverse 403: insufficient permissions ({resp.text[:200]})"
            )
        if resp.status_code == 404:
            raise EntityExtractionError(
                f"Dataverse 404: entity not found ({resp.url})"
            )
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 60))
            raise ThrottlingError(
                f"Dataverse 429: throttled (Retry-After={retry_after}s)",
                retry_after_seconds=retry_after,
            )
        if resp.status_code >= 500:
            raise TransientError(f"Dataverse {resp.status_code}: {resp.text[:200]}")
        raise EntityExtractionError(
            f"Dataverse {resp.status_code}: {resp.text[:200]}"
        )
