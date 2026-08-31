import app.tools
import json
import os
import asyncio
from app.main import app as chat_app

from app import db
from httpx import ASGITransport, AsyncClient

GOLDENS = os.path.join(os.path.dirname(__file__), "goldens")
PINNED = None

async def fake_score(conn, transaction_id):
    return PINNED

app.tools.score_fraud = fake_score

def load_cases():
    cases = []
    for name in sorted(os.listdir(GOLDENS)):

        if name.endswith(".json"):
            with open(os.path.join(GOLDENS, name)) as f:
                cases.append(json.load(f))
    return cases

async def reset_db(conn):
    await conn.execute(
        "TRUNCATE TABLE conversations, messages, disputes, traces RESTART IDENTITY CASCADE"
    )

async def check_dispute_row_exists(expected):
    result = await db.pool.fetchval(
        "SELECT EXISTS (SELECT 1 FROM disputes)"
    )
    return result == expected

async def main():
    global PINNED
    await db.connect()

    for case in load_cases():
        PINNED = case["pinned_score"]

        await reset_db(db.pool)

        async with AsyncClient(transport=ASGITransport(app=chat_app), base_url="http://test") as client:
            response = await client.post("/chat", json={"message": case["messages"][0]})
            print(response.text)
            assert response.status_code == 200

        if "dispute_row_exists" in case["checks"]:
            passed = await check_dispute_row_exists(case["checks"]["dispute_row_exists"])
            print(case["name"] + (" PASS" if passed else " FAIL"))

    await db.disconnect()

asyncio.run(main())