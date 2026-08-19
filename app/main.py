import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from app import db, llm
from fastapi.responses import StreamingResponse


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health():
    return {"status":"okay"}

@app.post("/chat")
async def chat(req: ChatRequest):
    if req.conversation_id is None:
        row = await db.pool.fetchrow(
            "INSERT INTO conversations (person_id) VALUES ($1) RETURNING conversation_id", 1 #TODO Auth
        )
        conversation_id = row["conversation_id"]
    else:
        conversation_id = req.conversation_id

    await db.pool.execute(
        "INSERT INTO messages (conversation_id, sender, message_text) VALUES ($1, 'customer', $2)", conversation_id, req.message
    )

    # Adding multiple messages context
    rows = await db.pool.fetch(
        "SELECT sender, message_text FROM messages WHERE conversation_id = $1 ORDER BY message_id", conversation_id
    )

    history = []
    for row in rows:
        if row["sender"] == 'customer':
            history.append({"role": "user", "content": row["message_text"]})
        else:
            history.append({"role": "assistant", "content": row["message_text"]})

    # Streaming function definition
    async def event_stream():
        full_reply = ""
        yield "data: " + json.dumps({"conversation_id": conversation_id}) + "\n\n"

        async for piece in llm.stream_reply(history):
            full_reply += piece
            yield "data: " + json.dumps({"text": piece}) + "\n\n"

        await db.pool.execute(
            "INSERT INTO messages (conversation_id, sender, message_text) VALUES ($1, 'agent', $2)", conversation_id, full_reply
        )

    # Older non-streaming version
    # agent_reply = await llm.get_reply(req.message)
    #
    # await db.pool.execute(
    #     "INSERT INTO messages (conversation_id, sender, message_text) VALUES ($1, 'agent', $2)", conversation_id, agent_reply
    # )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
    # Older non-streaming version
    # return {"conversation_id": conversation_id, "reply": agent_reply}