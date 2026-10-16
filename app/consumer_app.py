import faststream

from app.core import brokers

app = faststream.FastStream(brokers.rabbit_mq_broker)

@brokers.rabbit_mq_broker.subscriber("payments.new")
async def new_payment(message: dict):
    print(message)