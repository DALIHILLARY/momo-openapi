from __future__ import annotations

import socket
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests

from .config import NEW_PLATFORM_URL, USER_AGENT


@dataclass(frozen=True)
class ConnectivityResult:
    base_url: str
    reachable: bool
    addresses: tuple[str, ...] = ()
    status_code: int | None = None
    error: str | None = None


def check_connectivity(
    base_url: str = NEW_PLATFORM_URL,
    *,
    timeout: float = 10.0,
    proxies: dict[str, str] | None = None,
) -> ConnectivityResult:
    """Check that this machine can open an HTTPS connection to ``base_url``.

    Any HTTP answer counts as reachable: the point is to prove that DNS,
    firewall rules and TLS allow traffic to the platform before cutting over.
    """
    split = urlsplit(base_url)
    addresses: tuple[str, ...] = ()
    try:
        infos = socket.getaddrinfo(split.hostname, split.port or 443, proto=socket.IPPROTO_TCP)
        addresses = tuple(sorted({str(info[4][0]) for info in infos}))
    except socket.gaierror as exc:
        # Behind a proxy the local resolver may legitimately fail; let the request decide.
        if not proxies:
            return ConnectivityResult(base_url, False, error=f"DNS lookup failed: {exc}")

    try:
        response = requests.get(
            base_url, headers={"User-Agent": USER_AGENT}, timeout=timeout, proxies=proxies, allow_redirects=False
        )
    except requests.RequestException as exc:
        return ConnectivityResult(base_url, False, addresses, error=str(exc))
    return ConnectivityResult(base_url, True, addresses, status_code=response.status_code)
