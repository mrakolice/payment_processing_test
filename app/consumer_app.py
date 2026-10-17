import asyncio
import datetime
import logging
import random

import faststream
import httpx
from faststream.rabbit.annotations import RabbitMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import brokers, enums
from app.core.database import get_db
from app.core.models import Payment

logger = logging.getLogger(__name__)

app = faststream.FastStream(brokers.rabbit_mq_broker)

WEBHOOK_RETRIES = 3
WEBHOOK_BASE_DELAY = 1.0
WEBHOOK_MAX_DELAY = 5.0


@app.after_startup
async def _declare_retry_topology() -> None:
    # Основную очередь объявляет subscriber ниже; retry/DLQ отдельно, так как
    # на них никто не подписан напрямую — только дедлеттеринг и ручная публикация.
    await brokers.rabbit_mq_broker.declare_queue(brokers.payments_new_retry_queue)
    await brokers.rabbit_mq_broker.declare_queue(brokers.payments_new_dlq_queue)


def _retry_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    cap = min(max_delay, base_delay * (2 ** attempt))
    return random.uniform(0, cap)


async def _send_webhook(payment: Payment) -> None:
    async with httpx.AsyncClient() as client:
        for attempt in range(WEBHOOK_RETRIES):
            try:
                response = await client.post(
                    payment.webhook_url,
                    json=payment.model_dump(mode='json'),
                )
                response.raise_for_status()
                return
            except httpx.HTTPError:
                if attempt == WEBHOOK_RETRIES - 1:
                    raise
                await asyncio.sleep(_retry_delay(attempt, WEBHOOK_BASE_DELAY, WEBHOOK_MAX_DELAY))


async def _process_payment(payment: Payment, session: AsyncSession) -> None:
    await asyncio.sleep(random.uniform(2, 5))

    succeeded = random.random() < 0.9  # 90% успех, 10% ошибка
    payment.status = enums.PaymentStatus.SUCCEEDED if succeeded else enums.PaymentStatus.FAILED
    payment.processed_at = datetime.datetime.now()
    session.add(payment)
    await session.commit()

    try:
        await _send_webhook(payment)
    except httpx.HTTPError:
        logger.exception('Failed to deliver webhook for payment %s', payment.id)


def _failed_attempts(headers: dict) -> int:
    """Сколько раз сообщение уже побывало в payments.new и было rejected."""
    for entry in headers.get('x-death') or []:
        if entry.get('queue') == brokers.Queues.PAYMENTS_NEW.value and entry.get('reason') == 'rejected':
            return entry.get('count', 0)
    return 0


@brokers.rabbit_mq_broker.subscriber(
    brokers.payments_new_queue,
    ack_policy=faststream.AckPolicy.REJECT_ON_ERROR,
)
async def new_payment(
    message: dict,
    raw_message: RabbitMessage,
    session: AsyncSession = faststream.Depends(get_db),
) -> None:
    if _failed_attempts(raw_message.headers) >= brokers.MAX_PAYMENT_RETRIES:
        logger.error('Payment message exceeded %s retries, moving to DLQ: %s', brokers.MAX_PAYMENT_RETRIES, message)
        await brokers.rabbit_mq_broker.publish(message, queue=brokers.Queues.PAYMENTS_NEW_DLQ)
        return

    payment_id = message['id']
    payment = await session.get(Payment, payment_id)
    if payment is None:
        # Не возвращаемся молча: пусть сообщение пройдёт тот же цикл
        # retry -> DLQ, что и прочие ошибки обработки.
        raise LookupError(f'Payment {payment_id} not found')

    if payment.status != enums.PaymentStatus.PENDING:
        # Защита от дублей: повторная доставка того же сообщения
        # (ретрай очереди, повторная публикация из outbox) не должна
        # запускать обработку и повторный webhook заново.
        logger.info('Payment %s already in terminal status %s, skipping duplicate delivery', payment.id, payment.status)
        return

    await _process_payment(payment, session)
