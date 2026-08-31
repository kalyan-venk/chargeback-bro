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

# CHECK FUNCTIONS
async def check_dispute_row_exists(expected):
    result = await db.pool.fetchval(
        "SELECT EXISTS (SELECT 1 FROM disputes)"
    )
    return result == expected

async def check_tool_ran(list_of_required_tool_names):
    rows = await db.pool.fetch(
        "SELECT DISTINCT tool_called FROM traces"
    )
    result = {r["tool_called"] for r in rows}

    return result >= set(list_of_required_tool_names)

# THE RUN
async def main():
    global PINNED
    await db.connect()

    for case in load_cases():
        PINNED = case["pinned_score"]

        await reset_db(db.pool)

        async with AsyncClient(transport=ASGITransport(app=chat_app), base_url="http://test") as client:
            conversation_id = None
            replies = []
            for i in range(len(case["messages"])):
                response = await client.post("/chat", json={"conversation_id": conversation_id, "message": case["messages"][i]})
                extracted_response = response.text.splitlines()
                extracted_response = [ex for ex in extracted_response if ex!='']
                extracted_response = [ex.removeprefix("data: ") for ex in extracted_response]
                extracted_response = [json.loads(ex) for ex in extracted_response]

                conversation_id = extracted_response[0]["conversation_id"]
                message = ""
                for part in extracted_response:
                    if "text" in part:
                        message += part['text']
                replies.append(message)

            print(response.text)
            assert response.status_code == 200

        # Did it file the dispute?
        if "dispute_row_exists" in case["checks"]:
            passed = await check_dispute_row_exists(case["checks"]["dispute_row_exists"])
            print(case["name"] + " - Filed the dispute?: " + ("PASS" if passed else "FAIL"))

        # Did it call the tool it was supposed to?
        if "tools_that_must_run" in case["checks"]:
            passed = await check_tool_ran(case["checks"]["tools_that_must_run"])
            print(case["name"] + " - Called the tool?: " + ("PASS" if passed else "FAIL"))

    await db.disconnect()

asyncio.run(main())