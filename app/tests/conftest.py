import asyncio

import httpx
import pytest
import sqlalchemy as sa

from app.core import brokers, config
from app.core.database import async_session
from app.core.models import Outbox, Payment
from app.web_app import app as fastapi_app

API_KEY = config.settings.server.api_key


@pytest.fixture
async def db_session():
    async with async_session() as session:
        yield session


@pytest.fixture(autouse=True)
async def _clean_tables():
    """Тесты делят одну БД (см. README про тестовую БД) — чистим перед каждым тестом."""
    async with async_session() as session:
        await session.execute(sa.delete(Outbox))
        await session.execute(sa.delete(Payment))
        await session.commit()
    yield


@pytest.fixture
async def api_client():
    transport = httpx.ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url='http://test') as client:
        yield client


@pytest.fixture
def auth_headers():
    return {'X-API-Key': API_KEY}


@pytest.fixture
async def clean_queues():
    """Очищает payments.new/.retry/.dlq перед интеграционными тестами брокера."""
    async with brokers.rabbit_mq_broker:
        for queue in (brokers.payments_new_queue, brokers.payments_new_retry_queue, brokers.payments_new_dlq_queue):
            declared = await brokers.rabbit_mq_broker.declare_queue(queue)
            await declared.purge()
    yield
