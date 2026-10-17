import datetime
import decimal
import typing

import pydantic

from app.core import enums


class NewPaymentResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    payment_id: int = pydantic.Field(validation_alias='id')
    status: enums.PaymentStatus = enums.PaymentStatus.PENDING
    created_at: datetime.datetime


class PaymentDetailResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    payment_id: int = pydantic.Field(validation_alias='id')
    amount: decimal.Decimal
    currency: enums.Currency
    description: str | None
    metadata: dict[str, typing.Any] | None = pydantic.Field(validation_alias='meta')
    status: enums.PaymentStatus
    webhook_url: str
    created_at: datetime.datetime
    processed_at: datetime.datetime | None
