from __future__ import annotations

from ._base import TransferClient


class Disbursement(TransferClient):
    """Pay out from your disbursement account to MoMo wallets."""

    product = "disbursement"
