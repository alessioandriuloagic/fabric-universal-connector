"""Shared fixtures for all test modules."""
import pytest
import app.services.job_tracker as job_tracker


@pytest.fixture(autouse=True)
def clear_job_store():
    """Reset in-memory job store before and after every test."""
    job_tracker._store.clear()
    yield
    job_tracker._store.clear()


@pytest.fixture
def test_client():
    """FastAPI TestClient with JWT validation disabled (env vars not set)."""
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def auth_headers() -> dict:
    return {"Authorization": "Bearer test-token-for-unit-tests"}
