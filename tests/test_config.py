import pytest

from momo_openapi import LEGACY_PLATFORM_URL, NEW_PLATFORM_URL, SANDBOX_URL, ConfigurationError, MomoConfig

BASE_ENV = {
    "COLLECTION_PRIMARY_KEY": "sub-key",
    "COLLECTION_USER_ID": "user-id",
    "COLLECTION_CREDENTIAL_TOKEN": "cred-token",
    "MTN_ENVIRONMENT": "mtnzambia",
}


def test_production_defaults_to_new_platform(config):
    assert config.base_url == NEW_PLATFORM_URL


def test_sandbox_defaults_to_sandbox_url():
    config = MomoConfig("key", "user", "token", "sandbox")
    assert config.base_url == SANDBOX_URL
    assert config.is_sandbox


def test_explicit_base_url_wins_and_loses_trailing_slash():
    config = MomoConfig("key", "user", "token", "mtnuganda", base_url=LEGACY_PLATFORM_URL + "/")
    assert config.base_url == LEGACY_PLATFORM_URL


def test_missing_required_settings():
    with pytest.raises(ConfigurationError, match="user_id, credential_token"):
        MomoConfig("key", "", "", "mtnuganda")


def test_repr_hides_secrets(config):
    text = repr(config)
    assert "cred-token" not in text
    assert "sub-key" not in text


def test_from_env():
    config = MomoConfig.from_env(
        "collection",
        {**BASE_ENV, "CALLBACK_URL": "https://cb", "CURRENCY": "ZMW", "QUOTAGUARDSTATIC_URL": "http://proxy"},
    )
    assert config.subscription_key == "sub-key"
    assert config.user_id == "user-id"
    assert config.credential_token == "cred-token"
    assert config.target_environment == "mtnzambia"
    assert config.base_url == NEW_PLATFORM_URL
    assert config.callback_url == "https://cb"
    assert config.currency == "ZMW"
    assert config.proxies == {"http": "http://proxy", "https": "http://proxy"}


def test_from_env_accepts_legacy_api_secret_name():
    env = {k: v for k, v in BASE_ENV.items() if k != "COLLECTION_CREDENTIAL_TOKEN"}
    env["COLLECTION_API_SECRET"] = "old-name"
    assert MomoConfig.from_env("collection", env).credential_token == "old-name"


def test_from_env_prefers_credential_token_over_api_secret():
    env = {**BASE_ENV, "COLLECTION_API_SECRET": "old-name"}
    assert MomoConfig.from_env("collection", env).credential_token == "cred-token"


def test_from_env_shared_wallet_credentials():
    env = {
        "DISBURSEMENT_PRIMARY_KEY": "disb-key",
        "MOMO_USER_ID": "shared-user",
        "MOMO_CREDENTIAL_TOKEN": "shared-token",
        "MTN_ENVIRONMENT": "mtnzambia",
    }
    config = MomoConfig.from_env("disbursement", env)
    assert (config.user_id, config.credential_token) == ("shared-user", "shared-token")


def test_from_env_reports_missing_variables():
    with pytest.raises(ConfigurationError) as excinfo:
        MomoConfig.from_env("remittance", {"MTN_ENVIRONMENT": "sandbox"})
    message = str(excinfo.value)
    assert "REMITTANCE_PRIMARY_KEY" in message
    assert "REMITTANCE_USER_ID or MOMO_USER_ID" in message


SIDE_BY_SIDE_ENV = {
    "COLLECTION_PRIMARY_KEY": "sub-key",
    "MTN_ENVIRONMENT": "mtnuganda",
    "BASE_URL": NEW_PLATFORM_URL,
    "COLLECTION_USER_ID": "old-api-user",
    "COLLECTION_API_SECRET": "old-api-key",
    "COLLECTION_NEW_USER_ID": "new-user-id",
    "COLLECTION_NEW_CREDENTIAL_TOKEN": "new-token",
}


def test_from_env_legacy_platform_uses_old_api_user_and_key():
    config = MomoConfig.from_env("collection", SIDE_BY_SIDE_ENV, platform="legacy")
    assert config.base_url == LEGACY_PLATFORM_URL  # BASE_URL is ignored once a platform is given
    assert (config.user_id, config.credential_token) == ("old-api-user", "old-api-key")


def test_from_env_new_platform_uses_new_credentials():
    config = MomoConfig.from_env("collection", SIDE_BY_SIDE_ENV, platform="new")
    assert config.base_url == NEW_PLATFORM_URL
    assert (config.user_id, config.credential_token) == ("new-user-id", "new-token")


def test_from_env_new_platform_after_cutover_names():
    env = {**BASE_ENV, "COLLECTION_API_SECRET": "old-api-key"}
    config = MomoConfig.from_env("collection", env, platform="new")
    assert (config.user_id, config.credential_token) == ("user-id", "cred-token")


def test_from_env_new_platform_never_falls_back_to_the_old_api_key():
    env = {k: v for k, v in SIDE_BY_SIDE_ENV.items() if not k.startswith("COLLECTION_NEW_")}
    with pytest.raises(ConfigurationError) as excinfo:
        MomoConfig.from_env("collection", env, platform="new")
    assert "COLLECTION_NEW_USER_ID and COLLECTION_NEW_CREDENTIAL_TOKEN" in str(excinfo.value)


def test_from_env_rejects_unknown_platform():
    with pytest.raises(ConfigurationError, match="Unknown platform"):
        MomoConfig.from_env("collection", SIDE_BY_SIDE_ENV, platform="sandbox")


def test_from_env_rejects_unknown_product():
    with pytest.raises(ConfigurationError, match="Unknown product"):
        MomoConfig.from_env("payments", BASE_ENV)
