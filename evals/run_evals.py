import asyncio
import json
import os

from httpx import ASGITransport, AsyncClient

import app.tools
from app import db
from app.main import app as chat_app

GOLDENS = os.path.join(os.path.dirname(__file__), "goldens")
SUPPORTED_CHECKS = {
    "dispute_row_count", "tools_that_must_run",
    "final_reply_contains", "final_reply_excludes_fraud_score",
    "tool_result_equals", "tools_that_must_not_run",
    "final_reply_equals", "dispute_escalation_reason_is_nonempty"
}
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
async def check_dispute_row_count(expected_count):
    result = await db.pool.fetchval(
        "SELECT COUNT(*) FROM disputes"
    )
    return result == expected_count

async def check_dispute_escalation_reason_is_nonempty(expected):
    reason = await db.pool.fetchval(
        "SELECT escalation_reason FROM disputes"
    )
    cleaned_reason = bool(reason and reason.strip())
    return cleaned_reason == expected

def check_final_reply_excludes_fraud_score(replies, fraud_score, expected):
    if not replies:
        return False

    final_reply = replies[-1]
    decimal_representation = str(fraud_score)
    percentage_representations = [f"{fraud_score:.2%}", f"{fraud_score:.1%}", f"{fraud_score:.0%}"]

    result = decimal_representation not in final_reply and all(
        percentage_representation not in final_reply
        for percentage_representation in percentage_representations
    )
    return result == expected

async def check_tool_result_equals(expected_results):
    rows = await db.pool.fetch(
        "SELECT tool_called, result FROM traces"
    )

    extracted_rows = {(r["tool_called"], r["result"]) for r in rows}
    for expected_result in expected_results.items():
        if expected_result not in extracted_rows:
            return False

    return True

async def check_tool_ran(list_of_required_tool_names):
    rows = await db.pool.fetch(
        "SELECT DISTINCT tool_called FROM traces"
    )
    result = {r["tool_called"] for r in rows}

    return result >= set(list_of_required_tool_names)

async def check_tool_did_not_run(forbidden_tool_names):
    rows = await db.pool.fetch(
        "SELECT DISTINCT tool_called FROM traces"
    )
    result = {r["tool_called"] for r in rows}

    return set(forbidden_tool_names).isdisjoint(result)

def check_final_reply_equals(replies, expected):
    return bool(replies) and replies[-1] == expected

def check_final_reply_contains(replies, required_phrases):
    if not replies:
        return False

    final_reply = replies[-1].casefold()
    for required_phrase in required_phrases:
        if required_phrase.casefold() not in final_reply:
            return False

    return True

def finish_evaluation(check_results):
    if not check_results:
        raise RuntimeError("No checks were run.")

    if not all(check_results):
        raise SystemExit("One or more checks failed.")

    print("All checks successful.")

# VALIDATE THE CHECK FUNCTIONS
def validate_checks(checks):
    provided_checks = set(checks)
    unknown_checks = provided_checks - SUPPORTED_CHECKS

    if unknown_checks:
        raise ValueError(f"Unknown checks present in the provided checks - {sorted(unknown_checks)}")

# THE RUN
async def main():
    global PINNED
    await db.connect()

    check_results = []
    for case in load_cases():
        validate_checks(case["checks"])
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
            response.raise_for_status()

        # Did it file the dispute?
        if "dispute_row_count" in case["checks"]:
            passed = await check_dispute_row_count(case["checks"]["dispute_row_count"])
            check_results.append(passed)
            print(case["name"] + " - Dispute row count: " + ("PASS" if passed else "FAIL"))

        # Did it call the tool it was supposed to?
        if "tools_that_must_run" in case["checks"]:
            passed = await check_tool_ran(case["checks"]["tools_that_must_run"])
            check_results.append(passed)
            print(case["name"] + " - Called the tool: " + ("PASS" if passed else "FAIL"))

        if "tools_that_must_not_run" in case["checks"]:
            passed = await check_tool_did_not_run(case["checks"]["tools_that_must_not_run"])
            check_results.append(passed)
            print(case["name"] + " - Avoided forbidden tools: " + ("PASS" if passed else "FAIL"))

        if "final_reply_equals" in case["checks"]:
            passed = check_final_reply_equals(replies, case["checks"]["final_reply_equals"])
            check_results.append(passed)
            print(case["name"] + " - Final reply matched: " + ("PASS" if passed else "FAIL"))

        if "final_reply_contains" in case["checks"]:
            passed = check_final_reply_contains(replies, case["checks"]["final_reply_contains"])
            check_results.append(passed)
            print(case["name"] + " - Final reply contains expected phrases: " + ("PASS" if passed else "FAIL"))

        if "dispute_escalation_reason_is_nonempty" in case["checks"]:
            passed = await check_dispute_escalation_reason_is_nonempty(case["checks"]["dispute_escalation_reason_is_nonempty"])
            check_results.append(passed)
            print(case["name"] + " - Escalation reason is nonempty: " + ("PASS" if passed else "FAIL"))

        if "final_reply_excludes_fraud_score" in case["checks"]:
            passed = check_final_reply_excludes_fraud_score(replies, case["pinned_score"], case["checks"]["final_reply_excludes_fraud_score"])
            check_results.append(passed)
            print(case["name"] + " - Final reply excludes fraud score: " + ("PASS" if passed else "FAIL"))

        if "tool_result_equals" in case["checks"]:
            passed = await check_tool_result_equals(case["checks"]["tool_result_equals"])
            check_results.append(passed)
            print(case["name"] + " - Tool result equals expected: " + ("PASS" if passed else "FAIL"))

    await db.disconnect()
    finish_evaluation(check_results)

if __name__ == "__main__":
    asyncio.run(main())
