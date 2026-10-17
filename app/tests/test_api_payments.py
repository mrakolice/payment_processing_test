import sqlalchemy as sa

from app.core.models import Outbox, Payment

PAYLOAD = {
    'amount': '10.50',
    'currency': 'RUB',
    'description': 'test payment',
    'metadata': {'order_id': '42'},
    'webhook_url': 'http://example.com/hook',
}


async def test_create_payment_requires_api_key(api_client):
    response = await api_client.post(
        '/api/v1/payments/',
        headers={'Idempotency-Key': 'key-1'},
        json=PAYLOAD,
    )
    assert response.status_code == 403


async def test_create_payment_rejects_wrong_api_key(api_client):
    response = await api_client.post(
        '/api/v1/payments/',
        headers={'X-API-Key': 'wrong-key', 'Idempotency-Key': 'key-1'},
        json=PAYLOAD,
    )
    assert response.status_code == 403


async def test_create_payment_requires_idempotency_key(api_client, auth_headers):
    response = await api_client.post('/api/v1/payments/', headers=auth_headers, json=PAYLOAD)
    assert response.status_code == 400


async def test_create_payment_rejects_invalid_body(api_client, auth_headers):
    headers = {**auth_headers, 'Idempotency-Key': 'key-invalid'}
    bad_payload = {**PAYLOAD, 'currency': 'XXX'}  # не из enum Currency
    response = await api_client.post('/api/v1/payments/', headers=headers, json=bad_payload)
    assert response.status_code == 422


async def test_create_payment_success(api_client, auth_headers, db_session):
    headers = {**auth_headers, 'Idempotency-Key': 'key-success'}
    response = await api_client.post('/api/v1/payments/', headers=headers, json=PAYLOAD)

    assert response.status_code == 202
    body = response.json()
    assert body['status'] == 'pending'
    assert 'payment_id' in body and 'created_at' in body

    payment = (await db_session.execute(
        sa.select(Payment).where(Payment.id == body['payment_id'])
    )).scalar_one()
    assert payment.idempotency_key == 'key-success'
    assert str(payment.amount) == '10.50'

    # Outbox pattern: событие должно появиться атомарно с платежом.
    outbox_rows = (await db_session.execute(sa.select(Outbox))).scalars().all()
    assert len(outbox_rows) == 1
    assert outbox_rows[0].payload == {'id': payment.id}
    assert outbox_rows[0].published_at is None


async def test_create_payment_idempotent_duplicate(api_client, auth_headers, db_session):
    headers = {**auth_headers, 'Idempotency-Key': 'key-dup'}

    first = await api_client.post('/api/v1/payments/', headers=headers, json=PAYLOAD)
    second = await api_client.post(
        '/api/v1/payments/',
        headers=headers,
        json={**PAYLOAD, 'amount': '999.99', 'currency': 'USD'},
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()['payment_id'] == second.json()['payment_id']

    payments = (await db_session.execute(
        sa.select(Payment).where(Payment.idempotency_key == 'key-dup')
    )).scalars().all()
    assert len(payments) == 1
    assert payments[0].amount == 10.5  # от второго запроса не перезаписалось

    outbox_rows = (await db_session.execute(sa.select(Outbox))).scalars().all()
    assert len(outbox_rows) == 1  # повторный запрос не создал второе событие


async def test_get_payment_requires_api_key(api_client):
    response = await api_client.get('/api/v1/payments/1')
    assert response.status_code == 403


async def test_get_payment_not_found(api_client, auth_headers):
    response = await api_client.get('/api/v1/payments/999999', headers=auth_headers)
    assert response.status_code == 404


async def test_get_payment_returns_details(api_client, auth_headers):
    headers = {**auth_headers, 'Idempotency-Key': 'key-get'}
    created = await api_client.post('/api/v1/payments/', headers=headers, json=PAYLOAD)
    payment_id = created.json()['payment_id']

    response = await api_client.get(f'/api/v1/payments/{payment_id}', headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body['payment_id'] == payment_id
    assert body['currency'] == 'RUB'
    assert body['metadata'] == {'order_id': '42'}
    assert body['status'] == 'pending'
    assert body['processed_at'] is None
