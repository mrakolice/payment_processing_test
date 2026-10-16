import asyncio
import contextlib
import time
from collections.abc import AsyncGenerator
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import brokers, database, models


@contextlib.asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession]:
    """Get database session."""
    async with database.async_session() as session:
        try:
            yield session
        finally:
            await session.close()

async def _get_events() -> list:
    async with get_db() as session:
        await session.execute(sa.select(models.Outbox))

    return [{'id':1}]

async def main():
    while True:
        events = await _get_events()
        for event in events:
            await brokers.rabbit_mq_broker.publish(
                message=event,
                queue=brokers.Queues.PAYMENTS_NEW,
            )
        time.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())