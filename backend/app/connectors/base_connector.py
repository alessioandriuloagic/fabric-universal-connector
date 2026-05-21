"""
Abstract base class for all connector modules.

Key differences from the Spark-based design in ingestion-contracts.md:
  - No SparkSession — all data manipulation is pandas / PyArrow
  - BronzeWriter calls delta-rs via onelake_writer.write_bronze()
  - Watermarks are persisted via onelake_writer.upsert_watermark()
  - Authentication is resolved before the connector is instantiated
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Any

import pandas as pd

from app.exceptions import (
    ConnectorFatalError,
    ThrottlingError,
    TransientError,
    AuthenticationError,
    EntityExtractionError,
)
from app.models.connector_item_definition import (
    ConnectorItemDefinitionBase,
    SchemaEvolutionPolicy,
)

log = logging.getLogger(__name__)


# ── Result types ───────────────────────────────────────────────────────────────

@dataclass
class Watermark:
    watermark_type: str                # "delta_token" | "timestamp" | "rowversion"
    delta_token: Optional[str] = None
    watermark_value: Optional[str] = None
    watermark_column: Optional[str] = None

    def is_initial_load(self) -> bool:
        return self.delta_token is None and self.watermark_value is None

    def to_filter_value(self) -> str:
        if self.watermark_type == "delta_token":
            return self.delta_token or ""
        return self.watermark_value or ""


@dataclass
class EntityResult:
    entity_name: str
    status: str                        # "success" | "failed" | "skipped"
    records_ingested: int = 0
    records_failed: int = 0
    duration_seconds: float = 0.0
    new_watermark: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class RunResult:
    run_id: str
    status: str                        # "success" | "partial_success" | "failed"
    entity_results: List[EntityResult] = field(default_factory=list)
    total_records_ingested: int = 0
    total_entities_failed: int = 0


# ── Retry policy ───────────────────────────────────────────────────────────────

class RetryPolicy:
    def __init__(
        self,
        max_attempts: int = 3,
        initial_backoff: float = 5.0,
        multiplier: float = 2.0,
        max_backoff: float = 300.0,
    ):
        self.max_attempts = max_attempts
        self.initial_backoff = initial_backoff
        self.multiplier = multiplier
        self.max_backoff = max_backoff

    def execute_sync(self, fn, *args, **kwargs) -> Any:
        """Synchronous retry wrapper — blocks the calling thread via time.sleep.

        WARNING: This method is intentionally synchronous and will block the
        event loop if called from async code. Use execute_async() from coroutines.
        Only call this method from a dedicated thread or a synchronous context.
        """
        last_err: Optional[Exception] = None
        for attempt in range(self.max_attempts):
            try:
                return fn(*args, **kwargs)
            except (ThrottlingError, TransientError, AuthenticationError) as exc:
                last_err = exc
                wait = self._wait(exc, attempt)
                log.warning(
                    "Retryable error (attempt %d/%d), sleeping %.1fs: %s",
                    attempt + 1, self.max_attempts, wait, exc
                )
                time.sleep(wait)
            except (ConnectorFatalError, EntityExtractionError):
                raise
        raise ConnectorFatalError(
            f"Max retries ({self.max_attempts}) exhausted: {last_err}",
            "MAX_RETRIES_EXCEEDED",
        )

    async def execute_async(self, coro_fn, *args, **kwargs) -> Any:
        """Async retry wrapper — uses asyncio.sleep so the event loop is never blocked."""
        last_err: Optional[Exception] = None
        for attempt in range(self.max_attempts):
            try:
                return await coro_fn(*args, **kwargs)
            except (ThrottlingError, TransientError, AuthenticationError) as exc:
                last_err = exc
                wait = self._wait(exc, attempt)
                log.warning(
                    "Retryable error (attempt %d/%d), sleeping %.1fs: %s",
                    attempt + 1, self.max_attempts, wait, exc,
                )
                await asyncio.sleep(wait)
            except (ConnectorFatalError, EntityExtractionError):
                raise
        raise ConnectorFatalError(
            f"Max retries ({self.max_attempts}) exhausted: {last_err}",
            "MAX_RETRIES_EXCEEDED",
        )

    def _wait(self, exc: Exception, attempt: int) -> float:
        if isinstance(exc, ThrottlingError) and exc.retry_after_seconds:
            return min(exc.retry_after_seconds, self.max_backoff)
        return min(self.initial_backoff * (self.multiplier ** attempt), self.max_backoff)


# ── Abstract base ──────────────────────────────────────────────────────────────

class BaseConnector(ABC):
    """
    Abstract base connector. Subclasses implement source-specific logic.

    Shared responsibilities handled here:
      - Run orchestration (per-entity loop, error threshold)
      - Retry execution wrapper
      - Bronze write via onelake_writer (delta-rs, no Spark)
      - Watermark persistence via onelake_writer
    """

    BRONZE_SCHEMA: str = ""
    MODULE_TYPE: str = ""

    def __init__(
        self,
        config: ConnectorItemDefinitionBase,
        workspace_id: str,
        lakehouse_id: str,
        connector_id: str,
        bearer_token: str,
        retry_policy: Optional[RetryPolicy] = None,
    ):
        self.config = config
        self.workspace_id = workspace_id
        self.lakehouse_id = lakehouse_id
        self.connector_id = connector_id
        self.bearer_token = bearer_token
        self.retry_policy = retry_policy or RetryPolicy()
        self._run_id: Optional[str] = None
        self._allowed_entity_names: Optional[frozenset[str]] = None

    def set_entity_scope(self, allowed: frozenset[str]) -> None:
        """Restrict ingestion to only the named entities.

        Called by the job executor when the workload is scoped (non-UNIVERSAL).
        Entities whose _entity_name() value is not in *allowed* are skipped.
        """
        self._allowed_entity_names = allowed

    # ── Public entry point ─────────────────────────────────────────────────────

    async def run(self) -> RunResult:
        """
        Main entry point. Orchestrates the full ingestion run.
        """
        self._run_id = str(uuid.uuid4())
        run_start = datetime.now(timezone.utc)

        log.info(
            "Run started: run_id=%s module=%s connector=%s",
            self._run_id, self.MODULE_TYPE, self.connector_id
        )

        auth = None
        try:
            auth = await self._authenticate()
        except Exception as exc:
            raise ConnectorFatalError(
                f"Authentication failed: {exc}", "AUTH_ERROR"
            ) from exc

        entities = self._get_enabled_entities()
        if not entities:
            raise ConnectorFatalError("No entities enabled in config", "CONFIG_VALIDATION_ERROR")

        # Apply workload scope restriction (set by the job executor for scoped workloads).
        if self._allowed_entity_names is not None:
            before = len(entities)
            entities = [e for e in entities if self._entity_name(e) in self._allowed_entity_names]
            skipped = before - len(entities)
            if skipped:
                log.info(
                    "Entity scope applied: %d entities skipped (not in workload scope), %d remaining",
                    skipped,
                    len(entities),
                )
            if not entities:
                raise ConnectorFatalError(
                    "All configured entities are outside the workload scope",
                    "ENTITY_SCOPE_VIOLATION",
                )

        results = await self._process_entities(entities, auth)

        total_ingested = sum(r.records_ingested for r in results)
        total_failed = sum(1 for r in results if r.status == "failed")

        if total_failed == 0:
            status = "success"
        elif total_failed < len(results):
            status = "partial_success"
        else:
            status = "failed"

        run_end = datetime.now(timezone.utc)
        duration = (run_end - run_start).total_seconds()

        log.info(
            "Run finished: run_id=%s status=%s entities=%d/%d records=%d duration=%.1fs",
            self._run_id, status, len(results) - total_failed, len(results),
            total_ingested, duration
        )

        return RunResult(
            run_id=self._run_id,
            status=status,
            entity_results=results,
            total_records_ingested=total_ingested,
            total_entities_failed=total_failed,
        )

    # ── Abstract — must implement per module ───────────────────────────────────

    @abstractmethod
    async def _authenticate(self) -> Any:
        """Authenticate to the source system. Returns an AuthContext."""
        ...

    @abstractmethod
    async def _extract_entity(
        self,
        entity: Any,
        auth: Any,
        watermark: Optional[Watermark],
    ) -> pd.DataFrame:
        """
        Extract records for a single entity.
        Must return a plain DataFrame with only source columns.
        """
        ...

    @abstractmethod
    def _get_new_watermark(
        self,
        entity: Any,
        auth: Any,
        df: pd.DataFrame,
    ) -> Optional[Watermark]:
        """Compute the new watermark after a successful extraction."""
        ...

    @abstractmethod
    def _get_enabled_entities(self) -> List[Any]:
        """Return enabled entity configs from self.config."""
        ...

    @abstractmethod
    def _entity_name(self, entity: Any) -> str:
        """Return the logical name / display name for an entity."""
        ...

    # ── Provided by base ───────────────────────────────────────────────────────

    async def _process_entities(
        self,
        entities: List[Any],
        auth: Any,
    ) -> List[EntityResult]:
        results: List[EntityResult] = []
        failure_count = 0
        threshold = getattr(
            self.config.features, "error_threshold_percent", 50.0
        )

        for entity in entities:
            result = await self._process_single_entity(entity, auth)
            results.append(result)
            if result.status == "failed":
                failure_count += 1
                pct = (failure_count / len(entities)) * 100
                if pct > threshold:
                    raise ConnectorFatalError(
                        f"Error threshold exceeded ({failure_count}/{len(entities)} entities failed)",
                        "ERROR_THRESHOLD_EXCEEDED",
                    )

        return results

    async def _process_single_entity(
        self,
        entity: Any,
        auth: Any,
    ) -> EntityResult:
        from app.services import onelake_writer

        name = self._entity_name(entity)
        start = time.monotonic()

        try:
            watermark = await self._load_watermark(name)
            df = await self.retry_policy.execute_async(
                self._extract_entity, entity, auth, watermark
            )

            rows_written = await onelake_writer.write_bronze(
                df,
                workspace_id=self.workspace_id,
                lakehouse_id=self.lakehouse_id,
                schema=self.BRONZE_SCHEMA,
                table=name,
                run_id=self._run_id,
                connector_id=self.connector_id,
                module_type=self.MODULE_TYPE,
                entity_name=name,
                bearer_token=self.bearer_token,
                schema_evolution_policy=(
                    self.config.features.schema_evolution_handling
                    if self.config.features
                    else SchemaEvolutionPolicy.MERGE
                ),
            )

            new_wm = self._get_new_watermark(entity, auth, df)
            if new_wm is not None:
                await self._save_watermark(name, new_wm, rows_written)

            duration = time.monotonic() - start
            log.info("Entity %s: %d rows in %.1fs", name, rows_written, duration)

            return EntityResult(
                entity_name=name,
                status="success",
                records_ingested=rows_written,
                duration_seconds=duration,
                new_watermark=new_wm.to_filter_value() if new_wm else None,
            )

        except Exception as exc:
            duration = time.monotonic() - start
            log.error("Entity %s failed: %s", name, exc, exc_info=True)
            return EntityResult(
                entity_name=name,
                status="failed",
                duration_seconds=duration,
                error_message=str(exc),
            )

    async def _load_watermark(self, entity_name: str) -> Optional[Watermark]:
        """
        Reads current watermark from _entity_watermarks.
        Returns None if no watermark exists (triggers full extract).
        """
        from app.services import onelake_writer
        from deltalake import DeltaTable
        from deltalake.exceptions import TableNotFoundError
        import pyarrow.compute as pc

        path = onelake_writer._build_abfs_path(
            self.workspace_id, self.lakehouse_id,
            self.BRONZE_SCHEMA, "_meta/_entity_watermarks"
        )
        storage_opts = onelake_writer._get_storage_options(self.bearer_token)

        try:
            dt = DeltaTable(path, storage_options=storage_opts)
            df = dt.to_pandas()
            mask = (df["connector_id"] == self.connector_id) & (df["entity_name"] == entity_name)
            rows = df[mask]
            if rows.empty:
                return None
            row = rows.iloc[0]
            return Watermark(
                watermark_type=row.get("watermark_type", "timestamp"),
                delta_token=row.get("delta_token") or None,
                watermark_value=row.get("watermark_value") or None,
                watermark_column=row.get("watermark_column") or None,
            )
        except TableNotFoundError:
            return None
        except Exception as exc:
            log.warning("Could not load watermark for %s: %s", entity_name, exc)
            return None

    async def _save_watermark(
        self,
        entity_name: str,
        watermark: Watermark,
        records_at_last_run: int,
    ) -> None:
        from app.services import onelake_writer

        await onelake_writer.upsert_watermark(
            workspace_id=self.workspace_id,
            lakehouse_id=self.lakehouse_id,
            schema=self.BRONZE_SCHEMA,
            connector_id=self.connector_id,
            entity_name=entity_name,
            module_type=self.MODULE_TYPE,
            watermark_type=watermark.watermark_type,
            delta_token=watermark.delta_token,
            watermark_value=watermark.watermark_value,
            watermark_column=watermark.watermark_column,
            run_id=self._run_id,
            records_at_last_run=records_at_last_run,
            bearer_token=self.bearer_token,
        )
