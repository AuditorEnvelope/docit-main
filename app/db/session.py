from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import os

# Parse DATABASE_URL to check if it's Neon (has pooler or neon.tech)
database_url = settings.DATABASE_URL
is_neon = "neon.tech" in database_url or "pooler" in database_url

# Keep pooler endpoint - it works! The issue is SSL configuration, not the endpoint
# Pooler endpoint works fine (as proven by psql/DBeaver)
# We just need the right SSL settings for asyncpg
if is_neon and "pooler" in database_url:
    print("📡 Using pooler endpoint (verified working with psql)")

# Configure connection args for Neon
connect_args = {
    "server_settings": {"search_path": "public"}
}

# Add SSL for Neon databases
if is_neon:
    # For Neon, asyncpg works best with ssl=True (boolean)
    # SSL context objects can cause hanging/timeout issues
    # This is the recommended approach per asyncpg docs for Neon
    connect_args["ssl"] = True
    
    # Increase timeout for Neon (it can be idle and needs time to wake up)
    connect_args["command_timeout"] = 30
    connect_args["timeout"] = 30  # Connection timeout in seconds
    connect_args["server_settings"]["application_name"] = "pustak_ai"
    
    print(f"🔐 SSL configured for Neon (ssl=True)")
    print(f"⏱️  Connection timeout: 30s")

# Create async engine with proper pool settings
engine = create_async_engine(
    database_url,
    echo=settings.DATABASE_ECHO,
    future=True,
    connect_args=connect_args,
    # Pool settings for better connection handling
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using (important for Neon)
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_timeout=30,  # Wait up to 30 seconds for a connection
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def get_db() -> AsyncSession:
    """Dependency for getting async DB session"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def get_async_session():
    """Get async DB session for background tasks (generator for dependency injection)"""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_session() -> AsyncSession:
    """Get a new async session for background tasks (not a generator)"""
    session = async_session()
    return session