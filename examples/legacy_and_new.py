"""Use momo-openapi on the legacy and the new MoMo platform, side by side.

MTN is moving the MoMo Open API from proxy.momoapi.mtn.com ("legacy") to
momoapi.momo.africa ("new"). While both run you hold one credential pair per
platform, and a transaction's status can only be read on the platform that
created it. This script shows how one codebase handles both.

Settings come from .env (copy .env.example). ``platform=`` pins the base URL and
reads that platform's own credentials, so both pairs can sit in the same file:

    platform="legacy"  proxy.momoapi.mtn.com  COLLECTION_USER_ID + COLLECTION_API_SECRET
    platform="new"     momoapi.momo.africa    COLLECTION_NEW_USER_ID + COLLECTION_NEW_CREDENTIAL_TOKEN

DISBURSEMENT_* and REMITTANCE_* work the same way. The subscription keys
(*_PRIMARY_KEY), MTN_ENVIRONMENT, CURRENCY and CALLBACK_URL are shared by both.

Needs python-dotenv (pip install "momo-openapi[dotenv]"). From the repo root:

    .venv/bin/python examples/legacy_and_new.py token
    .venv/bin/python examples/legacy_and_new.py balance --platform legacy
    .venv/bin/python examples/legacy_and_new.py collect --platform new --amount 500 --phone 256772123456
    .venv/bin/python examples/legacy_and_new.py disburse --platform legacy --amount 500 --phone 256772123456
    .venv/bin/python examples/legacy_and_new.py status <reference>

collect and disburse move real money, so use small amounts.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from typing import Any, Callable, Sequence

import requests
from dotenv import load_dotenv

from momo_openapi import (
    LEGACY_PLATFORM_URL,
    NEW_PLATFORM_URL,
    AuthenticationError,
    Collection,
    ConfigurationError,
    Disbursement,
    MomoAPIError,
    MomoConfig,
    MomoError,
    Remittance,
)

PLATFORMS = ("legacy", "new")
CLIENTS = {"collection": Collection, "disbursement": Disbursement, "remittance": Remittance}


def make_client(product: str, platform: str) -> Any:
    """One client per platform, built from the environment."""
    return CLIENTS[product].from_env(platform=platform)


def make_collections_in_code() -> dict[str, Collection]:
    """The same two clients without environment variables. The commands below don't use it.

    Only the base URL and the credential pair differ between the platforms.
    """
    shared = {
        "subscription_key": "<Ocp-Apim-Subscription-Key>",  # unchanged by the migration
        "target_environment": "mtnuganda",
        "currency": "UGX",
        "callback_url": "https://example.com/momo/callback",
    }
    return {
        "legacy": Collection(MomoConfig(
            base_url=LEGACY_PLATFORM_URL,
            user_id="<old API user>",
            credential_token="<old API key>",
            **shared,
        )),
        "new": Collection(MomoConfig(
            base_url=NEW_PLATFORM_URL,
            user_id="<Partner Portal User ID>",
            credential_token="<Partner Portal Credential Token>",
            **shared,
        )),
    }


def wait_for_final_status(client: Any, reference: str, timeout: float, interval: float = 5.0) -> dict[str, Any]:
    """Poll until the transaction leaves PENDING. In production, prefer your callback URL."""
    deadline = time.monotonic() + timeout
    while True:
        result = client.get_transaction_status(reference)
        if result.get("status") != "PENDING" or time.monotonic() >= deadline:
            return result
        time.sleep(interval)


def report(result: dict[str, Any]) -> int:
    print(f"Status: {result.get('status')}")
    if result.get("reason"):
        print(f"Reason: {result['reason']}")
    return 0 if result.get("status") == "SUCCESSFUL" else 1


def on_each_platform(product: str, platforms: Sequence[str], action: Callable[[Any], str]) -> int:
    """Run ``action`` on every platform that has credentials and report each outcome.

    One platform failing doesn't stop the other, so each can be checked on its own.
    """
    results = []
    for platform in platforms:
        try:
            client = make_client(product, platform)
        except ConfigurationError as exc:
            print(f"SKIP  {platform:6}  {exc}")
            continue
        try:
            print(f"OK    {platform:6}  {client.base_url}  {action(client)}")
            results.append(True)
        except AuthenticationError as exc:
            # invalid_client: this platform doesn't know the pair. The other platform's pair never works here.
            print(f"FAIL  {platform:6}  {client.base_url}  credentials rejected: {exc.code or exc}")
            results.append(False)
        except (MomoError, requests.RequestException) as exc:
            print(f"FAIL  {platform:6}  {client.base_url}  {exc}")
            results.append(False)
    return 0 if results and all(results) else 1


def cmd_token(args: argparse.Namespace) -> int:
    def check(client: Any) -> str:
        client.get_access_token()
        return "token issued"

    return on_each_platform(args.product, [args.platform] if args.platform else PLATFORMS, check)


def cmd_balance(args: argparse.Namespace) -> int:
    def balance(client: Any) -> str:
        result = client.get_balance()
        return f"{result.get('availableBalance')} {result.get('currency')}"

    return on_each_platform(args.product, [args.platform] if args.platform else PLATFORMS, balance)


def cmd_collect(args: argparse.Namespace) -> int:
    collection = Collection.from_env(platform=args.platform)
    reference = collection.request_to_pay(
        args.amount, args.phone, external_id=args.ref, payer_message=f"Payment {args.ref}", payee_note=args.ref
    )
    # Store both: the status can only be read back on this platform.
    print(f"Accepted on {collection.base_url}, reference {reference}")
    print("Approve the prompt on the phone...")
    return report(wait_for_final_status(collection, reference, args.wait))


def cmd_disburse(args: argparse.Namespace) -> int:
    disbursement = Disbursement.from_env(platform=args.platform)
    reference = disbursement.transfer(
        args.amount, args.phone, external_id=args.ref, payer_message=f"Payout {args.ref}", payee_note=args.ref
    )
    print(f"Accepted on {disbursement.base_url}, reference {reference}")
    return report(wait_for_final_status(disbursement, reference, args.wait))


def cmd_status(args: argparse.Namespace) -> int:
    """Look a reference up on the platform that created it.

    In your app, store ``client.base_url`` with each reference and ask that client
    directly. Without --platform, this tries each one, for records that lack it.
    """
    for platform in [args.platform] if args.platform else PLATFORMS:
        try:
            client = make_client(args.product, platform)
        except ConfigurationError:
            if args.platform:
                raise
            continue
        try:
            result = client.get_transaction_status(args.reference)
        except MomoAPIError as exc:
            if exc.code != "RESOURCE_NOT_FOUND":
                raise
            print(f"Not found on {platform} ({client.base_url})")
            continue
        print(f"Found on {platform} ({client.base_url})")
        return report(result)
    print("Reference not found on any configured platform")
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    load_dotenv()  # variables already set in the environment win over .env

    parser = argparse.ArgumentParser(description="Use momo-openapi on the legacy and the new MoMo platform.")
    commands = parser.add_subparsers(dest="command", required=True)

    token = commands.add_parser("token", help="check each platform's credentials by requesting a token")
    token.set_defaults(handler=cmd_token)
    balance = commands.add_parser("balance", help="show the account balance on each platform")
    balance.set_defaults(handler=cmd_balance)
    for command in (token, balance):
        command.add_argument("--platform", choices=PLATFORMS, help="default: both")
        command.add_argument("--product", choices=CLIENTS, default="collection")

    collect = commands.add_parser("collect", help="request a payment and wait for the outcome")
    collect.set_defaults(handler=cmd_collect)
    disburse = commands.add_parser("disburse", help="pay out to a wallet and wait for the outcome")
    disburse.set_defaults(handler=cmd_disburse)
    test_phone = os.environ.get("MOMO_TEST_PHONE")
    for command in (collect, disburse):
        command.add_argument("--platform", choices=PLATFORMS, required=True)
        command.add_argument("--amount", required=True)
        command.add_argument(
            "--phone", default=test_phone, required=not test_phone,
            help="MSISDN in international format, e.g. 256772123456 (default: $MOMO_TEST_PHONE)",
        )
        command.add_argument("--ref", default=f"example-{uuid.uuid4().hex[:8]}", help="your external ID")
        command.add_argument("--wait", type=float, default=120.0, help="seconds to wait for a final status")

    status = commands.add_parser("status", help="find a transaction and show its status")
    status.set_defaults(handler=cmd_status)
    status.add_argument("reference")
    status.add_argument("--platform", choices=PLATFORMS, help="default: try each")
    status.add_argument("--product", choices=CLIENTS, default="collection")

    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except AuthenticationError as exc:
        print(f"Credentials rejected by {exc.url}: {exc.code or exc}", file=sys.stderr)
    except (MomoError, requests.RequestException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
