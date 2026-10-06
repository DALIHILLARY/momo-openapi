from __future__ import annotations

from uuid import uuid4

import requests

from .config import SANDBOX_URL, USER_AGENT
from .errors import MomoAPIError


def provision_sandbox_user(
    subscription_key: str,
    callback_host: str = "localhost",
    *,
    session: requests.Session | None = None,
    timeout: float = 30.0,
) -> tuple[str, str]:
    """Create a sandbox API user and API key, returned as ``(user_id, api_key)``.

    Only the sandbox supports this. Production credentials (User ID and
    Credential Token) are generated in the Partner Portal under
    "System and device credentials".
    """
    http = session or requests
    user_id = str(uuid4())
    headers = {"Ocp-Apim-Subscription-Key": subscription_key, "User-Agent": USER_AGENT}

    response = http.post(
        f"{SANDBOX_URL}/v1_0/apiuser",
        headers={**headers, "X-Reference-Id": user_id},
        json={"providerCallbackHost": callback_host},
        timeout=timeout,
    )
    if response.status_code != 201:
        raise MomoAPIError.from_response(response)

    response = http.post(f"{SANDBOX_URL}/v1_0/apiuser/{user_id}/apikey", headers=headers, timeout=timeout)
    if response.status_code != 201:
        raise MomoAPIError.from_response(response)
    return user_id, response.json()["apiKey"]
