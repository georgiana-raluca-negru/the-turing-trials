# backend/app/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Look for the Docker environment variable FIRST. 
# If it's not found (like when running locally without Docker), fallback to localhost.
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://admin:admin@localhost:5432/postgres"
)

# 2. Create the Database Engine
engine = create_async_engine(DATABASE_URL, echo=True)

# 3. Create a Session Factory
AsyncSessionLocal = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 4. Create the Base Class
Base = declarative_base()

# 5. Dependency function
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session