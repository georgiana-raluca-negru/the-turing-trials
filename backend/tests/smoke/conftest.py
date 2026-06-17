from __future__ import annotations

import httpx
import pytest_asyncio

from app.main import app

@pytest_asyncio.fixture
async def unauthenticated_client(db_session):
    app.dependency_overrides.clear()

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

    app.dependency_overrides.clear()
