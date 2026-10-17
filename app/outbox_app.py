import asyncio
import datetime
import logging

import sqlmodel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import brokers
from app.core.database import async_session
from app.core.models.payments import Outbox

logger = logging.getLogger(__name__)

POLL_INTERVAL = 1
BATCH_SIZE = 100


async def _get_events(session: AsyncSession) -> list[Outbox]:
    statement = (
        sqlmodel.select(Outbox)
        .where(Outbox.published_at.is_(None))
        .with_for_update(skip_locked=True)
        .order_by(Outbox.created_at)
        .limit(BATCH_SIZE)
    )
    result = await session.execute(statement)
    return list(result.scalars().all())


async def _publish_event(session: AsyncSession, event: Outbox) -> None:
    await brokers.rabbit_mq_broker.publish(
        message=event.payload,
        queue=brokers.Queues.PAYMENTS_NEW,
    )
    event.published_at = datetime.datetime.now()
    session.add(event)
    await session.commit()


async def main() -> None:
    async with brokers.rabbit_mq_broker:
        while True:
            async with async_session() as session:
                events = await _get_events(session)
                for event in events:
                    try:
                        await _publish_event(session, event)
                    except Exception:
                        logger.exception('Failed to publish outbox event %s', event.id)

            await asyncio.sleep(POLL_INTERVAL)


if __name__ == '__main__':
    asyncio.run(main())
