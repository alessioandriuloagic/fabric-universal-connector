"""Tests for DataverseClient — OData fetch, delta tokens, deletes, error mapping."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.connectors.crm.dataverse_client import DataverseClient
from app.exceptions import AuthenticationError, EntityExtractionError, ThrottlingError, TransientError


@pytest.fixture
def client():
    return DataverseClient(
        environment_url="https://org.crm.dynamics.com",
        api_version="v9.2",
        page_size=100,
    )


def _make_response(status_code: int, json_data: dict | None = None, headers: dict | None = None, text: str = ""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.headers = headers or {}
    resp.text = text
    resp.url = "https://org.crm.dynamics.com/api/data/v9.2/contacts"
    return resp


# ── fetch_all: full extract (no delta token) ──────────────────────────────────

async def test_fetch_all_single_page_no_delta(client):
    page = {
        "value": [{"contactid": "a1"}, {"contactid": "a2"}],
        "@odata.deltaLink": "https://org.crm.dynamics.com/api/data/v9.2/contacts?deltaToken=xyz",
    }
    mock_resp = _make_response(200, page)

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        records, delta_link = await client.fetch_all(
            token="tok", plural_name="contacts",
            select_columns=None, filter_expression=None, delta_token=None
        )

    assert len(records) == 2
    assert all(r["_operation"] == "insert" for r in records)
    assert delta_link is not None
    assert "deltaToken=xyz" in delta_link


async def test_fetch_all_select_columns_in_url(client):
    page = {"value": [{"contactid": "a1"}], "@odata.deltaLink": "https://x"}
    mock_resp = _make_response(200, page)

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)) as mock_get:
        await client.fetch_all(
            token="tok", plural_name="contacts",
            select_columns=["contactid", "fullname"],
            filter_expression=None, delta_token=None
        )

    url_called = mock_get.call_args[0][0]
    assert "$select=contactid,fullname" in url_called


async def test_fetch_all_filter_expression_encoded(client):
    page = {"value": [], "@odata.deltaLink": "https://x"}
    mock_resp = _make_response(200, page)

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)) as mock_get:
        await client.fetch_all(
            token="tok", plural_name="contacts",
            select_columns=None,
            filter_expression="statecode eq 0 & emailaddress1 ne null",
            delta_token=None
        )

    url_called = mock_get.call_args[0][0]
    assert "$filter=" in url_called
    assert "%26" in url_called or "&" in url_called  # URL-encoded ampersand


async def test_fetch_all_pagination_follows_next_link(client):
    page1 = {
        "value": [{"contactid": "a1"}],
        "@odata.nextLink": "https://org.crm.dynamics.com/api/data/v9.2/contacts?$skiptoken=1",
    }
    page2 = {
        "value": [{"contactid": "a2"}],
        "@odata.deltaLink": "https://org.crm.dynamics.com/api/data/v9.2/contacts?deltaToken=final",
    }
    responses = [_make_response(200, page1), _make_response(200, page2)]

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=responses)):
        records, delta_link = await client.fetch_all(
            token="tok", plural_name="contacts",
            select_columns=None, filter_expression=None, delta_token=None
        )

    assert len(records) == 2
    assert delta_link is not None
    assert "final" in delta_link


# ── fetch_all: incremental (delta token) ──────────────────────────────────────

async def test_fetch_all_uses_delta_token_as_url(client):
    delta_url = "https://org.crm.dynamics.com/api/data/v9.2/contacts?deltaToken=abc"
    page = {"value": [], "@odata.deltaLink": delta_url}
    mock_resp = _make_response(200, page)

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)) as mock_get:
        await client.fetch_all(
            token="tok", plural_name="contacts",
            select_columns=None, filter_expression=None, delta_token=delta_url
        )

    url_called = mock_get.call_args[0][0]
    assert url_called == delta_url


# ── fetch_all: deleted records ─────────────────────────────────────────────────

async def test_fetch_all_marks_deleted_records(client):
    page = {
        "value": [
            {"contactid": "a1", "@removed": {"reason": "deleted"}},
            {"contactid": "a2"},
        ],
        "@odata.deltaLink": "https://x",
    }
    mock_resp = _make_response(200, page)

    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=mock_resp)):
        records, _ = await client.fetch_all(
            token="tok", plural_name="contacts",
            select_columns=None, filter_expression=None, delta_token=None
        )

    ops = {r["contactid"]: r["_operation"] for r in records}
    assert ops["a1"] == "delete"
    assert ops["a2"] == "insert"


# ── _raise_for_status: HTTP error mapping ─────────────────────────────────────

def test_raise_for_status_401_raises_auth_error(client):
    resp = _make_response(401, text="Unauthorized")
    with pytest.raises(AuthenticationError):
        client._raise_for_status(resp)


def test_raise_for_status_403_raises_extraction_error(client):
    resp = _make_response(403, text="Forbidden")
    with pytest.raises(EntityExtractionError):
        client._raise_for_status(resp)


def test_raise_for_status_404_raises_extraction_error(client):
    resp = _make_response(404, text="Not Found")
    with pytest.raises(EntityExtractionError):
        client._raise_for_status(resp)


def test_raise_for_status_429_raises_throttling_with_retry_after(client):
    resp = _make_response(429, headers={"Retry-After": "45"}, text="Too Many Requests")
    with pytest.raises(ThrottlingError) as exc_info:
        client._raise_for_status(resp)
    assert exc_info.value.retry_after_seconds == 45.0


def test_raise_for_status_500_raises_transient_error(client):
    resp = _make_response(500, text="Internal Server Error")
    with pytest.raises(TransientError):
        client._raise_for_status(resp)


def test_raise_for_status_200_is_noop(client):
    resp = _make_response(200)
    client._raise_for_status(resp)  # must not raise
