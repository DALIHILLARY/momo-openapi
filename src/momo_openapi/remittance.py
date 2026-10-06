from __future__ import annotations

from ._base import TransferClient


class Remittance(TransferClient):
    """Send cross-border remittances to MoMo wallets."""

    product = "remittance"
