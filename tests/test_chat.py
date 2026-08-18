import pytest
from httpx import ASGITransport, AsyncClient

from app import db
from app.main import app


@pytest.mark.asyncio
async def test_chat():
    await db.connect()
    await db.pool.execute("TRUNCATE cardholders, conversations, messages RESTART IDENTITY CASCADE")
    await db.pool.execute("INSERT INTO cardholders (person_name, address, annual_salary) VALUES ($1, 'test_address', $2)", "Test Wayne", 200_000)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/chat", json={"message": "my card was charged twice"})
        row = await db.pool.fetchrow(
            "SELECT * FROM messages LIMIT 1"
        )
        assert response.status_code == 200
        assert row["message_text"] == "my card was charged twice" and row["sender"] == 'customer'

    await db.disconnect()