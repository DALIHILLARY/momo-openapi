from __future__ import annotations

import base64
import logging
import threading
import time
from decimal import Decimal
from typing import Any, ClassVar, Mapping, TypeVar, Union
from uuid import uuid4

import requests

from .config import SANDBOX_ENVIRONMENT, USER_AGENT, MomoConfig
from .errors import AuthenticationError, ConfigurationError, MomoAPIError
from .sandbox import provision_sandbox_user

logger = logging.getLogger("momo_openapi")

Amount = Union[str, int, Decimal]
ClientT = TypeVar("ClientT", bound="ProductClient")

# Refresh access tokens this many seconds before MoMo says they expire.
TOKEN_EXPIRY_MARGIN = 60


class ProductClient:
    """Shared plumbing for the collection, disbursement and remittance clients."""

    product: ClassVar[str]

    def __init__(self, config: MomoConfig, *, session: requests.Session | None = None) -> None:
        self.config = config
        self._session = session or requests.Session()
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = threading.Lock()

    @classmethod
    def from_env(
        cls: type[ClientT],
        environ: Mapping[str, str] | None = None,
        *,
        platform: str | None = None,
        session: requests.Session | None = None,
    ) -> ClientT:
        """Build a client from environment variables (see :meth:`MomoConfig.from_env`)."""
        return cls(MomoConfig.from_env(cls.product, environ, platform=platform), session=session)

    @classmethod
    def for_sandbox(
        cls: type[ClientT],
        subscription_key: str,
        *,
        callback_host: str = "localhost",
        callback_url: str | None = None,
        currency: str = "EUR",
        session: requests.Session | None = None,
    ) -> ClientT:
        """Provision a fresh sandbox API user and return a client that uses it."""
        user_id, api_key = provision_sandbox_user(subscription_key, callback_host, session=session)
        config = MomoConfig(
            subscription_key=subscription_key,
            user_id=user_id,
            credential_token=api_key,
            target_environment=SANDBOX_ENVIRONMENT,
            callback_url=callback_url,
            currency=currency,
        )
        return cls(config, session=session)

    @property
    def base_url(self) -> str:
        """The platform this client talks to.

        A transaction's status can only be read on the platform that processed it,
        so store this next to the reference ID while old and new platforms coexist.
        """
        return self.config.base_url

    def get_access_token(self, *, force_refresh: bool = False) -> str:
        """Return a bearer token, reusing the cached one until shortly before it expires."""
        with self._token_lock:
            if not force_refresh and self._token and time.monotonic() < self._token_expires_at:
                return self._token

            credentials = f"{self.config.user_id}:{self.config.credential_token}".encode()
            response = self._send(
                "POST",
                f"/{self.product}/token/",
                headers={
                    "Authorization": "Basic " + base64.b64encode(credentials).decode(),
                    "Ocp-Apim-Subscription-Key": self.config.subscription_key,
                    # Optional on the legacy platform, mandatory on momoapi.momo.africa.
                    "X-Target-Environment": self.config.target_environment,
                },
            )
            # Only a 401 is about the credentials; a 400 (bad X-Target-Environment),
            # a 403 (gateway block) or a 5xx is not.
            if response.status_code == 401:
                raise AuthenticationError.from_response(response)
            if response.status_code != 200:
                raise MomoAPIError.from_response(response)

            data = response.json()
            expires_in = int(data.get("expires_in", 3600))
            self._token = data["access_token"]
            self._token_expires_at = time.monotonic() + max(expires_in - TOKEN_EXPIRY_MARGIN, 0)
            return self._token

    def get_balance(self) -> dict[str, Any]:
        """Return the account balance, e.g. ``{"availableBalance": "100", "currency": "EUR"}``."""
        return self._request("GET", f"/{self.product}/v1_0/account/balance").json()

    def _payment_payload(
        self,
        amount: Amount,
        currency: str | None,
        external_id: str,
        party_role: str,
        party_id: str,
        party_id_type: str,
        payer_message: str,
        payee_note: str,
    ) -> dict[str, Any]:
        currency = currency or self.config.currency
        if not currency:
            raise ConfigurationError("currency is required: pass it or set it on the config (CURRENCY)")
        return {
            "amount": str(amount),
            "currency": currency,
            "externalId": str(external_id),
            party_role: {"partyIdType": party_id_type, "partyId": str(party_id)},
            "payerMessage": payer_message,
            "payeeNote": payee_note,
        }

    def _initiate(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        callback_url: str | None,
        reference_id: str | None,
    ) -> str:
        reference_id = reference_id or str(uuid4())
        headers = {"X-Reference-Id": reference_id}
        callback_url = callback_url or self.config.callback_url
        if callback_url:
            headers["X-Callback-Url"] = callback_url
        self._request("POST", path, json=payload, headers=headers, expected=(202,))
        logger.info("MoMo %s accepted %s on %s", self.product, reference_id, self.base_url)
        return reference_id

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
        expected: tuple[int, ...] = (200,),
    ) -> requests.Response:
        request_headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Ocp-Apim-Subscription-Key": self.config.subscription_key,
            "X-Target-Environment": self.config.target_environment,
            **(headers or {}),
        }
        response = self._send(method, path, headers=request_headers, json=json)
        if response.status_code not in expected:
            raise MomoAPIError.from_response(response)
        return response

    def _send(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str],
        json: Any = None,
    ) -> requests.Response:
        logger.debug("%s %s%s", method, self.base_url, path)
        return self._session.request(
            method,
            self.base_url + path,
            headers={"User-Agent": USER_AGENT, **headers},
            json=json,
            timeout=self.config.timeout,
            proxies=self.config.proxies,
        )


class TransferClient(ProductClient):
    """Send money to a MoMo wallet (shared by disbursement and remittance)."""

    def transfer(
        self,
        amount: Amount,
        phone_number: str,
        external_id: str,
        *,
        currency: str | None = None,
        payer_message: str = "",
        payee_note: str = "",
        callback_url: str | None = None,
        reference_id: str | None = None,
        party_id_type: str = "MSISDN",
    ) -> str:
        """Transfer ``amount`` to ``phone_number``.

        Returns the X-Reference-Id to pass to :meth:`get_transaction_status`.
        MoMo processes transfers asynchronously, so a returned reference means
        the request was accepted, not that the money has moved.
        """
        payload = self._payment_payload(
            amount, currency, external_id, "payee", phone_number, party_id_type, payer_message, payee_note
        )
        return self._initiate(
            f"/{self.product}/v1_0/transfer", payload, callback_url=callback_url, reference_id=reference_id
        )

    def get_transaction_status(self, reference_id: str) -> dict[str, Any]:
        """Return the transfer's current state, including ``status`` (PENDING, SUCCESSFUL or FAILED)."""
        return self._request("GET", f"/{self.product}/v1_0/transfer/{reference_id}").json()
