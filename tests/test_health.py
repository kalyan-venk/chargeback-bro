import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app, health


def test_health():
    assert health() == {"status":"okay"}

@pytest.mark.asyncio
async def test_health_http():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200 and response.json() == {"status":"okay"}