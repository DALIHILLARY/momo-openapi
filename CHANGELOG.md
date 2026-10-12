# Changelog

## 0.1.0 (2026-09-28)

First release, built for the MoMo Open API platform migration.

- Collection, Disbursement and Remittance clients.
- Defaults to the new platform, `https://momoapi.momo.africa`. Set `BASE_URL` to stay on `https://proxy.momoapi.mtn.com` until MTN confirms cutover.
- Authenticates with the Partner Portal System Credentials (User ID and Credential Token).
- Sends `X-Target-Environment` on every `*/token/` request, as the new platform requires.
- Caches access tokens until shortly before they expire.
- Sends `User-Agent: momo-openapi/<version>`, because the new platform's gateway returns 403 to the `python-requests` default.
- Sends Basic credentials raw. URL-encoding them, as `basicauth.encode()` does, gets a 500 from the new platform.
- `from_env(platform="legacy" | "new")`, `momo-openapi token --platform` and `momo-openapi check --platform` pick a platform with its own base URL and credential pair, so both platforms can be configured side by side: `BASE_URL` with `*_USER_ID` / `*_API_SECRET` for legacy, `NEW_BASE_URL` with `*_NEW_USER_ID` / `*_NEW_CREDENTIAL_TOKEN` for new.
- `AuthenticationError` is raised only for a 401 from the token endpoint. A 400, 403 or 5xx raises `MomoAPIError`. `MomoAPIError.code` also reads OAuth's `error` field (`invalid_client`), and gateway HTML error pages are shortened to their title.
- Sandbox API user provisioning via `provision_sandbox_user()` / `for_sandbox()`.
- `momo-openapi check` and `momo-openapi token` readiness checks. They read `./.env` (or `--env-file`) with the `dotenv` extra.
- Example scripts for every operation on each platform, in `examples/`.
