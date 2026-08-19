from anthropic import AsyncAnthropicBedrock

client = AsyncAnthropicBedrock(aws_region="us-east-1")

SYSTEM_PROMPT = "Hey this is a bank. We are newly starting. This service aims to provide assistance to customers who wants to disupte a transaction." \
                "The main aim is to check the transaction for fraud score. If it is a confident fraud, we file a dispute and then tell the customer that" \
                "it is being taken care of and there is no need to worry. If it is a confident not-fraud, we tell the customer to contact the bank directly." \
                "If it is somewhere un-sure, we escalate it and pass it on to humans with a message on why we are unsure about it." \
                "Answer in short plain text, no markdown formatting, no emojis"

async def get_reply(user_message: str) -> str:
    response = await client.messages.create(model="us.anthropic.claude-haiku-4-5-20251001-v1:0", max_tokens=512,
                                            messages=[{"role": "user", "content": user_message}], system=SYSTEM_PROMPT)
    return response.content[0].text

async def stream_reply(history: str):
    async with client.messages.stream(model="us.anthropic.claude-haiku-4-5-20251001-v1:0", max_tokens=512,
                                            messages=history, system=SYSTEM_PROMPT) as stream:
        async for text in stream.text_stream:
            yield text