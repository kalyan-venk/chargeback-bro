import asyncio
import csv
import os
import random
from datetime import datetime
from decimal import Decimal

import asyncpg

provider_options = ["Visa", "Mastercard", "AMEX", "Discover"]

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])

    await conn.execute(
        "TRUNCATE cardholders, merchants RESTART IDENTITY CASCADE"
    )

    with open("data/credit_card_transaction_test.csv") as data2:
        total_test_data = csv.DictReader(data2)

        people, merchants = {}, {}
        for row in total_test_data:
            if row["cc_num"] not in people:
                people[row["cc_num"]] = {"name": row["first"] + " " + row["last"],
                                         "address": row["street"] + ", " + row["city"] + ", " + row["state"] + ", " + row["zip"],
                                         "salary": int(random.uniform(30_000, 250_000)), "provider": random.choice(provider_options)}

            if row["merchant"].removeprefix("fraud_") not in merchants:
                merchants[row["merchant"].removeprefix("fraud_")] =\
                    {"merchant_lat": float(row["merch_lat"]), "merchant_long": float(row["merch_long"])}

        print(len(people))
        print(len(merchants))

    for person in people.values():
        id_made_for_person = await conn.fetchrow(
            "INSERT INTO cardholders (person_name, address, annual_salary) VALUES ($1, $2, $3) RETURNING person_id",
            person["name"], person["address"], person["salary"]
        )
        person["id_made_for_person"] = id_made_for_person["person_id"]

    for merchant_name, merchant_pos in merchants.items():
        id_made_for_merchant = await conn.fetchrow(
            "INSERT INTO merchants (merchant_name, merchant_latitude, merchant_longitude) VALUES ($1, $2, $3) RETURNING merchant_id",
            merchant_name, merchant_pos["merchant_lat"], merchant_pos["merchant_long"]
        )
        merchant_pos["id_made_for_merchant"] = id_made_for_merchant["merchant_id"]

    for card_no, person in people.items():
        id_made_for_card = await conn.fetchrow(
            "INSERT INTO cards (person_id, card_no_last4, provider) VALUES ($1, $2, $3) RETURNING card_id",
            person["id_made_for_person"], card_no[-4:], person["provider"]
        )
        person["id_made_for_card"] = id_made_for_card["card_id"]

    with open("data/credit_card_transaction_test.csv") as f:
        simple_rows = csv.DictReader(f)

        db_ready_rows = []
        for row in simple_rows:
            db_ready_rows.append([people[row["cc_num"]]["id_made_for_card"],
                                  merchants[row["merchant"].removeprefix("fraud_")]["id_made_for_merchant"],
                                  Decimal(row["amt"]), datetime.strptime(row["trans_date_trans_time"], "%Y-%m-%d %H:%M:%S"), row["category"], row["is_fraud"] == "1"])

        await conn.executemany(
            "INSERT INTO transactions (card_id, merchant_id, transaction_amount, transaction_time, category, is_fraud)"
            "VALUES ($1, $2, $3, $4, $5, $6)", db_ready_rows
        )

    await conn.close()

asyncio.run(main())