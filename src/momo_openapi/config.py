from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from ._version import __version__
from .errors import ConfigurationError

NEW_PLATFORM_URL = "https://momoapi.momo.africa"
LEGACY_PLATFORM_URL = "https://proxy.momoapi.mtn.com"
SANDBOX_URL = "https://sandbox.momodeveloper.mtn.com"

# The new platform's gateway answers 403 to any User-Agent containing "python-requests",
# so never send the requests default.
USER_AGENT = f"momo-openapi/{__version__}"

SANDBOX_ENVIRONMENT = "sandbox"
PRODUCTS = ("collection", "disbursement", "remittance")
PLATFORM_URLS = {"legacy": LEGACY_PLATFORM_URL, "new": NEW_PLATFORM_URL}


@dataclass(frozen=True)
class MomoConfig:
    """Settings for one MoMo product (collection, disbursement or remittance).

    ``user_id`` and ``credential_token`` are the System Credentials generated in the
    Partner Portal. They replace the API user and API key of the legacy platform.
    In the sandbox they are the provisioned API user and API key.

    ``base_url`` defaults to the sandbox when ``target_environment`` is ``"sandbox"``
    and to the new platform (``https://momoapi.momo.africa``) otherwise.
    """

    subscription_key: str = field(repr=False)
    user_id: str
    credential_token: str = field(repr=False)
    target_environment: str
    base_url: str = ""
    callback_url: str | None = None
    currency: str | None = None
    timeout: float = 30.0
    proxy_url: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        required = ("subscription_key", "user_id", "credential_token", "target_environment")
        missing = [name for name in required if not getattr(self, name)]
        if missing:
            raise ConfigurationError(f"Missing required settings: {', '.join(missing)}")
        base_url = self.base_url or (SANDBOX_URL if self.is_sandbox else NEW_PLATFORM_URL)
        object.__setattr__(self, "base_url", base_url.rstrip("/"))

    @property
    def is_sandbox(self) -> bool:
        return self.target_environment == SANDBOX_ENVIRONMENT

    @property
    def proxies(self) -> dict[str, str] | None:
        if not self.proxy_url:
            return None
        return {"http": self.proxy_url, "https": self.proxy_url}

    @classmethod
    def from_env(
        cls,
        product: str,
        environ: Mapping[str, str] | None = None,
        *,
        platform: str | None = None,
    ) -> MomoConfig:
        """Build the settings for ``product`` from environment variables.

        The variable names match the legacy integration, so existing deployments
        only need new values. See the README for the full list.

        By default BASE_URL picks the platform. ``platform`` ("legacy" or "new")
        pins it instead and reads that platform's own credentials, so both can be
        configured side by side while they run in parallel:

        - legacy: ``{P}_USER_ID`` and ``{P}_API_SECRET``, the old API user and key
        - new: ``{P}_NEW_USER_ID`` and ``{P}_NEW_CREDENTIAL_TOKEN``, else
          ``{P}_USER_ID`` and ``{P}_CREDENTIAL_TOKEN``, else the shared
          ``MOMO_USER_ID`` and ``MOMO_CREDENTIAL_TOKEN``
        """
        if product not in PRODUCTS:
            raise ConfigurationError(f"Unknown product {product!r}, expected one of {PRODUCTS}")
        if platform is not None and platform not in PLATFORM_URLS:
            raise ConfigurationError(f"Unknown platform {platform!r}, expected one of {tuple(PLATFORM_URLS)}")
        env = os.environ if environ is None else environ
        prefix = product.upper()

        required = {
            "subscription_key": (f"{prefix}_PRIMARY_KEY",),
            "target_environment": ("MTN_ENVIRONMENT",),
        }
        if platform is None:
            required["user_id"] = (f"{prefix}_USER_ID", "MOMO_USER_ID")
            required["credential_token"] = (
                f"{prefix}_CREDENTIAL_TOKEN",
                f"{prefix}_API_SECRET",
                "MOMO_CREDENTIAL_TOKEN",
            )
        values: dict[str, str] = {}
        missing = []
        for name, variables in required.items():
            value = _first(env, variables)
            if value is None:
                missing.append(" or ".join(variables))
            else:
                values[name] = value
        if platform is not None:
            # Take a whole pair: mixing one platform's user ID with the other's token never works.
            pairs = _credential_pairs(prefix, platform)
            pair = next(((env[user], env[token]) for user, token in pairs if env.get(user) and env.get(token)), None)
            if pair is None:
                missing.append(" or ".join(f"{user} and {token}" for user, token in pairs))
            else:
                values["user_id"], values["credential_token"] = pair
        if missing:
            raise ConfigurationError("Missing environment variables: " + "; ".join(missing))

        timeout = env.get("MOMO_TIMEOUT")
        return cls(
            **values,
            base_url=PLATFORM_URLS[platform] if platform else env.get("BASE_URL", ""),
            callback_url=env.get("CALLBACK_URL") or None,
            currency=env.get("CURRENCY") or None,
            timeout=float(timeout) if timeout else 30.0,
            proxy_url=_first(env, ("MOMO_PROXY_URL", "QUOTAGUARDSTATIC_URL")),
        )


def _credential_pairs(prefix: str, platform: str) -> list[tuple[str, str]]:
    if platform == "legacy":
        return [(f"{prefix}_USER_ID", f"{prefix}_API_SECRET")]
    return [
        (f"{prefix}_NEW_USER_ID", f"{prefix}_NEW_CREDENTIAL_TOKEN"),
        (f"{prefix}_USER_ID", f"{prefix}_CREDENTIAL_TOKEN"),
        ("MOMO_USER_ID", "MOMO_CREDENTIAL_TOKEN"),
    ]


def _first(env: Mapping[str, str], names: Sequence[str]) -> str | None:
    for name in names:
        value = env.get(name)
        if value:
            return value
    return None
