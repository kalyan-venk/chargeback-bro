from anthropic import AsyncAnthropicBedrock

from app import db, tools

client = AsyncAnthropicBedrock(aws_region="us-east-1")

SYSTEM_PROMPT = """You are the dispute assistant for ChargeBack bank. You help customers dispute card transactions.

  Follow this exact flow every time:
  1. Find the charge with look_up_transactions using only details the customer gave. Never assume dates or amounts.
  2. When the transaction is found, call score_fraud with its transaction_id.
  3. Act on the score:
     - Below 0.33: do not file anything. Tell the customer to contact Chargeback Customer Care for help with this exact sentence and nothing else - "Sorry, I regret to say I can't help you with this. Please contact customer care."
     - Between 0.33 and 0.67: you MUST call file_dispute with transaction_id, claim_reason, and escalation_reason explaining why it is unclear. Do
  this BEFORE replying to the customer.
     - Above 0.67: you MUST call file_dispute with transaction_id and claim_reason. Do this BEFORE replying to the customer.
  4. Never tell the customer something was done unless you actually called the tool and saw its result. Describe only what the tool result says
  happened.
  
  Never reveal the raw fraud score to the customer. Answer in short plain text, no markdown, no emojis."""

TOOLS = [
    {"name": "look_up_transactions",
    "description": "search this customer's transaction to find the charge they are asking about",
    "input_schema": {
        "type": "object",
        "properties": {
            "merchant_name": {"type": "string", "description": "the name of the merchant that the customer says they were charged at."},
            "amount": {"type": "number", "description": "how much the customer was charged"},
            "date": {"type": "string", "description": "when the transaction happened. It must be in YYYY-MM-DD form. Do not assume the date if the customer didn't tell."},
            "card_last4": {"type": "string", "description": "last 4 digits of the card number"}
        },
        "required": []
    }
},

    {"name": "score_fraud",
    "description": "score this transaction for the chances of it being a fraud",
    "input_schema": {
        "type": "object",
        "properties": {
            "transaction_id": {"type": "number", "description": "the id of the transaction that we are concerned about here."}
        },
        "required": ["transaction_id"]
    }
},

    {"name": "file_dispute",
    "description": "dispute the transaction by adding an entry in the disputes table of the database",
    "input_schema": {
        "type": "object",
        "properties": {
            "transaction_id": {"type": "number", "description": "the id of the transaction that we are concerned about here."},
            "claim_reason": {"type": "string", "description": "the reason why this client is claiming this transaction as fraud."},
            "escalation_reason": {"type": "string", "description": "the reason why we couldn't get this transaction checked by ourselves and why are we unsure."}
        },
        "required": ["transaction_id", "claim_reason"]
    }
}]

async def get_reply(user_message: str) -> str:
    response = await client.messages.create(model="us.anthropic.claude-haiku-4-5-20251001-v1:0", max_tokens=512,
                                            messages=[{"role": "user", "content": user_message}], system=SYSTEM_PROMPT)
    return response.content[0].text

async def stream_reply(history: str, person_id: int):
    while True:
        async with client.messages.stream(model="us.anthropic.claude-haiku-4-5-20251001-v1:0", max_tokens=512,
                                                messages=history, system=SYSTEM_PROMPT, tools=TOOLS) as stream:
            async for text in stream.text_stream:
                yield text

            final = await stream.get_final_message()
            print(final.stop_reason)

            if final.stop_reason != "tool_use":
                break
            else:
                for block in final.content:
                    if block.type == "tool_use":
                        if block.name == "look_up_transactions":
                            # print(block.name, block.input, block.id)
                            rows = await tools.look_up_transactions(db.pool, person_id, **block.input)
                            result = str([dict(r) for r in rows])

                        elif block.name == "score_fraud":
                            # Score Fraud
                            score = await tools.score_fraud(db.pool, **block.input)
                            result = str(score)

                        elif block.name == "file_dispute":
                            # Filing the dispute
                            dispute = await tools.file_dispute(db.pool, person_id, **block.input)
                            result = dispute

                        # print(rows)
                        history.append({"role": "assistant", "content": final.content})
                        history.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": block.id, "content": result}]})
