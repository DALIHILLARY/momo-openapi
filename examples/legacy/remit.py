"""Send a remittance to a MoMo wallet on the legacy platform (proxy.momoapi.mtn.com).

Sends money from your remittance account to the wallet.

Reads .env:
- REMITTANCE_PRIMARY_KEY
- REMITTANCE_USER_ID and REMITTANCE_API_SECRET: the old API user and API key
- MTN_ENVIRONMENT, CURRENCY and, if set, CALLBACK_URL
- MOMO_TEST_PHONE, if set, as the default --phone

    .venv/bin/python examples/legacy/remit.py 500 --phone 256772123456 --ref remit-42

This moves real money, so use a small amount.
"""

import argparse
import os
import uuid

from dotenv import load_dotenv

from momo_openapi import Remittance

load_dotenv()  # variables already set in the environment win over .env

parser = argparse.ArgumentParser(description="Send a remittance to a MoMo wallet on the legacy platform.")
parser.add_argument("amount", help="in CURRENCY, e.g. 500")
parser.add_argument(
    "--phone",
    default=os.environ.get("MOMO_TEST_PHONE"),
    help="MSISDN in international format, e.g. 256772123456 (default: $MOMO_TEST_PHONE)",
)
parser.add_argument("--ref", default=f"remit-{uuid.uuid4().hex[:8]}", help="your external ID")
args = parser.parse_args()
if not args.phone:
    parser.error("--phone is required when MOMO_TEST_PHONE is not set")

remittance = Remittance.from_env(platform="legacy")
reference = remittance.transfer(
    args.amount,
    args.phone,
    external_id=args.ref,
    payer_message=f"Remittance {args.ref}",
    payee_note=args.ref,
)

# MoMo accepted the request (HTTP 202); the outcome comes later. Store the reference:
# its status can only be read on the legacy platform.
print(f"Accepted on {remittance.base_url}, reference {reference}")
print(f"Check it with: .venv/bin/python examples/legacy/remit_status.py {reference}")
