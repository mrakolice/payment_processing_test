import asyncio
import time

from app.core import brokers


async def _get_events() -> list:
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