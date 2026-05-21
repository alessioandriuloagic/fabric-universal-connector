"""Tests for the WDK IJobsController endpoints (start, poll, cancel)."""
import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import auth_headers


# ── /health ────────────────────────────────────────────────────────────────────

def test_health_endpoint(test_client):
    resp = test_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


# ── POST /workload/jobs/instances/{id} ────────────────────────────────────────

def test_start_job_missing_auth_header(test_client):
    resp = test_client.post(
        "/workload/jobs/instances/job-1",
        json={"jobType": "ConnectorIngestionJob", "itemObjectId": "i1", "workspaceObjectId": "w1"},
    )
    assert resp.status_code == 401


def test_start_job_invalid_auth_header(test_client):
    resp = test_client.post(
        "/workload/jobs/instances/job-1",
        json={"jobType": "ConnectorIngestionJob", "itemObjectId": "i1", "workspaceObjectId": "w1"},
        headers={"Authorization": "NotBearer token"},
    )
    assert resp.status_code == 401


def test_start_job_returns_in_progress(test_client):
    with patch("app.api.jobs._execute_job", AsyncMock()):
        resp = test_client.post(
            "/workload/jobs/instances/job-new",
            json={"jobType": "ConnectorIngestionJob", "itemObjectId": "i1", "workspaceObjectId": "w1"},
            headers=auth_headers(),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "InProgress"


def test_start_job_idempotent_in_progress(test_client):
    """Second POST for the same jobInstanceId while InProgress returns InProgress."""
    with patch("app.api.jobs._execute_job", AsyncMock()):
        resp1 = test_client.post(
            "/workload/jobs/instances/job-dup",
            json={"jobType": "ConnectorIngestionJob", "itemObjectId": "i1", "workspaceObjectId": "w1"},
            headers=auth_headers(),
        )
        resp2 = test_client.post(
            "/workload/jobs/instances/job-dup",
            json={"jobType": "ConnectorIngestionJob", "itemObjectId": "i1", "workspaceObjectId": "w1"},
            headers=auth_headers(),
        )
    assert resp1.json()["status"] == "InProgress"
    assert resp2.json()["status"] == "InProgress"


# ── GET /workload/jobs/instances/{id} ─────────────────────────────────────────

def test_get_job_not_found(test_client):
    resp = test_client.get(
        "/workload/jobs/instances/nonexistent-job",
        headers=auth_headers(),
    )
    assert resp.status_code == 404


def test_get_job_after_start(test_client):
    with patch("app.api.jobs._execute_job", AsyncMock()):
        test_client.post(
            "/workload/jobs/instances/job-poll",
            json={"jobType": "ConnectorIngestionJob", "itemObjectId": "i1", "workspaceObjectId": "w1"},
            headers=auth_headers(),
        )
    resp = test_client.get("/workload/jobs/instances/job-poll", headers=auth_headers())
    assert resp.status_code == 200
    assert resp.json()["status"] == "InProgress"


# ── DELETE + POST /cancel ─────────────────────────────────────────────────────

def test_cancel_nonexistent_job(test_client):
    resp = test_client.post(
        "/workload/jobs/instances/ghost/cancel",
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["cancelled"] is False


def test_cancel_existing_job(test_client):
    with patch("app.api.jobs._execute_job", AsyncMock()):
        test_client.post(
            "/workload/jobs/instances/job-cancel",
            json={"jobType": "ConnectorIngestionJob", "itemObjectId": "i1", "workspaceObjectId": "w1"},
            headers=auth_headers(),
        )
    resp = test_client.post(
        "/workload/jobs/instances/job-cancel/cancel",
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["cancelled"] is True


def test_delete_existing_job(test_client):
    with patch("app.api.jobs._execute_job", AsyncMock()):
        test_client.post(
            "/workload/jobs/instances/job-delete",
            json={"jobType": "ConnectorIngestionJob", "itemObjectId": "i1", "workspaceObjectId": "w1"},
            headers=auth_headers(),
        )
    resp = test_client.delete(
        "/workload/jobs/instances/job-delete",
        headers=auth_headers(),
    )
    assert resp.status_code == 200
    assert resp.json()["cancelled"] is True


# ── get_or_create atomicity ───────────────────────────────────────────────────

async def test_get_or_create_returns_existing():
    from app.services import job_tracker
    from app.models.job_models import JobRecord, JobStatus

    record = JobRecord(
        job_instance_id="j1",
        item_object_id="i1",
        workspace_object_id="w1",
        job_type="ConnectorIngestionJob",
        status=JobStatus.IN_PROGRESS,
    )
    await job_tracker.create("j1", record)

    existing, created = await job_tracker.get_or_create("j1", record)
    assert not created
    assert existing.job_instance_id == "j1"


async def test_get_or_create_creates_new():
    from app.services import job_tracker
    from app.models.job_models import JobRecord, JobStatus

    record = JobRecord(
        job_instance_id="j-new",
        item_object_id="i1",
        workspace_object_id="w1",
        job_type="ConnectorIngestionJob",
        status=JobStatus.IN_PROGRESS,
    )
    result, created = await job_tracker.get_or_create("j-new", record)
    assert created


# ── Entity scope enforcement (S1-1) ──────────────────────────────────────────

class _ConcreteConnector:
    """Minimal connector stub that satisfies the set_entity_scope interface."""

    def __init__(self, entities):
        self._entities = entities
        self._allowed_entity_names = None

    def set_entity_scope(self, allowed: frozenset) -> None:
        self._allowed_entity_names = allowed

    def get_effective_entities(self):
        if self._allowed_entity_names is None:
            return list(self._entities)
        return [e for e in self._entities if e in self._allowed_entity_names]


def test_entity_scope_filters_out_of_scope_entities():
    """Entities not in the workload scope are excluded after set_entity_scope."""
    all_entities = ["contact", "lead", "account", "msdynmkt_journey"]
    connector = _ConcreteConnector(all_entities)

    from app.workload_config.customer_insight_journey import ALLOWED_ENTITY_NAMES
    connector.set_entity_scope(ALLOWED_ENTITY_NAMES)

    effective = connector.get_effective_entities()
    assert "contact" in effective
    assert "msdynmkt_journey" in effective
    # lead and account belong to Sales CRM, not Customer Insight Journey
    assert "lead" not in effective
    assert "account" not in effective


def test_entity_scope_not_applied_for_universal():
    """UNIVERSAL workload leaves all entities intact (no scope restriction)."""
    from app.api.jobs import _get_entity_scope
    from app.api.workloads import WorkloadId

    scope = _get_entity_scope(WorkloadId.UNIVERSAL)
    assert scope is None


def test_entity_scope_not_applied_for_sql_db():
    """SQL_DB workload has user-defined tables so no scope restriction is applied."""
    from app.api.jobs import _get_entity_scope
    from app.api.workloads import WorkloadId

    scope = _get_entity_scope(WorkloadId.SQL_DB)
    assert scope is None


def test_entity_scope_cij_contains_expected_entities():
    """Customer Insight Journey scope contains exactly the 3 expected entities."""
    from app.api.jobs import _get_entity_scope
    from app.api.workloads import WorkloadId

    scope = _get_entity_scope(WorkloadId.CUSTOMER_INSIGHT_JOURNEY)
    assert scope is not None
    assert scope == frozenset({"contact", "msdynmkt_email", "msdynmkt_journey"})


def test_entity_scope_sales_crm_contains_expected_entities():
    """Sales CRM scope contains the 7 configured entities."""
    from app.api.jobs import _get_entity_scope
    from app.api.workloads import WorkloadId

    scope = _get_entity_scope(WorkloadId.SALES_CRM)
    assert scope is not None
    assert "lead" in scope
    assert "opportunity" in scope
    assert "account" in scope
    assert "contact" in scope
    assert "quote" in scope
    assert "salesorder" in scope
    assert "invoice" in scope
    assert len(scope) == 7


def test_set_entity_scope_all_entities_out_of_scope():
    """If every entity is out of scope, connector has zero effective entities."""
    connector = _ConcreteConnector(["msdynmkt_journey", "contact"])
    # Apply a scope that matches nothing
    connector.set_entity_scope(frozenset({"lead", "account"}))
    effective = connector.get_effective_entities()
    assert effective == []
