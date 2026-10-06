"""Show the status of a payout made on the new platform (momoapi.momo.africa).

A status can only be read on the platform that created the transaction, so pass a
reference from examples/new/disburse.py. One from the legacy platform is not found here.

Reads .env:
- DISBURSEMENT_PRIMARY_KEY
- DISBURSEMENT_NEW_USER_ID and DISBURSEMENT_NEW_CREDENTIAL_TOKEN: System Credentials from the
  Partner Portal. After cutover, DISBURSEMENT_USER_ID and DISBURSEMENT_CREDENTIAL_TOKEN work too.
- MTN_ENVIRONMENT

    .venv/bin/python examples/new/disburse_status.py <reference>
"""

import argparse
import json
import sys

from dotenv import load_dotenv

from momo_openapi import Disbursement, MomoAPIError

load_dotenv()  # variables already set in the environment win over .env

parser = argparse.ArgumentParser(description="Show a payout's status on the new platform.")
parser.add_argument("reference", help="the reference printed by disburse.py")
args = parser.parse_args()

disbursement = Disbursement.from_env(platform="new")
try:
    result = disbursement.get_transaction_status(args.reference)
except MomoAPIError as exc:
    if exc.code == "RESOURCE_NOT_FOUND":
        sys.exit(f"{args.reference} is unknown on {disbursement.base_url}. Was it created on the legacy platform?")
    raise

print(f"Status: {result.get('status')}")  # PENDING, SUCCESSFUL or FAILED
print(json.dumps(result, indent=2))
