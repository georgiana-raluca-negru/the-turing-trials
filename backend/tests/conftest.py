from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
LLM_ROOT = BACKEND_ROOT / "llm_functionality"

for path in (BACKEND_ROOT, LLM_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")

from app.api.deps import get_current_user
from app.database import AsyncSessionLocal, Base, engine
from app.main import app
from app.services.game_store import game_store
from app.core.security import hash_password
import backend_integration.services.lifecycle as lifecycle
from tests.factories import build_user
from tests.fakes import ScriptedAIRunner

TRUNCATE_SQL = text(
    "TRUNCATE TABLE rounds, evidence, game_sessions, matches, users RESTART IDENTITY CASCADE"
)


@pytest.fixture
def fake_ai_runner() -> ScriptedAIRunner:
    return ScriptedAIRunner()


@pytest.fixture(autouse=True)
def patch_default_ai_runner(monkeypatch: pytest.MonkeyPatch, fake_ai_runner: ScriptedAIRunner) -> None:
    monkeypatch.setattr(lifecycle, "_get_default_ai_runner", lambda: fake_ai_runner)


@pytest.fixture(autouse=True)
def clear_game_store() -> None:
    with game_store._lock:
        game_store._states.clear()
    yield
    with game_store._lock:
        game_store._states.clear()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def ensure_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture
async def db_session(ensure_schema) -> AsyncSessionLocal:
    async with engine.begin() as conn:
        await conn.execute(TRUNCATE_SQL)

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.execute(TRUNCATE_SQL)


@pytest_asyncio.fixture
async def persisted_user(db_session):
    user = build_user(hashed_password=hash_password("test-password"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_user(db_session):
    user = build_user(hashed_password=hash_password("test-password"))
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def async_client(persisted_user):
    async def override_current_user():
        return persisted_user

    app.dependency_overrides[get_current_user] = override_current_user

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client

    app.dependency_overrides.clear()
