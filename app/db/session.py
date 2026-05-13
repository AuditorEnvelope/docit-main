from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create async engine
# pool_pre_ping: verify connections are alive before using them (prevents
#   "connection is closed" errors after long-running tasks like doc generation)
# pool_recycle: recycle connections after 5 minutes (Neon/serverless PG may
#   close idle connections after ~5 min)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    future=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "server_settings": {"search_path": "public"}
    }
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
