"""Request a payment from a customer on the new platform (momoapi.momo.africa).

The customer gets a prompt on their phone to approve the debit.

Reads .env:
- COLLECTION_PRIMARY_KEY
- COLLECTION_NEW_USER_ID and COLLECTION_NEW_CREDENTIAL_TOKEN: System Credentials from the
  Partner Portal. After cutover, COLLECTION_USER_ID and COLLECTION_CREDENTIAL_TOKEN work too.
- MTN_ENVIRONMENT, CURRENCY and, if set, CALLBACK_URL
- MOMO_TEST_PHONE, if set, as the default --phone

    .venv/bin/python examples/new/collect.py 500 --phone 256772123456 --ref order-42

This moves real money, so use a small amount.
"""

import argparse
import os
import uuid

from dotenv import load_dotenv

from momo_openapi import Collection

load_dotenv()  # variables already set in the environment win over .env

parser = argparse.ArgumentParser(description="Request a payment from a customer on the new platform.")
parser.add_argument("amount", help="in CURRENCY, e.g. 500")
parser.add_argument(
    "--phone",
    default=os.environ.get("MOMO_TEST_PHONE"),
    help="MSISDN in international format, e.g. 256772123456 (default: $MOMO_TEST_PHONE)",
)
parser.add_argument("--ref", default=f"order-{uuid.uuid4().hex[:8]}", help="your external ID")
args = parser.parse_args()
if not args.phone:
    parser.error("--phone is required when MOMO_TEST_PHONE is not set")

collection = Collection.from_env(platform="new")
reference = collection.request_to_pay(
    args.amount,
    args.phone,
    external_id=args.ref,
    payer_message=f"Payment {args.ref}",
    payee_note=args.ref,
)

# MoMo accepted the request (HTTP 202); the outcome comes later. Store the reference:
# its status can only be read on the new platform.
print(f"Accepted on {collection.base_url}, reference {reference}")
print(f"Check it with: .venv/bin/python examples/new/collect_status.py {reference}")
