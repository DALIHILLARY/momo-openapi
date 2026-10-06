import json
from dataclasses import replace
from decimal import Decimal

import pytest

from conftest import add_token
from momo_openapi import LEGACY_PLATFORM_URL, NEW_PLATFORM_URL, Collection, ConfigurationError, MomoAPIError

REQUEST_TO_PAY_URL = f"{NEW_PLATFORM_URL}/collection/v1_0/requesttopay"


def test_request_to_pay(config, mocked):
    add_token(mocked, "collection")
    mocked.post(REQUEST_TO_PAY_URL, status=202)

    reference = Collection(config).request_to_pay(
        Decimal("1500"), "256772123456", "order-42", payer_message="Order 42", payee_note="Thanks"
    )

    request = mocked.calls[1].request
    assert json.loads(request.body) == {
        "amount": "1500",
        "currency": "UGX",
        "externalId": "order-42",
        "payer": {"partyIdType": "MSISDN", "partyId": "256772123456"},
        "payerMessage": "Order 42",
        "payeeNote": "Thanks",
    }
    assert request.headers["X-Reference-Id"] == reference
    assert request.headers["X-Callback-Url"] == "https://example.com/momo/callback"
    assert request.headers["X-Target-Environment"] == "mtnuganda"
    assert request.headers["Ocp-Apim-Subscription-Key"] == "sub-key"
    assert request.headers["Authorization"] == "Bearer access-token"


def test_request_to_pay_with_own_reference_and_no_callback(config, mocked):
    add_token(mocked, "collection")
    mocked.post(REQUEST_TO_PAY_URL, status=202)

    client = Collection(replace(config, callback_url=None))
    assert client.request_to_pay(10, "256772123456", "x", reference_id="my-ref") == "my-ref"
    assert "X-Callback-Url" not in mocked.calls[1].request.headers


def test_request_to_pay_requires_currency(config):
    with pytest.raises(ConfigurationError, match="currency"):
        Collection(replace(config, currency=None)).request_to_pay(10, "256772123456", "x")


def test_request_to_pay_error(config, mocked):
    add_token(mocked, "collection")
    mocked.post(REQUEST_TO_PAY_URL, status=409, json={"code": "RESOURCE_ALREADY_EXIST", "message": "Duplicated reference id"})

    with pytest.raises(MomoAPIError) as excinfo:
        Collection(config).request_to_pay(10, "256772123456", "x")
    assert excinfo.value.status_code == 409
    assert excinfo.value.code == "RESOURCE_ALREADY_EXIST"


def test_get_transaction_status(config, mocked):
    add_token(mocked, "collection")
    mocked.get(f"{REQUEST_TO_PAY_URL}/ref-1", json={"status": "SUCCESSFUL", "financialTransactionId": "123"})

    assert Collection(config).get_transaction_status("ref-1")["status"] == "SUCCESSFUL"


def test_get_balance(config, mocked):
    add_token(mocked, "collection")
    mocked.get(f"{NEW_PLATFORM_URL}/collection/v1_0/account/balance", json={"availableBalance": "10", "currency": "UGX"})

    assert Collection(config).get_balance() == {"availableBalance": "10", "currency": "UGX"}


def test_legacy_platform_client(config, mocked):
    add_token(mocked, "collection", base_url=LEGACY_PLATFORM_URL)
    mocked.get(f"{LEGACY_PLATFORM_URL}/collection/v1_0/requesttopay/ref-1", json={"status": "PENDING"})

    client = Collection(replace(config, base_url=LEGACY_PLATFORM_URL))
    assert client.base_url == LEGACY_PLATFORM_URL
    assert client.get_transaction_status("ref-1") == {"status": "PENDING"}
