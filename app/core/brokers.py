from faststream.rabbit import RabbitBroker

from app.core import config

rabbit_mq_broker = RabbitBroker(config.settings.rabbitmq.connection_string)

