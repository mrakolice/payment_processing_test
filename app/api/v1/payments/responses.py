import datetime

import pydantic

from app.core import enums


class NewPaymentResponse(pydantic.BaseModel):
    payment_id: int
    status: enums.PaymentStatus = enums.PaymentStatus.PENDING
    created_at: datetime.datetime
