# backend/app/main.py

import os
import sys

# Make llm_functionality packages importable (ai_engine, backend_integration)
# This is needed for local development; in Docker, PYTHONPATH is set in the Dockerfile.
_LLM_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "llm_functionality")
if _LLM_DIR not in sys.path:
    sys.path.insert(0, _LLM_DIR)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, engine, Base
from app.core.config import settings

# Import all models so Base.metadata is fully populated before create_all()
import app.models  # noqa: F401

# Import all routers
from app.api import auth, users, matches, evidence, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(text("SELECT 1"))
        print("✅ DATABASE CONNECTED & TABLES CREATED SUCCESSFULLY!")
    except Exception as e:
        print(f"❌ DATABASE STARTUP FAILED: {e}")

    yield  # ← server runs here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await engine.dispose()


app = FastAPI(
    title="The Turing Trials API",
    description=(
        "Multi-agent LLM courtroom simulation backend.\n\n"
        "**Auth:** Use `POST /api/auth/login` to get a JWT, then click "
        "**Authorize** and paste the `access_token` as `Bearer <token>`."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://the-turing-trials.games",
        "http://www.the-turing-trials.games",
        "https://the-turing-trials.games",
        "https://www.the-turing-trials.games",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(matches.router)
app.include_router(evidence.router)
app.include_router(sessions.router)


# ── Health / system check ─────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def read_root():
    return {"message": "The Turing Trials backend is live."}


@app.get("/api/system-check", tags=["Health"])
async def system_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "Connected 🟢"
    except Exception as e:
        db_status = f"Offline 🔴 ({str(e)})"

    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "backend_status": "Active 🟢",
        "database_status": db_status,
    }