import decimal
import typing

import pydantic

from app.core import enums


class CreatePaymentRequest(pydantic.BaseModel):
    amount: decimal.Decimal = pydantic.Field(gt=0)
    currency: enums.Currency
    description: str | None = None
    metadata: dict[str, typing.Any] | None = None
    webhook_url: pydantic.AnyHttpUrl
