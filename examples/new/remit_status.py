"""Show the status of a remittance made on the new platform (momoapi.momo.africa).

A status can only be read on the platform that created the transaction, so pass a
reference from examples/new/remit.py. One from the legacy platform is not found here.

Reads .env:
- REMITTANCE_PRIMARY_KEY
- REMITTANCE_NEW_USER_ID and REMITTANCE_NEW_CREDENTIAL_TOKEN: System Credentials from the
  Partner Portal. After cutover, REMITTANCE_USER_ID and REMITTANCE_CREDENTIAL_TOKEN work too.
- MTN_ENVIRONMENT

    .venv/bin/python examples/new/remit_status.py <reference>
"""

import argparse
import json
import sys

from dotenv import load_dotenv

from momo_openapi import Remittance, MomoAPIError

load_dotenv()  # variables already set in the environment win over .env

parser = argparse.ArgumentParser(description="Show a remittance's status on the new platform.")
parser.add_argument("reference", help="the reference printed by remit.py")
args = parser.parse_args()

remittance = Remittance.from_env(platform="new")
try:
    result = remittance.get_transaction_status(args.reference)
except MomoAPIError as exc:
    if exc.code == "RESOURCE_NOT_FOUND":
        sys.exit(f"{args.reference} is unknown on {remittance.base_url}. Was it created on the legacy platform?")
    raise

print(f"Status: {result.get('status')}")  # PENDING, SUCCESSFUL or FAILED
print(json.dumps(result, indent=2))
