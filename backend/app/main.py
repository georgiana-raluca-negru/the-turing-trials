# backend/app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends          
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession 
from app.database import get_db, engine

# This runs exactly once when the server starts up
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # Try to connect and run a simple "SELECT 1" query
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ DATABASE CONNECTED SUCCESSFULLY!")
    except Exception as e:
        print(f"❌ DATABASE CONNECTION FAILED: {e}")
    
    yield # The server runs here
    
    # This runs when the server shuts down
    await engine.dispose()

# Initialize FastAPI with the lifespan
app = FastAPI(lifespan=lifespan)

# Your existing CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://cine406.go.ro:3001",
        "http://localhost:3001",      # for local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello World! The Turing Trials backend is live."}


@app.get("/api/system-check")
async def system_check(db: AsyncSession = Depends(get_db)):
    try:
        # Ask the database a simple question to see if it's awake
        await db.execute(text("SELECT 1"))
        db_status = "Connected 🟢"
    except Exception as e:
        db_status = f"Offline 🔴 ({str(e)})"

    return {
        "message": "Hello World! The Turing Trials is online.",
        "backend_status": "Active 🟢",
        "database_status": db_status
    }