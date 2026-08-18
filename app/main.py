from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from app import db
from app import llm


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

    agent_reply = await llm.get_reply(req.message)

    await db.pool.execute(
        "INSERT INTO messages (conversation_id, sender, message_text) VALUES ($1, 'agent', $2)", conversation_id, agent_reply
    )

    return {"conversation_id": conversation_id, "reply": agent_reply}