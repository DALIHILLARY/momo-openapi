import pytest
import responses

from momo_openapi import NEW_PLATFORM_URL, MomoConfig


@pytest.fixture
def config():
    return MomoConfig(
        subscription_key="sub-key",
        user_id="user-id",
        credential_token="cred-token",
        target_environment="mtnuganda",
        currency="UGX",
        callback_url="https://example.com/momo/callback",
    )


@pytest.fixture
def mocked():
    with responses.RequestsMock() as rsps:
        yield rsps


def add_token(rsps, product, base_url=NEW_PLATFORM_URL, expires_in=3600):
    return rsps.post(
        f"{base_url}/{product}/token/",
        json={"access_token": "access-token", "token_type": "access_token", "expires_in": expires_in},
    )
