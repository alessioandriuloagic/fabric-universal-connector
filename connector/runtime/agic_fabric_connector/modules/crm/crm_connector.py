from __future__ import annotations

import json
import logging
import urllib.parse
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import requests

from agic_fabric_connector.base.connector_base import BaseConnector
from agic_fabric_connector.base.bronze_writer import BronzeWriter
from agic_fabric_connector.base.exceptions import (
    AuthenticationError,
    EntityExtractionError,
    ThrottlingError,
    TransientError,
)
from agic_fabric_connector.base.retry_policy import with_retry
from agic_fabric_connector.base.run_result import EntityResult, RunResult
from agic_fabric_connector.base.watermark import Watermark, WatermarkStore, WatermarkType
from agic_fabric_connector.modules.crm.entity_catalog import ENTITY_CATALOG_BY_KEY

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

logger = logging.getLogger(__name__)

_DATAVERSE_API_VERSION = "v9.2"


class CRMConnector(BaseConnector):
    def __init__(self, config: object, spark: "SparkSession") -> None:
        super().__init__(config, spark)
        self._access_token: Optional[str] = None
        self._session: Optional[requests.Session] = None

    # ── Authentication ──────────────────────────────────────────────────────

    def authenticate(self) -> None:
        auth = self.config.authentication
        env_url = self.config.source.environment_url.rstrip("/")

        if auth.mode == "service_principal":
            self._auth_service_principal(auth, env_url)
        elif auth.mode == "fabric_connection":
            self._auth_fabric_connection(auth)
        else:
            raise AuthenticationError(f"Unsupported auth mode: {auth.mode}")

        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self._access_token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        logger.info("Authenticated to Dataverse: %s", env_url)

    def _auth_service_principal(self, auth, env_url: str) -> None:
        client_secret = self._resolve_client_secret(auth.secret_ref)
        token_url = (
            f"https://login.microsoftonline.com/{auth.tenant_id}/oauth2/v2.0/token"
        )
        resp = requests.post(
            token_url,
            data={
                "grant_type": "client_credentials",
                "client_id": auth.client_id,
                "client_secret": client_secret,
                "scope": f"{env_url}/.default",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise AuthenticationError(
                f"Token request failed ({resp.status_code}): {resp.text}"
            )
        self._access_token = resp.json()["access_token"]

    def _auth_fabric_connection(self, auth) -> None:
        try:
            from notebookutils import mssparkutils  # type: ignore[import]

            raw = mssparkutils.credentials.getConnectionStringOrCreds(
                auth.fabric_connection_id
            )
            try:
                parsed = json.loads(raw)
                self._access_token = (
                    parsed.get("accessToken")
                    or parsed.get("access_token")
                    or parsed.get("clientSecret")
                    or raw
                )
            except (ValueError, TypeError):
                self._access_token = raw
        except Exception as exc:
            raise AuthenticationError(
                f"Fabric connection auth failed: {exc}"
            ) from exc

    def _resolve_client_secret(self, secret_ref) -> str:
        if secret_ref.mode == "fabric_connection":
            try:
                from notebookutils import mssparkutils  # type: ignore[import]

                raw = mssparkutils.credentials.getConnectionStringOrCreds(
                    secret_ref.fabric_connection_id
                )
                try:
                    parsed = json.loads(raw)
                    return (
                        parsed.get("clientSecret")
                        or parsed.get("password")
                        or raw
                    )
                except (ValueError, TypeError):
                    return raw
            except Exception as exc:
                raise AuthenticationError(
                    f"Failed to resolve Fabric connection secret: {exc}"
                ) from exc

        if secret_ref.mode == "keyvault_reference":
            try:
                from notebookutils import mssparkutils  # type: ignore[import]

                return mssparkutils.credentials.getSecret(
                    secret_ref.key_vault_uri,
                    secret_ref.client_secret_name,
                )
            except Exception as exc:
                raise AuthenticationError(
                    f"Failed to resolve Key Vault secret: {exc}"
                ) from exc

        raise AuthenticationError(
            f"Unknown secret_ref mode: {secret_ref.mode}"
        )

    # ── Entity extraction ───────────────────────────────────────────────────

    def extract_entity(self, entity: dict) -> tuple:  # (list[dict], str | None)
        """Query Dataverse with delta-token incremental pattern.

        Returns (records, new_delta_token).
        """
        watermark_store = WatermarkStore(self.config, self.spark)
        current_wm = watermark_store.get(entity["logical_name"])

        env_url = self.config.source.environment_url.rstrip("/")
        entity_set = entity["entity_set_name"]
        page_size = getattr(self.config.source, "page_size", 5000) or 5000
        select_cols = ",".join(entity.get("select_columns", []))

        if current_wm and current_wm.delta_token:
            # Incremental load using existing delta token
            url = (
                f"{env_url}/api/data/{_DATAVERSE_API_VERSION}/{entity_set}"
                f"?$deltatoken={urllib.parse.quote(current_wm.delta_token)}"
            )
            prefer_header = f"odata.maxpagesize={page_size}"
        else:
            # Initial full load with change tracking enabled
            url = (
                f"{env_url}/api/data/{_DATAVERSE_API_VERSION}/{entity_set}"
                f"?$select={select_cols}&$top={page_size}"
            )
            prefer_header = f"odata.track-changes,odata.maxpagesize={page_size}"

        all_records: list = []
        new_delta_token: Optional[str] = None

        while url:
            headers = {"Prefer": prefer_header}

            def _get(bound_url=url, bound_headers=headers):
                return self._session.get(bound_url, headers=bound_headers, timeout=60)

            resp = with_retry(_get)

            if resp.status_code == 410:
                # Delta token expired — reset watermark and redo full load
                logger.warning(
                    "Delta token expired for %s — falling back to full reload",
                    entity["logical_name"],
                )
                watermark_store.reset(entity["logical_name"])
                return self.extract_entity(entity)

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 60))
                raise ThrottlingError(
                    f"Dataverse throttled request for {entity_set}",
                    retry_after_seconds=retry_after,
                )

            if resp.status_code >= 500:
                raise TransientError(
                    f"Dataverse server error {resp.status_code} for {entity_set}"
                )

            if resp.status_code != 200:
                raise EntityExtractionError(
                    f"Failed to fetch {entity_set}: {resp.status_code} — {resp.text[:500]}"
                )

            data = resp.json()
            records = data.get("value", [])
            all_records.extend(records)

            next_link = data.get("@odata.nextLink")
            delta_link = data.get("@odata.deltaLink")

            if delta_link:
                parsed = urllib.parse.urlparse(delta_link)
                qs = dict(urllib.parse.parse_qsl(parsed.query))
                new_delta_token = qs.get("$deltatoken") or qs.get("deltatoken")
                url = None
            elif next_link:
                url = next_link
                # Prefer header not needed for continuation pages
                prefer_header = f"odata.maxpagesize={page_size}"
            else:
                url = None

        logger.info(
            "Extracted %d records from %s", len(all_records), entity["logical_name"]
        )
        return all_records, new_delta_token

    # ── Orchestration ───────────────────────────────────────────────────────

    def run(self) -> RunResult:
        run_id = str(uuid.uuid4())
        run_result = RunResult(run_id=run_id, status="running")

        self.authenticate()

        writer = BronzeWriter(self.config, self.spark)
        watermark_store = WatermarkStore(self.config, self.spark)

        entities = self._resolve_entities()
        logger.info("Starting run %s — entities: %s", run_id, [e["logical_name"] for e in entities])

        for entity in entities:
            start = datetime.utcnow()
            try:
                records, new_delta_token = self.extract_entity(entity)

                records_ingested = 0
                if records:
                    import pandas as pd  # type: ignore[import]

                    df = pd.DataFrame(records)
                    records_ingested = writer.write(df, entity)

                if new_delta_token:
                    watermark_store.upsert(
                        entity["logical_name"],
                        Watermark(
                            watermark_type=WatermarkType.DELTA_TOKEN,
                            delta_token=new_delta_token,
                            watermark_value=None,
                            watermark_column=None,
                        ),
                    )

                duration = (datetime.utcnow() - start).total_seconds()
                run_result.entity_results.append(
                    EntityResult(
                        entity_name=entity["logical_name"],
                        status="success",
                        records_ingested=records_ingested,
                        records_failed=0,
                        duration_seconds=duration,
                        new_watermark=new_delta_token,
                        error_message=None,
                    )
                )
                logger.info(
                    "Entity %s: %d records ingested in %.1fs",
                    entity["logical_name"],
                    records_ingested,
                    duration,
                )
            except Exception as exc:
                duration = (datetime.utcnow() - start).total_seconds()
                logger.error(
                    "Entity %s failed after %.1fs: %s",
                    entity["logical_name"],
                    duration,
                    exc,
                    exc_info=True,
                )
                run_result.entity_results.append(
                    EntityResult(
                        entity_name=entity["logical_name"],
                        status="failed",
                        records_ingested=0,
                        records_failed=0,
                        duration_seconds=duration,
                        new_watermark=None,
                        error_message=str(exc),
                    )
                )

        succeeded = sum(1 for r in run_result.entity_results if r.status == "success")
        failed = sum(1 for r in run_result.entity_results if r.status == "failed")

        if failed == 0:
            run_result.status = "success"
        elif succeeded > 0:
            run_result.status = "partial_success"
        else:
            run_result.status = "failed"

        logger.info(
            "Run %s complete: %s | %d succeeded, %d failed",
            run_id,
            run_result.status,
            succeeded,
            failed,
        )
        return run_result

    def _resolve_entities(self) -> list:
        """Resolve entity keys/configs from the item definition against the catalog."""
        resolved = []
        for item in self.config.entities:
            if isinstance(item, str):
                key = item
            elif isinstance(item, dict):
                key = item.get("logicalName") or item.get("logical_name", "")
            else:
                key = getattr(item, "logical_name", "") or getattr(item, "logicalName", "")

            if key in ENTITY_CATALOG_BY_KEY:
                catalog_entry = dict(ENTITY_CATALOG_BY_KEY[key])
                # Allow saved select_columns to override catalog defaults
                if isinstance(item, dict):
                    saved_cols = item.get("selectColumns") or item.get("select_columns")
                    if saved_cols:
                        catalog_entry["select_columns"] = saved_cols
                resolved.append(catalog_entry)
            else:
                logger.warning("Unknown entity key '%s' — skipping", key)

        return resolved
