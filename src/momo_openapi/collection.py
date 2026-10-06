from __future__ import annotations

from typing import Any

from ._base import Amount, ProductClient


class Collection(ProductClient):
    """Receive payments by asking customers to approve a debit from their MoMo wallet."""

    product = "collection"

    def request_to_pay(
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
        """Ask ``phone_number`` to approve a payment of ``amount``.

        Returns the X-Reference-Id to pass to :meth:`get_transaction_status`.
        MoMo processes the request asynchronously, so a returned reference means
        the request was accepted, not that the customer has paid.
        """
        payload = self._payment_payload(
            amount, currency, external_id, "payer", phone_number, party_id_type, payer_message, payee_note
        )
        return self._initiate(
            "/collection/v1_0/requesttopay", payload, callback_url=callback_url, reference_id=reference_id
        )

    def get_transaction_status(self, reference_id: str) -> dict[str, Any]:
        """Return the request's current state, including ``status`` (PENDING, SUCCESSFUL or FAILED)."""
        return self._request("GET", f"/collection/v1_0/requesttopay/{reference_id}").json()
