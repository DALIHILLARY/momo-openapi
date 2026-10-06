"""Show an account balance on the new platform (momoapi.momo.africa).

Reads .env, where PRODUCT is COLLECTION, DISBURSEMENT or REMITTANCE:
- PRODUCT_PRIMARY_KEY
- PRODUCT_NEW_USER_ID and PRODUCT_NEW_CREDENTIAL_TOKEN: System Credentials from the
  Partner Portal. After cutover, PRODUCT_USER_ID and PRODUCT_CREDENTIAL_TOKEN work too.
- MTN_ENVIRONMENT

    .venv/bin/python examples/new/balance.py               # collection
    .venv/bin/python examples/new/balance.py disbursement
"""

import argparse

from dotenv import load_dotenv

from momo_openapi import Collection, Disbursement, Remittance

load_dotenv()  # variables already set in the environment win over .env

CLIENTS = {"collection": Collection, "disbursement": Disbursement, "remittance": Remittance}

parser = argparse.ArgumentParser(description="Show a balance on the new platform.")
parser.add_argument("product", nargs="?", choices=CLIENTS, default="collection")
args = parser.parse_args()

client = CLIENTS[args.product].from_env(platform="new")

balance = client.get_balance()
print(f"{balance['availableBalance']} {balance['currency']} on {client.base_url}")
