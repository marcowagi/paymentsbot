"""
Database setup and session management
"""

import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Create async engine
if "sqlite" in DATABASE_URL:
    # SQLite specific configuration
    engine = create_async_engine(
        DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )
else:
    # PostgreSQL configuration
    engine = create_async_engine(DATABASE_URL, echo=False)

# Create session maker
SessionMaker = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    """Initialize database and create tables"""
    from models import Base
    
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

async def get_session() -> AsyncSession:
    """Get database session"""
    async with SessionMaker() as session:
        yield session