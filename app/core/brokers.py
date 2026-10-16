import enum

from faststream.rabbit import RabbitBroker

from app.core import config

class Queues(enum.StrEnum):
    PAYMENTS_NEW='payments.new'

rabbit_mq_broker = RabbitBroker(config.settings.rabbitmq.connection_string)

