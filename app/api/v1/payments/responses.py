import datetime

import pydantic

from app.core import enums


class NewPaymentResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)

    payment_id: int = pydantic.Field(validation_alias='id')
    status: enums.PaymentStatus = enums.PaymentStatus.PENDING
    created_at: datetime.datetime
