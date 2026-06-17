from __future__ import annotations

import httpx
import pytest

pytestmark = [pytest.mark.asyncio, pytest.mark.smoke]

async def test_protected_route_rejects_missing_auth(unauthenticated_client: httpx.AsyncClient):
    response = await unauthenticated_client.get("/api/matches/")

    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"
