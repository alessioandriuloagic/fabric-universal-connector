import pytest
import token_validator

class DummyMSALApp:
    def acquire_token_for_client(self, scopes):
        return {"access_token": "app-token-xyz", "expires_in": 3600}

    def acquire_token_on_behalf_of(self, user_assertion, scopes):
        return {"access_token": "obo-token-abc", "expires_in": 3600}


def test_acquire_app_token_monkeypatch(monkeypatch):
    # Monkeypatch get_msal_app to return a dummy app
    monkeypatch.setattr(token_validator, 'get_msal_app', lambda: DummyMSALApp())
    res = token_validator.acquire_app_token(["https://api.businesscentral.dynamics.com/.default"])
    assert 'access_token' in res
    assert res['access_token'] == 'app-token-xyz'


def test_acquire_obo_token_monkeypatch(monkeypatch):
    monkeypatch.setattr(token_validator, 'get_msal_app', lambda: DummyMSALApp())
    res = token_validator.acquire_token_on_behalf_of('user-assertion', ["https://graph.microsoft.com/.default"])
    assert 'access_token' in res
    assert res['access_token'] == 'obo-token-abc'
