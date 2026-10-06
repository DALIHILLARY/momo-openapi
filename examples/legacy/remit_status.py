"""Show the status of a remittance made on the legacy platform (proxy.momoapi.mtn.com).

A status can only be read on the platform that created the transaction, so pass a
reference from examples/legacy/remit.py. One from the new platform is not found here.

Reads .env:
- REMITTANCE_PRIMARY_KEY
- REMITTANCE_USER_ID and REMITTANCE_API_SECRET: the old API user and API key
- MTN_ENVIRONMENT

    .venv/bin/python examples/legacy/remit_status.py <reference>
"""

import argparse
import json
import sys

from dotenv import load_dotenv

from momo_openapi import Remittance, MomoAPIError

load_dotenv()  # variables already set in the environment win over .env

parser = argparse.ArgumentParser(description="Show a remittance's status on the legacy platform.")
parser.add_argument("reference", help="the reference printed by remit.py")
args = parser.parse_args()

remittance = Remittance.from_env(platform="legacy")
try:
    result = remittance.get_transaction_status(args.reference)
except MomoAPIError as exc:
    if exc.code == "RESOURCE_NOT_FOUND":
        sys.exit(f"{args.reference} is unknown on {remittance.base_url}. Was it created on the new platform?")
    raise

print(f"Status: {result.get('status')}")  # PENDING, SUCCESSFUL or FAILED
print(json.dumps(result, indent=2))
