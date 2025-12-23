"""
Database configuration for Organizational Design Workbench.
Supports async SQLAlchemy with SQLite (development) or PostgreSQL (production).
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool, StaticPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./orgdesign.db")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Configure engine based on database type
engine_kwargs = {
    "echo": ENVIRONMENT == "development",
}

# SQLite requires special handling for async
if "sqlite" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine_kwargs["poolclass"] = StaticPool
else:
    engine_kwargs["poolclass"] = NullPool

# Create async engine
engine = create_async_engine(DATABASE_URL, **engine_kwargs)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for all models
Base = declarative_base()


async def get_session() -> AsyncSession:
    """
    Dependency for FastAPI to get database session.
    Usage:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables. Call on application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections. Call on application shutdown."""
    await engine.dispose()
