# backend/app/database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. The URL based on your Docker Compose credentials
DATABASE_URL = "postgresql+asyncpg://admin:admin@localhost:5432/postgres"

# 2. Create the Database Engine (The main connection point)
# echo=True will print all SQL queries to your terminal (great for debugging!)
engine = create_async_engine(DATABASE_URL, echo=True)

# 3. Create a Session Factory (This hands out connections when your API needs them)
AsyncSessionLocal = sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# 4. Create the Base Class (Your future database tables will inherit from this)
Base = declarative_base()

# 5. Dependency function to use in your FastAPI routes
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session