import fastapi

from app import dependencies
from app.api.v1.payments import responses
from app.core import models
import sqlalchemy as sa
import sqlalchemy.exc as sa_exceptions

router = fastapi.APIRouter(prefix="/payments", tags=["payments"])


@router.post('/')
async def create_payment(
        session: dependencies.DBSession,
        request: models.Payment,
        idempotency_key: dependencies.StrHeader,
        x_api_key: dependencies.StrHeader,
):
    try:
        if x_api_key is None:
            return fastapi.Response(status_code=403)

        if idempotency_key is None:
            return fastapi.Response(status_code=400, content="IDEMPOTENCY KEY is required")

        _existing_payment = await session.execute(
            sa.select(models.Payment).where(models.Payment.idempotency_key == idempotency_key)
        )
        existing_payment = _existing_payment.scalars().one()

        result = existing_payment

        if existing_payment is None:
            request.idempotency_key = idempotency_key
            outbox = models.Outbox(
                payment=request,
            )
            session.add(request)
            session.add(outbox)
            session.commit()

            result = request

        return fastapi.Response(status_code=202, content=responses.NewPaymentResponse.model_validate(result))

    except sa_exceptions.DatabaseError:
        return fastapi.Response(status_code=400, )


@router.get('/{payment_id')
async def get_payment(
        session: dependencies.DBSession,
        payment_id: str,
):
    try:
        if idempotency_key is None:
            return fastapi.Response(status_code=400, content="IDEMPOTENCY KEY is required")

        _payment = await session.execute(sa.select(models.Payment, models.Payment.id == payment_id))

        result = _payment.scalars().one()

        if result is None:
            return fastapi.Response(status_code=404)

        return result

    except sa_exceptions.DatabaseError:
        return fastapi.Response(status_code=400, )
