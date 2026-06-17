from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
import pytest_asyncio

from app.api.deps import get_current_user
from app.main import app


@pytest_asyncio.fixture
async def client_for_user():
    @asynccontextmanager
    async def _build(user):
        async def override_current_user():
            return user

        app.dependency_overrides[get_current_user] = override_current_user

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

    async with app.router.lifespan_context(app):
        yield _build

    app.dependency_overrides.clear()
