# backend/app/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# 1. Engine — URL comes from settings (which reads DATABASE_URL from env)
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# 2. Session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 3. Base class shared by all models
Base = declarative_base()


# 4. Dependency — yields an async session per request
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session