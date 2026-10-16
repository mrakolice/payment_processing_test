import enum

from faststream.rabbit import RabbitBroker, RabbitQueue

from app.core import config

MAX_PAYMENT_RETRIES = 3
RETRY_TTL_MS = 5_000


class Queues(enum.StrEnum):
    PAYMENTS_NEW = 'payments.new'
    PAYMENTS_NEW_RETRY = 'payments.new.retry'
    PAYMENTS_NEW_DLQ = 'payments.new.dlq'


rabbit_mq_broker = RabbitBroker(config.settings.rabbitmq.connection_string)

# payments.new --(reject, requeue=False)--> payments.new.retry --(TTL истёк)--> payments.new
# Цикл повторяется, пока в x-death не накопится MAX_PAYMENT_RETRIES неудачных
# попыток в payments.new — после этого хендлер (см. consumer_app.py) публикует
# сообщение в payments.new.dlq вручную и забирает его из цикла ретраев.
payments_new_queue = RabbitQueue(
    Queues.PAYMENTS_NEW.value,
    durable=True,
    arguments={
        'x-dead-letter-exchange': '',
        'x-dead-letter-routing-key': Queues.PAYMENTS_NEW_RETRY.value,
    },
)

payments_new_retry_queue = RabbitQueue(
    Queues.PAYMENTS_NEW_RETRY.value,
    durable=True,
    arguments={
        'x-dead-letter-exchange': '',
        'x-dead-letter-routing-key': Queues.PAYMENTS_NEW.value,
        'x-message-ttl': RETRY_TTL_MS,
    },
)

payments_new_dlq_queue = RabbitQueue(
    Queues.PAYMENTS_NEW_DLQ.value,
    durable=True,
)
