"""Полная интеграция consumer'а с реальным RabbitMQ: защита от дублей и DLQ
после 3 попыток.
Медленный (TTL retry-очереди = 5с * 3 попытки) — запускается
отдельно: `make tests test_dir=app/tests/test_consumer_integration.py`.
"""
import asyncio
import decimal

import aio_pika
import pytest
import sqlalchemy as sa

import app.consumer_app as consumer_app
from app.core import brokers, config, enums
from app.core.models import Payment

pytestmark = pytest.mark.slow


async def _queue_message_count(queue_name: str) -> int:
    connection = await aio_pika.connect_robust(config.settings.rabbitmq.connection_string)
    try:
        channel = await connection.channel()
        queue = await channel.declare_queue(queue_name, passive=True)
        return queue.declaration_result.message_count
    finally:
        await connection.close()


async def test_duplicate_skip_and_dlq_after_max_retries(db_session, clean_queues):
    payment = Payment(
        amount=decimal.Decimal('1'),
        currency=enums.Currency.RUB,
        webhook_url='http://127.0.0.1:1/unreachable',
        idempotency_key='integration-dup',
        status=enums.PaymentStatus.SUCCEEDED,
    )
    db_session.add(payment)
    await db_session.commit()
    payment_id = payment.id

    task = asyncio.create_task(consumer_app.app.run())
    await asyncio.sleep(1.0)

    try:
        # защита от дублей: сообщение по уже обработанному платежу
        await brokers.rabbit_mq_broker.publish({'id': payment_id}, queue=brokers.Queues.PAYMENTS_NEW.value)
        await asyncio.sleep(1.5)

        refreshed = (await db_session.execute(
            sa.select(Payment).where(Payment.id == payment_id)
        )).scalar_one()
        assert refreshed.processed_at is None  # обработчик вышел рано, не трогая платёж

        # DLQ: несуществующий payment_id, 3 неудачные попытки -> DLQ
        await brokers.rabbit_mq_broker.publish({'id': -1}, queue=brokers.Queues.PAYMENTS_NEW.value)

        deadline = brokers.MAX_PAYMENT_RETRIES * (brokers.RETRY_TTL_MS / 1000) + 10
        message_count = 0
        elapsed = 0.0
        while elapsed < deadline:
            message_count = await _queue_message_count(brokers.Queues.PAYMENTS_NEW_DLQ.value)
            if message_count >= 1:
                break
            await asyncio.sleep(1.0)
            elapsed += 1.0

        assert message_count == 1
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
