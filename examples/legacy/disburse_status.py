"""Show the status of a payout made on the legacy platform (proxy.momoapi.mtn.com).

A status can only be read on the platform that created the transaction, so pass a
reference from examples/legacy/disburse.py. One from the new platform is not found here.

Reads .env:
- DISBURSEMENT_PRIMARY_KEY
- DISBURSEMENT_USER_ID and DISBURSEMENT_API_SECRET: the old API user and API key
- MTN_ENVIRONMENT

    .venv/bin/python examples/legacy/disburse_status.py <reference>
"""

import argparse
import json
import sys

from dotenv import load_dotenv

from momo_openapi import Disbursement, MomoAPIError

load_dotenv()  # variables already set in the environment win over .env

parser = argparse.ArgumentParser(description="Show a payout's status on the legacy platform.")
parser.add_argument("reference", help="the reference printed by disburse.py")
args = parser.parse_args()

disbursement = Disbursement.from_env(platform="legacy")
try:
    result = disbursement.get_transaction_status(args.reference)
except MomoAPIError as exc:
    if exc.code == "RESOURCE_NOT_FOUND":
        sys.exit(f"{args.reference} is unknown on {disbursement.base_url}. Was it created on the new platform?")
    raise

print(f"Status: {result.get('status')}")  # PENDING, SUCCESSFUL or FAILED
print(json.dumps(result, indent=2))
