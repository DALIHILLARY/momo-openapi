from __future__ import annotations

import re
from typing import Any

import requests


class MomoError(Exception):
    """Base class for every error raised by momo_openapi."""


class ConfigurationError(MomoError):
    """Required settings are missing or invalid."""


class MomoAPIError(MomoError):
    """The MoMo API answered with an unexpected HTTP status."""

    def __init__(self, status_code: int, body: Any, *, method: str = "", url: str = "") -> None:
        self.status_code = status_code
        self.body = body
        self.method = method
        self.url = url
        super().__init__(f"{method} {url} returned HTTP {status_code}: {_summarize(body)}".strip())

    @property
    def code(self) -> str | None:
        """The error code in the body: MoMo's ``code`` (e.g. ``RESOURCE_NOT_FOUND``)
        or, from the token endpoints, OAuth's ``error`` (e.g. ``invalid_client``)."""
        if isinstance(self.body, dict):
            return self.body.get("code") or self.body.get("error")
        return None

    @classmethod
    def from_response(cls, response: requests.Response) -> MomoAPIError:
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        method = response.request.method if response.request is not None else ""
        return cls(response.status_code, body, method=method or "", url=response.url)


def _summarize(body: Any) -> Any:
    """Gateway errors come back as HTML pages; their <title> says all there is to say."""
    if isinstance(body, str):
        match = re.search(r"<title>(.*?)</title>", body, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
    return body


class AuthenticationError(MomoAPIError):
    """The token endpoint rejected the credentials (HTTP 401).

    ``invalid_client`` means the User ID / Credential Token pair is not known to
    the platform the base URL points at. A 401 that mentions the subscription key
    is about ``Ocp-Apim-Subscription-Key`` instead.
    """
