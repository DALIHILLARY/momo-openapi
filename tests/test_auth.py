import base64
from dataclasses import replace

import pytest

from conftest import add_token
from momo_openapi import NEW_PLATFORM_URL, AuthenticationError, Collection, MomoAPIError


def test_token_request_uses_system_credentials_and_target_environment(config, mocked):
    add_token(mocked, "collection")
    assert Collection(config).get_access_token() == "access-token"

    headers = mocked.calls[0].request.headers
    assert mocked.calls[0].request.url == f"{NEW_PLATFORM_URL}/collection/token/"
    assert headers["Authorization"] == "Basic " + base64.b64encode(b"user-id:cred-token").decode()
    assert headers["Ocp-Apim-Subscription-Key"] == "sub-key"
    assert headers["X-Target-Environment"] == "mtnuganda"


def test_requests_default_user_agent_is_never_sent(config, mocked):
    # momoapi.momo.africa's gateway returns 403 for any User-Agent containing "python-requests".
    add_token(mocked, "collection")
    mocked.get(f"{NEW_PLATFORM_URL}/collection/v1_0/account/balance", json={})
    Collection(config).get_balance()

    for call in mocked.calls:
        assert call.request.headers["User-Agent"].startswith("momo-openapi/")
        assert "python-requests" not in call.request.headers["User-Agent"]


def test_token_is_cached(config, mocked):
    add_token(mocked, "collection")
    client = Collection(config)
    client.get_access_token()
    client.get_access_token()
    assert len(mocked.calls) == 1


def test_token_refreshes_when_close_to_expiry(config, mocked):
    add_token(mocked, "collection", expires_in=30)
    client = Collection(config)
    client.get_access_token()
    client.get_access_token()
    assert len(mocked.calls) == 2


def test_force_refresh(config, mocked):
    add_token(mocked, "collection")
    client = Collection(config)
    client.get_access_token()
    client.get_access_token(force_refresh=True)
    assert len(mocked.calls) == 2


def test_rejected_credentials_raise_authentication_error(config, mocked):
    mocked.post(f"{NEW_PLATFORM_URL}/collection/token/", status=401, json={"error": "invalid_client"})
    with pytest.raises(AuthenticationError) as excinfo:
        Collection(config).get_access_token()
    assert excinfo.value.status_code == 401
    assert excinfo.value.code == "invalid_client"


def test_missing_target_environment_is_not_an_authentication_error(config, mocked):
    # What momoapi.momo.africa answers when X-Target-Environment is missing or wrong.
    body = {"error": "Invalid or missing X-Target-Environment header"}
    mocked.post(f"{NEW_PLATFORM_URL}/collection/token/", status=400, json=body)
    with pytest.raises(MomoAPIError) as excinfo:
        Collection(config).get_access_token()
    assert not isinstance(excinfo.value, AuthenticationError)
    assert excinfo.value.status_code == 400


def test_gateway_html_error_is_summarized(config, mocked):
    page = "<html><head><title>504 Gateway Time-out</title></head><body>...</body></html>"
    mocked.post(f"{NEW_PLATFORM_URL}/collection/token/", status=504, body=page)
    with pytest.raises(MomoAPIError) as excinfo:
        Collection(config).get_access_token()
    assert not isinstance(excinfo.value, AuthenticationError)
    assert str(excinfo.value).endswith("returned HTTP 504: 504 Gateway Time-out")
    assert excinfo.value.body == page


def test_credentials_are_sent_raw_not_url_encoded(config, mocked):
    # The new platform answers 500 when the Basic credentials are URL-encoded
    # (as the basicauth package does), and its User IDs end in "=".
    add_token(mocked, "collection")
    raw = replace(config, user_id="LSMtIy0jMTc4NzY2NjEzNDA0Ng==", credential_token="!qVD9b+K/(,*=@")
    Collection(raw).get_access_token()

    sent = base64.b64decode(mocked.calls[0].request.headers["Authorization"].split(" ", 1)[1]).decode()
    assert sent == "LSMtIy0jMTc4NzY2NjEzNDA0Ng==:!qVD9b+K/(,*=@"
