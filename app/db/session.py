from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import ssl

# Determine SSL configuration based on DATABASE_URL
connect_args = {
    "server_settings": {"search_path": "public"}
}

# If DATABASE_URL contains specific hosts (like render, neon, supabase, etc.), require SSL
if any(host in settings.DATABASE_URL.lower() for host in ['render.com', 'neon.tech', 'supabase.', 'railway.app', 'aws.', 'azure.', 'gcp.']):
    # For cloud databases, use SSL with default context
    connect_args["ssl"] = ssl.create_default_context()
else:
    # For local databases, disable SSL requirement
    connect_args["ssl"] = False

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    future=True,
    connect_args=connect_args
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