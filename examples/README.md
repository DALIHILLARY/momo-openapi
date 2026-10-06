# Examples

One script per platform and operation. The `legacy/` and `new/` versions of a script are identical except for `platform="legacy"` or `platform="new"`, which picks the base URL and that platform's own credentials.

| Operation | Legacy (`proxy.momoapi.mtn.com`) | New (`momoapi.momo.africa`) |
|---|---|---|
| Check credentials | [legacy/check_credentials.py](legacy/check_credentials.py) | [new/check_credentials.py](new/check_credentials.py) |
| Account balance | [legacy/balance.py](legacy/balance.py) | [new/balance.py](new/balance.py) |
| Request a payment | [legacy/collect.py](legacy/collect.py) | [new/collect.py](new/collect.py) |
| Payment status | [legacy/collect_status.py](legacy/collect_status.py) | [new/collect_status.py](new/collect_status.py) |
| Pay out | [legacy/disburse.py](legacy/disburse.py) | [new/disburse.py](new/disburse.py) |
| Payout status | [legacy/disburse_status.py](legacy/disburse_status.py) | [new/disburse_status.py](new/disburse_status.py) |
| Send a remittance | [legacy/remit.py](legacy/remit.py) | [new/remit.py](new/remit.py) |
| Remittance status | [legacy/remit_status.py](legacy/remit_status.py) | [new/remit_status.py](new/remit_status.py) |

## Setup

Copy [.env.example](../.env.example) to `.env` in the repo root and fill in the platform you want. Both can be set at once:

| | Legacy | New |
|---|---|---|
| Credentials | `COLLECTION_USER_ID` + `COLLECTION_API_SECRET` | `COLLECTION_NEW_USER_ID` + `COLLECTION_NEW_CREDENTIAL_TOKEN` |
| Shared | `COLLECTION_PRIMARY_KEY`, `MTN_ENVIRONMENT`, `CURRENCY`, `CALLBACK_URL` | same |

`DISBURSEMENT_*` and `REMITTANCE_*` follow the same pattern. `MOMO_TEST_PHONE` sets the default `--phone`. `BASE_URL` is ignored, because each script pins its platform.

The scripts need `python-dotenv` (`pip install "momo-openapi[dotenv]"`). Run them from the repo root:

```bash
.venv/bin/python examples/new/check_credentials.py
.venv/bin/python examples/legacy/collect.py 500 --phone 256772123456 --ref order-42
.venv/bin/python examples/legacy/collect_status.py <reference>
```

`collect`, `disburse` and `remit` move real money, so use small amounts. Each prints the reference to pass to its `_status` script. Use the status script from the same folder: a transaction's status can only be read on the platform that created it.
