"""Live check: collect money and confirm it arrived, on the legacy and the new platform.

This sends real request-to-pay prompts to a phone, so it only runs when
MOMO_LIVE_TESTS=1. Each platform runs when its credentials are set, either in
the environment or in the project's .env (copy .env.example):

    # shared by both platforms (subscription keys do not change in the migration)
    COLLECTION_PRIMARY_KEY=...  MTN_ENVIRONMENT=mtnuganda  CURRENCY=UGX

    # legacy, https://proxy.momoapi.mtn.com: the old setup's API user and API key
    COLLECTION_USER_ID=...  COLLECTION_API_SECRET=...

    # new, https://momoapi.momo.africa: System Credentials from the Partner Portal
    COLLECTION_NEW_USER_ID=...  COLLECTION_NEW_CREDENTIAL_TOKEN=...

    MOMO_LIVE_TESTS=1 .venv/bin/pytest -m live -s              # both platforms
    MOMO_LIVE_TESTS=1 .venv/bin/pytest -m live -s -k legacy    # only one

Approve each prompt on the phone with your PIN before MOMO_TEST_TIMEOUT runs out.
MOMO_TEST_PHONE, MOMO_TEST_COUNTRY_CODE and MOMO_TEST_AMOUNT override the defaults below.
"""

import os
import time
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv

from momo_openapi import Collection, ConfigurationError, MomoConfig

# Real environment variables win over .env, so MOMO_LIVE_TESTS=1 on the command line still decides.
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

PHONE_NUMBER = os.environ.get("MOMO_TEST_PHONE", "0760087659")
COUNTRY_CODE = os.environ.get("MOMO_TEST_COUNTRY_CODE", "256")
AMOUNT = os.environ.get("MOMO_TEST_AMOUNT", "500")
TIMEOUT = float(os.environ.get("MOMO_TEST_TIMEOUT", "120"))
POLL_INTERVAL = 5

pytestmark = pytest.mark.live


def platform_param(name):
    if os.environ.get("MOMO_LIVE_TESTS") != "1":
        skip = pytest.mark.skip(reason="set MOMO_LIVE_TESTS=1 to send a real payment prompt")
    else:
        try:
            MomoConfig.from_env("collection", platform=name)
            problem = None if os.environ.get("CURRENCY") else "CURRENCY is not set"
        except ConfigurationError as exc:
            problem = str(exc)
        skip = pytest.mark.skipif(bool(problem), reason=f"{name}: {problem}")
    return pytest.param(name, id=name, marks=skip)


@pytest.mark.parametrize("platform", [platform_param("legacy"), platform_param("new")])
def test_collect_and_confirm(platform):
    client = Collection.from_env(platform=platform)
    msisdn = to_msisdn(PHONE_NUMBER, COUNTRY_CODE)
    currency = client.config.currency
    external_id = f"live-{platform}-{uuid4().hex[:12]}"

    reference = client.request_to_pay(
        AMOUNT, msisdn, external_id, payer_message="momo-openapi live test", payee_note=f"{platform} platform check"
    )
    print(f"\n[{platform}] Requested {AMOUNT} {currency} from {msisdn} on {client.base_url}")
    print(f"[{platform}] Reference {reference}. Approve the prompt on the phone within {TIMEOUT:.0f}s.")

    # Status must be read on the platform that processed the payment, i.e. with the same client.
    status = wait_for_final_status(client, reference)
    print(f"[{platform}] Final status: {status}")

    assert status["status"] == "SUCCESSFUL", f"payment {status['status']}: {status.get('reason')}"
    assert status["financialTransactionId"]
    assert Decimal(status["amount"]) == Decimal(AMOUNT)
    assert status["currency"] == currency
    assert status["externalId"] == external_id
    assert status["payer"]["partyId"] == msisdn


def to_msisdn(number, country_code):
    """Turn a local number like 0772123456 into the international form MoMo expects (256772123456)."""
    digits = number.replace(" ", "").lstrip("+")
    return country_code + digits[1:] if digits.startswith("0") else digits


def wait_for_final_status(client, reference):
    deadline = time.monotonic() + TIMEOUT
    while True:
        status = client.get_transaction_status(reference)
        if status["status"] != "PENDING":
            return status
        if time.monotonic() >= deadline:
            pytest.fail(f"{reference} still PENDING after {TIMEOUT:.0f}s; approve faster or raise MOMO_TEST_TIMEOUT")
        time.sleep(POLL_INTERVAL)
