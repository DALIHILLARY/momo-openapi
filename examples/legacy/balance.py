"""Show an account balance on the legacy platform (proxy.momoapi.mtn.com).

Reads .env, where PRODUCT is COLLECTION, DISBURSEMENT or REMITTANCE:
- PRODUCT_PRIMARY_KEY
- PRODUCT_USER_ID and PRODUCT_API_SECRET: the old API user and API key
- MTN_ENVIRONMENT

    .venv/bin/python examples/legacy/balance.py               # collection
    .venv/bin/python examples/legacy/balance.py disbursement
"""

import argparse

from dotenv import load_dotenv

from momo_openapi import Collection, Disbursement, Remittance

load_dotenv()  # variables already set in the environment win over .env

CLIENTS = {"collection": Collection, "disbursement": Disbursement, "remittance": Remittance}

parser = argparse.ArgumentParser(description="Show a balance on the legacy platform.")
parser.add_argument("product", nargs="?", choices=CLIENTS, default="collection")
args = parser.parse_args()

client = CLIENTS[args.product].from_env(platform="legacy")

balance = client.get_balance()
print(f"{balance['availableBalance']} {balance['currency']} on {client.base_url}")
