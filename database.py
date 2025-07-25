import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()


DB_URL = os.getenv("DB_NEON_URL")

if not DB_URL:
    raise ValueError("DB URL not set. Check .env.")

#to help with debugging db

engine = create_async_engine(DB_URL, echo=True)

#creating sessions for db interactions

AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

#fastapi dependency to inject sessions ito route fcns

async def get_db():
    """
    this fcn creates a session and closes auto after the req is processed
    """
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

#fcn for creating tables based on sqlalchelmy mdoels
async def create_db_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


