import base64
import os
import socket

import pytest

from conftest import add_token
from momo_openapi import LEGACY_PLATFORM_URL, NEW_PLATFORM_URL, check_connectivity
from momo_openapi.cli import main

ENV = {
    "COLLECTION_PRIMARY_KEY": "sub-key",
    "COLLECTION_USER_ID": "user-id",
    "COLLECTION_CREDENTIAL_TOKEN": "cred-token",
    "MTN_ENVIRONMENT": "mtnuganda",
}
MOMO_PREFIXES = ("COLLECTION_", "DISBURSEMENT_", "REMITTANCE_", "MOMO_")
MOMO_VARIABLES = {"BASE_URL", "MTN_ENVIRONMENT", "CALLBACK_URL", "CURRENCY", "QUOTAGUARDSTATIC_URL"}


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """No MoMo settings in the environment, and a working directory without the project's .env."""
    saved = dict(os.environ)
    for name in list(os.environ):
        if name.startswith(MOMO_PREFIXES) or name in MOMO_VARIABLES:
            del os.environ[name]
    monkeypatch.chdir(tmp_path)
    yield tmp_path
    # load_dotenv writes to os.environ directly, so restore everything, not just what monkeypatch touched.
    os.environ.clear()
    os.environ.update(saved)


@pytest.fixture
def env(clean_env):
    os.environ.update(ENV)
    return clean_env


@pytest.fixture
def resolves(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, "", ("203.0.113.7", 443))])


def test_token_command_skips_unconfigured_products(env, mocked, capsys):
    add_token(mocked, "collection")

    assert main(["token"]) == 0

    out = capsys.readouterr().out
    assert "OK    collection: token issued by https://momoapi.momo.africa for mtnuganda" in out
    assert "SKIP  disbursement" in out
    assert "access-token" not in out


def test_token_command_fails_for_explicitly_requested_unconfigured_product(env, capsys):
    assert main(["token", "disbursement"]) == 1
    assert "FAIL  disbursement: Missing environment variables" in capsys.readouterr().out


def test_token_command_reports_rejected_credentials(env, mocked, capsys):
    mocked.post(f"{NEW_PLATFORM_URL}/collection/token/", status=401, json={"error": "login_failed"})
    assert main(["token", "collection"]) == 1
    assert "FAIL  collection" in capsys.readouterr().out


def test_token_command_reads_dotenv_in_working_directory(clean_env, mocked, capsys):
    (clean_env / ".env").write_text("\n".join(f"{k}={v}" for k, v in ENV.items()))
    add_token(mocked, "collection")

    assert main(["token", "collection"]) == 0
    assert "OK    collection" in capsys.readouterr().out


def test_environment_wins_over_dotenv(clean_env, mocked):
    (clean_env / "legacy.env").write_text("\n".join(f"{k}={v}" for k, v in ENV.items()) + "\nBASE_URL=https://ignored.example")
    os.environ["BASE_URL"] = LEGACY_PLATFORM_URL
    add_token(mocked, "collection", base_url=LEGACY_PLATFORM_URL)

    assert main(["--env-file", "legacy.env", "token", "collection"]) == 0


def test_token_command_platform_new_uses_new_credentials(env, mocked, capsys):
    os.environ.update({"BASE_URL": LEGACY_PLATFORM_URL, "COLLECTION_NEW_USER_ID": "new-user", "COLLECTION_NEW_CREDENTIAL_TOKEN": "new-token"})
    add_token(mocked, "collection")

    assert main(["token", "collection", "--platform", "new"]) == 0

    sent = mocked.calls[0].request
    assert sent.url == f"{NEW_PLATFORM_URL}/collection/token/"
    assert sent.headers["Authorization"] == "Basic " + base64.b64encode(b"new-user:new-token").decode()
    assert "OK    collection: token issued by https://momoapi.momo.africa" in capsys.readouterr().out


def test_missing_explicit_env_file(clean_env, capsys):
    with pytest.raises(SystemExit):
        main(["--env-file", "nope.env", "token"])
    assert "env file nope.env not found" in capsys.readouterr().err


def test_check_command(env, mocked, resolves, capsys):
    mocked.get(NEW_PLATFORM_URL, status=404)

    assert main(["check"]) == 0
    assert "OK    https://momoapi.momo.africa is reachable (HTTP 404) via 203.0.113.7" in capsys.readouterr().out


def test_check_connectivity_dns_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr(socket, "getaddrinfo", fail)
    result = check_connectivity("https://unreachable.invalid")
    assert not result.reachable
    assert "DNS lookup failed" in result.error
