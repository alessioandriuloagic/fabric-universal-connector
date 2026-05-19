"""
Business Central REST API v2.0 client (OData v4).

BC uses timestamp watermark (lastModifiedDateTime) — no delta tokens.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx

from app.exceptions import (
    AuthenticationError,
    EntityExtractionError,
    ThrottlingError,
    TransientError,
)

log = logging.getLogger(__name__)

BC_API_BASE = "https://api.businesscentral.dynamics.com/v2.0"


class BusinessCentralClient:
    def __init__(
        self,
        tenant_id: str,
        environment: str,
        company_id: Optional[str] = None,
        api_version: str = "2.0",
        page_size: int = 500,
        http_timeout: float = 120.0,
    ):
        self.base_url = (
            f"{BC_API_BASE}/{tenant_id}/{environment}"
            f"/api/v{api_version}"
        )
        self.company_id = company_id
        self.page_size = page_size
        self.timeout = http_timeout

    def _endpoint_url(self, api_endpoint: str) -> str:
        if self.company_id:
            return f"{self.base_url}/companies({self.company_id})/{api_endpoint}"
        return f"{self.base_url}/{api_endpoint}"

    def _headers(self, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    async def fetch_all(
        self,
        token: str,
        api_endpoint: str,
        select_columns: Optional[List[str]],
        watermark_column: str,
        watermark_value: Optional[str],
        filter_expression: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Fetches all pages for a BC entity.
        Applies watermark filter if set, paginates via @odata.nextLink.
        """
        filters = []
        if watermark_value:
            filters.append(f"{watermark_column} gt {watermark_value}")
        if filter_expression:
            filters.append(filter_expression)

        params: Dict[str, str] = {
            "$top": str(self.page_size),
            "$orderby": f"{watermark_column} asc",
        }
        if filters:
            params["$filter"] = " and ".join(filters)
        if select_columns:
            params["$select"] = ",".join(select_columns)

        url = self._endpoint_url(api_endpoint) + "?" + urlencode(params)
        all_records: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            while url:
                resp = await client.get(url, headers=self._headers(token))
                self._raise_for_status(resp, api_endpoint)
                data = resp.json()
                all_records.extend(data.get("value", []))
                url = data.get("@odata.nextLink")

        log.debug(
            "BC fetch complete: endpoint=%s records=%d watermark=%s",
            api_endpoint, len(all_records), watermark_value
        )
        return all_records

    def _raise_for_status(self, resp: httpx.Response, endpoint: str) -> None:
        if resp.status_code == 200:
            return
        if resp.status_code == 401:
            raise AuthenticationError(f"BC 401: token rejected for {endpoint}")
        if resp.status_code == 403:
            raise EntityExtractionError(
                f"BC 403: insufficient permissions for {endpoint} ({resp.text[:200]})"
            )
        if resp.status_code == 404:
            raise EntityExtractionError(
                f"BC 404: endpoint not found — {endpoint}. "
                "Check environment name and company ID."
            )
        if resp.status_code == 429:
            retry_after = float(resp.headers.get("Retry-After", 60))
            raise ThrottlingError(
                f"BC 429: throttled (Retry-After={retry_after}s)",
                retry_after_seconds=retry_after,
            )
        if resp.status_code >= 500:
            raise TransientError(f"BC {resp.status_code}: {resp.text[:200]}")
        raise EntityExtractionError(
            f"BC {resp.status_code}: {resp.text[:200]}"
        )
