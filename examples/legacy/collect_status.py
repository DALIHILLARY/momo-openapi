"""Show the status of a payment request made on the legacy platform (proxy.momoapi.mtn.com).

A status can only be read on the platform that created the transaction, so pass a
reference from examples/legacy/collect.py. One from the new platform is not found here.

Reads .env:
- COLLECTION_PRIMARY_KEY
- COLLECTION_USER_ID and COLLECTION_API_SECRET: the old API user and API key
- MTN_ENVIRONMENT

    .venv/bin/python examples/legacy/collect_status.py <reference>
"""

import argparse
import json
import sys

from dotenv import load_dotenv

from momo_openapi import Collection, MomoAPIError

load_dotenv()  # variables already set in the environment win over .env

parser = argparse.ArgumentParser(description="Show a payment request's status on the legacy platform.")
parser.add_argument("reference", help="the reference printed by collect.py")
args = parser.parse_args()

collection = Collection.from_env(platform="legacy")
try:
    result = collection.get_transaction_status(args.reference)
except MomoAPIError as exc:
    if exc.code == "RESOURCE_NOT_FOUND":
        sys.exit(f"{args.reference} is unknown on {collection.base_url}. Was it created on the new platform?")
    raise

print(f"Status: {result.get('status')}")  # PENDING, SUCCESSFUL or FAILED
print(json.dumps(result, indent=2))
