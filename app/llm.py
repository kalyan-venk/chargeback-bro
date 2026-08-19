from anthropic import AsyncAnthropicBedrock

from app import db, tools

client = AsyncAnthropicBedrock(aws_region="us-east-1")

SYSTEM_PROMPT = "Hey this is a bank. We are newly starting. This service aims to provide assistance to customers who wants to disupte a transaction." \
                "The main aim is to check the transaction for fraud score. If it is a confident fraud, we file a dispute and then tell the customer that" \
                "it is being taken care of and there is no need to worry. If it is a confident not-fraud, we tell the customer to contact the bank directly." \
                "If it is somewhere un-sure, we escalate it and pass it on to humans with a message on why we are unsure about it." \
                "Answer in short plain text, no markdown formatting, no emojis"

TOOLS = [{
    "name": "look_up_transactions",
    "description": "search this customer's transaction to find the charge they are asking about",
    "input_schema": {
        "type": "object",
        "properties": {
            "merchant_name": {"type": "string", "description": "the name of the merchant that the customer says they were charged at"},
            "amount": {"type": "number", "description": "how much the customer was charged"},
            "date": {"type": "string", "description": "when the transaction happened. It must be in YYYY-MM-DD form. Do not assume the date if the customer didn't tell."},
            "card_last4": {"type": "string", "description": "last 4 digits of the card number"}
        },
        "required": []
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
                        # print(block.name, block.input, block.id)
                        rows = await tools.look_up_transactions(db.pool, person_id, **block.input)

                        # print(rows)
                        history.append({"role": "assistant", "content": final.content})
                        history.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": block.id, "content": str([dict(r) for r in rows])}]})