"""Check your credentials on the legacy platform (proxy.momoapi.mtn.com) by requesting a token.

Reads .env, where PRODUCT is COLLECTION, DISBURSEMENT or REMITTANCE:
- PRODUCT_PRIMARY_KEY
- PRODUCT_USER_ID and PRODUCT_API_SECRET: the old API user and API key
- MTN_ENVIRONMENT

    .venv/bin/python examples/legacy/check_credentials.py             # collection
    .venv/bin/python examples/legacy/check_credentials.py disbursement

Clients fetch, cache and renew tokens themselves, so you only call
get_access_token() yourself to test credentials.
"""

import argparse
import sys

from dotenv import load_dotenv

from momo_openapi import AuthenticationError, Collection, Disbursement, Remittance

load_dotenv()  # variables already set in the environment win over .env

CLIENTS = {"collection": Collection, "disbursement": Disbursement, "remittance": Remittance}

parser = argparse.ArgumentParser(description="Check credentials on the legacy platform.")
parser.add_argument("product", nargs="?", choices=CLIENTS, default="collection")
args = parser.parse_args()

client = CLIENTS[args.product].from_env(platform="legacy")

try:
    client.get_access_token()
except AuthenticationError as exc:
    # invalid_client: the legacy platform doesn't know this API user and key.
    sys.exit(f"{client.base_url} rejected the {args.product} credentials: {exc.code or exc}")

print(f"OK: {client.base_url} issued a {args.product} token")
