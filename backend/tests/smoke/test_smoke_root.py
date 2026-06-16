from __future__ import annotations

import httpx
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.smoke]

async def test_root_route_smoke(unauthenticated_client: httpx.AsyncClient):
    response = await unauthenticated_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "The Turing Trials backend is live."}
