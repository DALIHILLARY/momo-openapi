import json
import re

import pytest

from momo_openapi import SANDBOX_URL, Collection, MomoAPIError, provision_sandbox_user


def add_provisioning(mocked):
    mocked.post(f"{SANDBOX_URL}/v1_0/apiuser", status=201)
    mocked.post(re.compile(rf"{SANDBOX_URL}/v1_0/apiuser/[0-9a-f-]+/apikey"), status=201, json={"apiKey": "sandbox-key"})


def test_provision_sandbox_user(mocked):
    add_provisioning(mocked)

    user_id, api_key = provision_sandbox_user("sub-key", "example.com")

    create_user, create_key = mocked.calls[0].request, mocked.calls[1].request
    assert create_user.headers["X-Reference-Id"] == user_id
    assert create_user.headers["Ocp-Apim-Subscription-Key"] == "sub-key"
    assert json.loads(create_user.body) == {"providerCallbackHost": "example.com"}
    assert create_key.url == f"{SANDBOX_URL}/v1_0/apiuser/{user_id}/apikey"
    assert "python-requests" not in create_user.headers["User-Agent"]
    assert api_key == "sandbox-key"


def test_provision_sandbox_user_error(mocked):
    mocked.post(f"{SANDBOX_URL}/v1_0/apiuser", status=401, json={"statusCode": 401, "message": "Invalid subscription key"})
    with pytest.raises(MomoAPIError) as excinfo:
        provision_sandbox_user("bad-key")
    assert excinfo.value.status_code == 401


def test_for_sandbox(mocked):
    add_provisioning(mocked)

    client = Collection.for_sandbox("sub-key")

    assert client.base_url == SANDBOX_URL
    assert client.config.target_environment == "sandbox"
    assert client.config.currency == "EUR"
    assert client.config.credential_token == "sandbox-key"
