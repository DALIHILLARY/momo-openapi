# momo-openapi

Python client for the MTN MoMo Open API (Collections, Disbursements and Remittances), built for the migration from `proxy.momoapi.mtn.com` to the new platform at `momoapi.momo.africa`.

```bash
pip install momo-openapi
```

Requires Python 3.9+ and `requests`.

## What the migration changes

If your integration reaches MoMo over the internet through `https://proxy.momoapi.mtn.com`, you have to migrate. Integrations over a VPN are not affected.

| | Legacy platform | New platform |
|---|---|---|
| Base URL | `https://proxy.momoapi.mtn.com` (IP `172.205.99.23`) | `https://momoapi.momo.africa` (use the FQDN, not an IP) |
| Credentials | API User + API Key | User ID + Credential Token, from the Partner Portal |
| `X-Target-Environment` on `*/token/` | Optional | **Mandatory** |
| Callback source IPs | `212.88.125.100`, `212.88.100.195` | Shared by MTN on request |

Subscription keys, the `X-Target-Environment` value, request and response bodies, and callbacks passed in `X-Callback-Url` all stay the same.

MTN's documents don't mention these behaviours of the new platform's gateway. They were found by testing it, and this package handles all of them:

- **No `python-requests` User-Agent.** Any `User-Agent` containing `python-requests` (the `requests` library's default) gets an HTML `403 Forbidden` page from "Microsoft-Azure-Application-Gateway". This package sends `User-Agent: momo-openapi/<version>`.
- **Credentials go into the Basic header raw.** New User IDs are base64 strings ending in `=`, and tokens contain punctuation. If they are URL-encoded before base64, as the `basicauth` package's `encode()` does, the gateway answers `500 Internal server error`. Send `base64("<user id>:<token>")` exactly as the portal shows them.
- **A missing or wrong `X-Target-Environment` on `*/token/`** gets `400 {"error": "Invalid or missing X-Target-Environment header"}`.

This package sends `X-Target-Environment` on every token request and defaults to the new base URL. Most migrations therefore only need new credential values and, before cutover, a `BASE_URL` override.

## Quick start

```python
from momo_openapi import Collection, Disbursement

collection = Collection.from_env()

reference = collection.request_to_pay("1500", "256772123456", external_id="order-42",
                                      payer_message="Order 42", payee_note="Thank you")
status = collection.get_transaction_status(reference)
print(status["status"])  # PENDING, SUCCESSFUL or FAILED

disbursement = Disbursement.from_env()
payout = disbursement.transfer("500", "256772123456", external_id="payout-7")
```

`request_to_pay()` and `transfer()` return the `X-Reference-Id` once MoMo accepts the request (HTTP 202). The outcome arrives later, on your callback URL or through `get_transaction_status()`. Pass `reference_id=` to use your own UUID, for example to retry safely.

You can also configure a client in code:

```python
from momo_openapi import Collection, MomoConfig

collection = Collection(MomoConfig(
    subscription_key="...",       # Ocp-Apim-Subscription-Key, unchanged by the migration
    user_id="...",                # Partner Portal User ID
    credential_token="...",       # Partner Portal Credential Token
    target_environment="mtnuganda",
    currency="UGX",
    callback_url="https://example.com/momo/callback",
))
```

Every client also has `get_balance()` and `get_access_token()`. Tokens are cached and renewed a minute before they expire.

## Configuration from the environment

The variable names match the older `mtnmomoapi` integration, so existing deployments only need new values.

| Variable | Meaning |
|---|---|
| `COLLECTION_PRIMARY_KEY` | Subscription key for the product. `DISBURSEMENT_` and `REMITTANCE_` variants work the same way. |
| `COLLECTION_USER_ID` | User ID. Falls back to `MOMO_USER_ID`. |
| `COLLECTION_CREDENTIAL_TOKEN` | Credential Token. Falls back to the old `COLLECTION_API_SECRET`, then `MOMO_CREDENTIAL_TOKEN`. |
| `MTN_ENVIRONMENT` | `X-Target-Environment`, e.g. `mtnuganda`, `mtnzambia` or `sandbox`. Required. |
| `BASE_URL` | Optional. Defaults to `https://momoapi.momo.africa`, or to the sandbox when `MTN_ENVIRONMENT=sandbox`. |
| `CALLBACK_URL` | Optional. Sent as `X-Callback-Url`. |
| `CURRENCY` | Default currency, e.g. `UGX`. The sandbox only accepts `EUR`. |
| `MOMO_PROXY_URL` | Optional outbound proxy for static egress IPs. Falls back to `QUOTAGUARDSTATIC_URL`. |
| `MOMO_TIMEOUT` | Request timeout in seconds. Default `30`. |
| `COLLECTION_NEW_USER_ID`, `COLLECTION_NEW_CREDENTIAL_TOKEN` | Optional. The new platform's credentials, kept next to the old ones while both platforms run. Read only with `platform="new"`, see below. |

### Both platforms side by side

During the migration you'll have two credential pairs: the old API user and key, and the new System Credentials. Pass `platform` to choose a platform. That pins the base URL and reads that platform's own pair, ignoring `BASE_URL`:

| `platform=` | Base URL | Credentials read |
|---|---|---|
| `"legacy"` | `proxy.momoapi.mtn.com` | `COLLECTION_USER_ID` + `COLLECTION_API_SECRET` |
| `"new"` | `momoapi.momo.africa` | `COLLECTION_NEW_USER_ID` + `COLLECTION_NEW_CREDENTIAL_TOKEN`, else `COLLECTION_USER_ID` + `COLLECTION_CREDENTIAL_TOKEN`, else `MOMO_USER_ID` + `MOMO_CREDENTIAL_TOKEN` |

```python
legacy = Collection.from_env(platform="legacy")
new = Collection.from_env(platform="new")
```

A pair is always taken whole. The new platform never falls back to the old `*_API_SECRET`, because one platform's credentials never work on the other. [examples/legacy_and_new.py](examples/legacy_and_new.py) is a runnable version of this setup.

### Using a `.env` file

Copy [.env.example](.env.example) to `.env` and fill it in. Variables already set in the real environment take precedence over the file.

- The `momo-openapi` CLI reads `./.env` automatically. Use `--env-file path` for a different file. This needs `pip install "momo-openapi[dotenv]"`.
- In your own app, load the file yourself. Either call `load_dotenv()` before `from_env()`, or hand the values over directly:

  ```python
  from dotenv import dotenv_values
  from momo_openapi import Collection

  collection = Collection.from_env(dotenv_values(".env"))
  ```

Credentials are issued per wallet, not per API. If Collections and Disbursements share a wallet, set `MOMO_USER_ID` and `MOMO_CREDENTIAL_TOKEN` once. Products on different wallets each need their own pair.

## Migration checklist

**You can do these now:**

1. Confirm you call `proxy.momoapi.mtn.com` (VPN integrations are not affected). Find every place your app references that URL.
2. Upgrade to this package. It already sends `X-Target-Environment` on token requests.
3. Check that the new base URL is reachable from your servers, through your firewall and proxy:
   ```bash
   momo-openapi check
   ```
4. If you whitelist MTN source IPs for callbacks, ask for the new list by replying to the migration email, and whitelist it before cutover.
5. If you lack Partner Portal access, contact your account manager or support now.

**After MTN confirms the new platform is ready:**

6. In the Partner Portal, open **System and device credentials**, choose **+** under **System Credentials**, name the credential and choose **Create credential**. Copy the User ID and Credential Token immediately, because the token is not shown again.
7. Put them in `*_NEW_USER_ID` / `*_NEW_CREDENTIAL_TOKEN` to run both platforms side by side. Or, at cutover, put them in `*_USER_ID` / `*_CREDENTIAL_TOKEN` and remove any `BASE_URL` override that points at the legacy platform.
8. Verify the credentials work:
   ```bash
   momo-openapi token --platform new              # every configured product
   momo-openapi token collection --platform new   # just one
   ```
   It prints which platform and target environment issued the token. The token itself is never printed. Without `--platform`, it uses `BASE_URL` and the default credential names.

Until the new platform is confirmed, stay on the legacy platform with your existing API user and key:

```bash
BASE_URL=https://proxy.momoapi.mtn.com
```

For questions, write to support.momodeveloper@mtn.com and cc your account manager.

## Running both platforms (pilot traffic)

Both platforms run in parallel for one month after cutover. You can send part of your traffic to the new one first. Both kinds of transaction show up in the Partner Portal. **A transaction's status can only be read on the platform that processed it.** Keep a client per platform, and store `client.base_url` with each reference:

```python
from momo_openapi import Collection

new = Collection.from_env(platform="new")
legacy = Collection.from_env(platform="legacy")
clients = {c.base_url: c for c in (new, legacy)}

client = new if in_pilot(order) else legacy
reference = client.request_to_pay(amount, msisdn, external_id=order.id)
save(order, reference=reference, platform=client.base_url)

# later
status = clients[order.platform].get_transaction_status(order.reference)
```

## Errors

All exceptions derive from `momo_openapi.MomoError`:

- `ConfigurationError`: a required setting is missing, such as currency or credentials.
- `AuthenticationError`: the token endpoint answered 401. With `code == "invalid_client"`, the platform doesn't recognise the User ID / Credential Token pair: check it was created under **System credentials** for the right wallet, and that it belongs to the platform you're calling. A 401 that mentions the subscription key is about `Ocp-Apim-Subscription-Key`.
- `MomoAPIError`: any other non-success response, including a 400, 403 or 5xx from the token endpoint. It carries `status_code`, `body` and `code`, which is MoMo's `code` (e.g. `RESOURCE_NOT_FOUND`) or OAuth's `error` (e.g. `invalid_client`). Gateway HTML error pages are shortened to their title in the message.

```python
from momo_openapi import MomoAPIError

try:
    collection.get_transaction_status(reference)
except MomoAPIError as exc:
    if exc.code == "RESOURCE_NOT_FOUND":
        ...  # unknown reference, or it was created on the other platform
```

## Sandbox

The sandbox at `sandbox.momodeveloper.mtn.com` is not part of the migration. There you create an API user and key yourself:

```python
from momo_openapi import Collection

collection = Collection.for_sandbox("YOUR_COLLECTION_SUBSCRIPTION_KEY")
reference = collection.request_to_pay("100", "46733123453", external_id="test-1")
```

`provision_sandbox_user(subscription_key)` returns the `(user_id, api_key)` pair if you'd rather store it.

## Upgrading from the old `mtnmomoapi` module

| Old | New |
|---|---|
| `Collection()` | `Collection.from_env()` |
| `requestToPay(amount, phone, external_id, payernote, payermessage)` | `request_to_pay(amount, phone, external_id, payer_message=..., payee_note=...)` returns the reference ID |
| `transfer(amount, phone, external_id, payermessage, payermessageNone)` | `transfer(amount, phone, external_id, payer_message=..., payee_note=...)` returns the reference ID |
| `getTransactionStatus(ref)` | `get_transaction_status(ref)` returns MoMo's JSON |
| `getBalance()` / `authToken()` | `get_balance()` / `get_access_token()` |
| Failures returned a status code or raised `Exception` | Failures raise `MomoAPIError` |

Clients no longer create an API user on construction. Production credentials come from the Partner Portal, and for the sandbox you call `for_sandbox()`.

The old module built its Basic header with `basicauth.encode()`, which URL-encodes the user ID and key. That was harmless with UUIDs and hex keys, but the new platform's gateway answers 500 to it. It also sent the `python-requests` User-Agent and used a 3-second timeout, while the new platform currently takes 10–20 seconds to answer a token request. Patching the old module only for the new base URL and header is therefore not enough.

## Development

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/pytest
```

[examples/legacy_and_new.py](examples/legacy_and_new.py) shows the package on both platforms side by side, and it doubles as a manual check. It reads `.env` and passes `platform=` for every call, so `BASE_URL` doesn't matter. It can check each platform's credentials and balance, collect a payment or make a payout and wait for the final status, and find an earlier transaction on whichever platform created it. It is not part of the published package. `collect` and `disburse` move real money.

```bash
.venv/bin/python examples/legacy_and_new.py token                  # both platforms
.venv/bin/python examples/legacy_and_new.py balance --platform legacy
.venv/bin/python examples/legacy_and_new.py collect --platform new --amount 100 --ref swap-123
.venv/bin/python examples/legacy_and_new.py disburse --platform legacy --amount 30000 --ref payout-7
.venv/bin/python examples/legacy_and_new.py status <reference>     # tries each platform
```

## License

MIT © Dali Hillary
