"""Check your credentials on the new platform (momoapi.momo.africa) by requesting a token.

Reads .env, where PRODUCT is COLLECTION, DISBURSEMENT or REMITTANCE:
- PRODUCT_PRIMARY_KEY
- PRODUCT_NEW_USER_ID and PRODUCT_NEW_CREDENTIAL_TOKEN: System Credentials from the
  Partner Portal. After cutover, PRODUCT_USER_ID and PRODUCT_CREDENTIAL_TOKEN work too.
- MTN_ENVIRONMENT

    .venv/bin/python examples/new/check_credentials.py             # collection
    .venv/bin/python examples/new/check_credentials.py disbursement

Clients fetch, cache and renew tokens themselves, so you only call
get_access_token() yourself to test credentials.
"""

import argparse
import sys

from dotenv import load_dotenv

from momo_openapi import AuthenticationError, Collection, Disbursement, Remittance

load_dotenv()  # variables already set in the environment win over .env

CLIENTS = {"collection": Collection, "disbursement": Disbursement, "remittance": Remittance}

parser = argparse.ArgumentParser(description="Check credentials on the new platform.")
parser.add_argument("product", nargs="?", choices=CLIENTS, default="collection")
args = parser.parse_args()

client = CLIENTS[args.product].from_env(platform="new")

try:
    client.get_access_token()
except AuthenticationError as exc:
    # invalid_client: the new platform doesn't know this User ID and Credential Token.
    # Check they were created under System credentials for the right wallet.
    sys.exit(f"{client.base_url} rejected the {args.product} credentials: {exc.code or exc}")

print(f"OK: {client.base_url} issued a {args.product} token")
