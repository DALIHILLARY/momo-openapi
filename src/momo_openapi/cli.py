"""Migration readiness checks: ``momo-openapi check`` and ``momo-openapi token``."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

from .collection import Collection
from .config import NEW_PLATFORM_URL, PLATFORM_URLS, PRODUCTS, MomoConfig
from .connectivity import check_connectivity
from .disbursement import Disbursement
from .errors import ConfigurationError, MomoError
from .remittance import Remittance

CLIENTS = {"collection": Collection, "disbursement": Disbursement, "remittance": Remittance}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="momo-openapi",
        description="Readiness checks for the MoMo Open API platform migration.",
    )
    parser.add_argument(
        "--env-file",
        help="load settings from this file; defaults to ./.env when present (needs momo-openapi[dotenv])",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="check that this machine can reach the MoMo base URL")
    check.add_argument("--base-url", help=f"defaults to $BASE_URL, then {NEW_PLATFORM_URL}")
    check.add_argument("--timeout", type=float, default=10.0)

    token = commands.add_parser("token", help="create an access token with credentials from the environment")
    # Validated by hand: argparse rejects an empty nargs="*" list against choices on older Pythons.
    token.add_argument("products", nargs="*", metavar="product", help=f"any of {', '.join(PRODUCTS)}; defaults to all")
    token.add_argument(
        "--platform",
        choices=PLATFORM_URLS,
        help="use this platform and its own credentials (*_NEW_* for new); default: BASE_URL",
    )

    args = parser.parse_args(argv)
    _load_env_file(parser, args.env_file)
    if args.command == "token":
        unknown = sorted(set(args.products) - set(PRODUCTS))
        if unknown:
            token.error(f"unknown product(s) {', '.join(unknown)}; choose from {', '.join(PRODUCTS)}")
    if args.command == "check":
        return _check(args.base_url or os.environ.get("BASE_URL") or NEW_PLATFORM_URL, args.timeout)
    return _token(args.products or PRODUCTS, explicit=bool(args.products), platform=args.platform)


def _load_env_file(parser: argparse.ArgumentParser, path: str | None) -> None:
    env_file = Path(path or ".env")
    if not env_file.is_file():
        if path:
            parser.error(f"env file {path} not found")
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        message = f"python-dotenv is needed to read {env_file}: pip install 'momo-openapi[dotenv]'"
        if path:
            parser.error(message)
        print(f"WARN  {message}; ignoring it", file=sys.stderr)
        return
    # Variables already set in the environment win over the file.
    load_dotenv(env_file, override=False)


def _check(base_url: str, timeout: float) -> int:
    proxy_url = os.environ.get("MOMO_PROXY_URL") or os.environ.get("QUOTAGUARDSTATIC_URL")
    proxies = {"http": proxy_url, "https": proxy_url} if proxy_url else None
    result = check_connectivity(base_url, timeout=timeout, proxies=proxies)
    via = f" via {', '.join(result.addresses)}" if result.addresses else ""
    if result.reachable:
        print(f"OK    {base_url} is reachable (HTTP {result.status_code}){via}")
        return 0
    print(f"FAIL  {base_url} is not reachable{via}: {result.error}")
    return 1


def _token(products: Sequence[str], *, explicit: bool, platform: str | None = None) -> int:
    failed = succeeded = 0
    for product in products:
        try:
            config = MomoConfig.from_env(product, platform=platform)
        except ConfigurationError as exc:
            if explicit:
                print(f"FAIL  {product}: {exc}")
                failed += 1
            else:
                print(f"SKIP  {product}: not configured")
            continue
        try:
            CLIENTS[product](config).get_access_token()
        except MomoError as exc:
            print(f"FAIL  {product}: {exc}")
            failed += 1
            continue
        print(f"OK    {product}: token issued by {config.base_url} for {config.target_environment}")
        succeeded += 1
    if not succeeded and not failed:
        print("No product is configured; see the README for the environment variables.")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
