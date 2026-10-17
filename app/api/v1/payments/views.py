import fastapi
import sqlalchemy as sa
import sqlalchemy.exc as sa_exceptions

from app import dependencies
from app.api.v1.payments import requests, responses
from app.core import models

router = fastapi.APIRouter(
    prefix="/payments",
    tags=["payments"],
    dependencies=[fastapi.Depends(dependencies.verify_api_key)],
)


@router.post('/', status_code=202, response_model=responses.NewPaymentResponse)
async def create_payment(
        session: dependencies.DBSession,
        body: requests.CreatePaymentRequest,
        idempotency_key: dependencies.StrHeader = None,
):
    if idempotency_key is None:
        return fastapi.Response(status_code=400, content="Idempotency-Key header is required")

    existing_payment = (await session.execute(
        sa.select(models.Payment).where(models.Payment.idempotency_key == idempotency_key)
    )).scalars().one_or_none()

    if existing_payment is not None:
        return responses.NewPaymentResponse.model_validate(existing_payment)

    payment = models.Payment(
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        meta=body.metadata,
        webhook_url=str(body.webhook_url),
        idempotency_key=idempotency_key,
    )

    try:
        session.add(payment)
        await session.flush()
        session.add(models.Outbox(payload={'id': payment.id}))
        await session.commit()
    except sa_exceptions.IntegrityError:
        await session.rollback()
        existing_payment = (await session.execute(
            sa.select(models.Payment).where(models.Payment.idempotency_key == idempotency_key)
        )).scalars().one()
        return responses.NewPaymentResponse.model_validate(existing_payment)
    except sa_exceptions.DatabaseError:
        await session.rollback()
        return fastapi.Response(status_code=400)

    return responses.NewPaymentResponse.model_validate(payment)


@router.get('/{payment_id}', response_model=responses.PaymentDetailResponse)
async def get_payment(
        session: dependencies.DBSession,
        payment_id: int,
):
    try:
        payment = (await session.execute(
            sa.select(models.Payment).where(models.Payment.id == payment_id)
        )).scalars().one_or_none()
    except sa_exceptions.DatabaseError:
        return fastapi.Response(status_code=400)

    if payment is None:
        return fastapi.Response(status_code=404)

    return payment
