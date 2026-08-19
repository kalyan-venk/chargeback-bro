import csv
import random
import asyncio, os, asyncpg

async def main():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])

    # with open("data/credit_card_transaction_train.csv") as data1:
    #     total_training_data = csv.DictReader(data1)

    with open("data/credit_card_transaction_test.csv") as data2:
        total_test_data = csv.DictReader(data2)

        people, merchants = {}, {}
        for row in total_test_data:
            if row["cc_num"] not in people:
                people[row["cc_num"]] = {"name": row["first"] + " " + row["last"],
                                         "address": row["street"] + ", " + row["city"] + ", " + row["state"] + ", " + row["zip"],
                                         "salary": int(random.uniform(30_000, 250_000))}

            if row["merchant"] not in merchants:
                merchants[row["merchant"]] = {row["merchant"].removeprefix("fraud_"): (float(row["merch_lat"]), float(row["merch_long"]))}

        print(len(people))
        print(len(merchants))

    await conn.close()

asyncio.run(main())