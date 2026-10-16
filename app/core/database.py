from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import config

engine = create_async_engine(
    config.settings.database.async_connection_string,
    echo=False,
    future=True,
)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Get database session."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()