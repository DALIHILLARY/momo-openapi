import json

import pytest

from conftest import add_token
from momo_openapi import NEW_PLATFORM_URL, Disbursement, Remittance


@pytest.fixture(params=[Disbursement, Remittance], ids=["disbursement", "remittance"])
def client_class(request):
    return request.param


def test_transfer(config, mocked, client_class):
    product = client_class.product
    add_token(mocked, product)
    mocked.post(f"{NEW_PLATFORM_URL}/{product}/v1_0/transfer", status=202)

    reference = client_class(config).transfer(250, "256772123456", 99, payer_message="Payout", payee_note="Ref 99")

    request = mocked.calls[1].request
    assert json.loads(request.body) == {
        "amount": "250",
        "currency": "UGX",
        "externalId": "99",
        "payee": {"partyIdType": "MSISDN", "partyId": "256772123456"},
        "payerMessage": "Payout",
        "payeeNote": "Ref 99",
    }
    assert request.headers["X-Reference-Id"] == reference
    assert request.headers["X-Target-Environment"] == "mtnuganda"
    assert mocked.calls[0].request.url == f"{NEW_PLATFORM_URL}/{product}/token/"


def test_get_transaction_status(config, mocked, client_class):
    product = client_class.product
    add_token(mocked, product)
    mocked.get(f"{NEW_PLATFORM_URL}/{product}/v1_0/transfer/ref-1", json={"status": "FAILED", "reason": "PAYEE_NOT_FOUND"})

    assert client_class(config).get_transaction_status("ref-1")["reason"] == "PAYEE_NOT_FOUND"


def test_get_balance(config, mocked, client_class):
    product = client_class.product
    add_token(mocked, product)
    mocked.get(f"{NEW_PLATFORM_URL}/{product}/v1_0/account/balance", json={"availableBalance": "5", "currency": "UGX"})

    assert client_class(config).get_balance()["availableBalance"] == "5"
