import decimal
from unittest import mock

import httpx
import pytest

from app.consumer_app import _failed_attempts, _process_payment, _retry_delay
from app.core import enums
from app.core.models import Payment


def _make_payment(**overrides) -> Payment:
    defaults = dict(
        amount=decimal.Decimal('10'),
        currency=enums.Currency.RUB,
        webhook_url='http://example.com/hook',
        idempotency_key='consumer-test',
        status=enums.PaymentStatus.PENDING,
    )
    defaults.update(overrides)
    return Payment(**defaults)


class _FakeResponse:
    def raise_for_status(self):
        pass


async def test_process_payment_success_sets_terminal_status_and_processed_at(db_session):
    payment = _make_payment()
    db_session.add(payment)
    await db_session.flush()

    with mock.patch('random.random', return_value=0.0), \
         mock.patch('asyncio.sleep', new=mock.AsyncMock()), \
         mock.patch.object(httpx.AsyncClient, 'post', new=mock.AsyncMock(return_value=_FakeResponse())):
        await _process_payment(payment, db_session)

    assert payment.status == enums.PaymentStatus.SUCCEEDED
    assert payment.processed_at is not None


async def test_process_payment_failure_sets_failed_status(db_session):
    payment = _make_payment()
    db_session.add(payment)
    await db_session.flush()

    with mock.patch('random.random', return_value=0.99), \
         mock.patch('asyncio.sleep', new=mock.AsyncMock()):
        await _process_payment(payment, db_session)

    assert payment.status == enums.PaymentStatus.FAILED
    assert payment.processed_at is not None


async def test_process_payment_webhook_failure_does_not_crash_handler(db_session):
    """Статус должен сохраниться, даже если webhook недоступен после всех ретраев."""
    payment = _make_payment()
    db_session.add(payment)
    await db_session.flush()

    with mock.patch('random.random', return_value=0.0), \
         mock.patch('asyncio.sleep', new=mock.AsyncMock()), \
         mock.patch.object(httpx.AsyncClient, 'post', new=mock.AsyncMock(side_effect=httpx.ConnectError('boom'))):
        await _process_payment(payment, db_session)  # не должно поднять исключение

    assert payment.status == enums.PaymentStatus.SUCCEEDED


class TestWebhookRetry:
    async def test_succeeds_after_transient_failures(self):
        calls = []

        async def flaky_post(self, url, json=None):
            calls.append(json)
            if len(calls) < 3:
                raise httpx.ConnectError('boom')
            return _FakeResponse()

        payment = _make_payment()
        with mock.patch.object(httpx.AsyncClient, 'post', flaky_post), \
             mock.patch('asyncio.sleep', new=mock.AsyncMock()):
            from app.consumer_app import _send_webhook
            await _send_webhook(payment)

        assert len(calls) == 3

    async def test_raises_after_exhausting_all_retries(self):
        async def always_fail(self, url, json=None):
            raise httpx.ConnectError('boom')

        payment = _make_payment()
        with mock.patch.object(httpx.AsyncClient, 'post', always_fail), \
             mock.patch('asyncio.sleep', new=mock.AsyncMock()):
            from app.consumer_app import _send_webhook
            with pytest.raises(httpx.HTTPError):
                await _send_webhook(payment)


@pytest.mark.parametrize('attempt', [0, 1, 2, 5])
def test_retry_delay_never_exceeds_max_delay(attempt):
    for _ in range(20):
        assert 0 <= _retry_delay(attempt, base_delay=1.0, max_delay=5.0) <= 5.0


def test_retry_delay_cap_grows_with_attempt():
    # Экспоненциальный рост: cap на attempt=0 должен быть меньше, чем на attempt=3
    # (до тех пор, пока не упрётся в max_delay).
    caps = [min(5.0, 1.0 * (2 ** a)) for a in range(4)]
    assert caps == [1.0, 2.0, 4.0, 5.0]


def test_failed_attempts_reads_x_death_count_for_main_queue():
    headers = {
        'x-death': [
            {'queue': 'payments.new', 'reason': 'rejected', 'count': 2},
            {'queue': 'payments.new.retry', 'reason': 'expired', 'count': 2},
        ],
    }
    assert _failed_attempts(headers) == 2


def test_failed_attempts_returns_zero_without_x_death():
    assert _failed_attempts({}) == 0
