"""Pay out to a MoMo wallet on the new platform (momoapi.momo.africa).

Sends money from your disbursement account to the wallet.

Reads .env:
- DISBURSEMENT_PRIMARY_KEY
- DISBURSEMENT_NEW_USER_ID and DISBURSEMENT_NEW_CREDENTIAL_TOKEN: System Credentials from the
  Partner Portal. After cutover, DISBURSEMENT_USER_ID and DISBURSEMENT_CREDENTIAL_TOKEN work too.
- MTN_ENVIRONMENT, CURRENCY and, if set, CALLBACK_URL
- MOMO_TEST_PHONE, if set, as the default --phone

    .venv/bin/python examples/new/disburse.py 500 --phone 256772123456 --ref payout-42

This moves real money, so use a small amount.
"""

import argparse
import os
import uuid

from dotenv import load_dotenv

from momo_openapi import Disbursement

load_dotenv()  # variables already set in the environment win over .env

parser = argparse.ArgumentParser(description="Pay out to a MoMo wallet on the new platform.")
parser.add_argument("amount", help="in CURRENCY, e.g. 500")
parser.add_argument(
    "--phone",
    default=os.environ.get("MOMO_TEST_PHONE"),
    help="MSISDN in international format, e.g. 256772123456 (default: $MOMO_TEST_PHONE)",
)
parser.add_argument("--ref", default=f"payout-{uuid.uuid4().hex[:8]}", help="your external ID")
args = parser.parse_args()
if not args.phone:
    parser.error("--phone is required when MOMO_TEST_PHONE is not set")

disbursement = Disbursement.from_env(platform="new")
reference = disbursement.transfer(
    args.amount,
    args.phone,
    external_id=args.ref,
    payer_message=f"Payout {args.ref}",
    payee_note=args.ref,
)

# MoMo accepted the request (HTTP 202); the outcome comes later. Store the reference:
# its status can only be read on the new platform.
print(f"Accepted on {disbursement.base_url}, reference {reference}")
print(f"Check it with: .venv/bin/python examples/new/disburse_status.py {reference}")
