import datetime

import sqlalchemy as sa

from app.core import brokers
from app.core.models import Outbox
from app.outbox_app import _get_events, _publish_event


async def test_get_events_returns_only_unpublished_ordered_by_created_at(db_session):
    old = Outbox(payload={'id': 1}, created_at=datetime.datetime.now() - datetime.timedelta(seconds=10))
    new = Outbox(payload={'id': 2}, created_at=datetime.datetime.now())
    already_published = Outbox(payload={'id': 3}, published_at=datetime.datetime.now())
    db_session.add_all([old, new, already_published])
    await db_session.commit()

    events = await _get_events(db_session)

    assert [e.payload['id'] for e in events] == [1, 2]


async def test_publish_event_marks_published_and_sends_to_broker(db_session, clean_queues):
    event = Outbox(payload={'id': 123})
    db_session.add(event)
    await db_session.commit()

    async with brokers.rabbit_mq_broker:
        await _publish_event(db_session, event)

    assert event.published_at is not None

    refreshed = (await db_session.execute(
        sa.select(Outbox).where(Outbox.id == event.id)
    )).scalar_one()
    assert refreshed.published_at is not None

    async with brokers.rabbit_mq_broker:
        queue = await brokers.rabbit_mq_broker.declare_queue(brokers.payments_new_queue)
        assert queue.declaration_result.message_count == 1
