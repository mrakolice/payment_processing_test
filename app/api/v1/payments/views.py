import fastapi
import sqlalchemy as sa
import sqlalchemy.exc as sa_exceptions

from app import dependencies
from app.api.v1.payments import responses
from app.core import models

router = fastapi.APIRouter(prefix="/payments", tags=["payments"])


@router.post('/', status_code=202)
async def create_payment(
        session: dependencies.DBSession,
        request: models.Payment,
        idempotency_key: dependencies.StrHeader,
        x_api_key: dependencies.StrHeader,
):
    if x_api_key is None:
        return fastapi.Response(status_code=403)

    if idempotency_key is None:
        return fastapi.Response(status_code=400, content="IDEMPOTENCY KEY is required")

    existing_payment = (await session.execute(
        sa.select(models.Payment).where(models.Payment.idempotency_key == idempotency_key)
    )).scalars().one_or_none()

    if existing_payment is not None:

        return responses.NewPaymentResponse.model_validate(existing_payment)

    request.id = None
    request.idempotency_key = idempotency_key

    try:
        session.add(request)
        await session.flush()  #
        session.add(models.Outbox(payload={'id': request.id}))
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

    return responses.NewPaymentResponse.model_validate(request)


@router.get('/{payment_id}')
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
