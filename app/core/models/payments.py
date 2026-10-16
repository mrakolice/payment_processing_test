import enum
import datetime

import sqlalchemy
import sqlmodel

class Currency(enum.StrEnum):
    RUB='RUB'
    USD='USD'
    EUR='EUR'

class PaymentStatus(enum.StrEnum):
    PENDING='pending'
    SUCCEEDED='succeeded'
    FAILED='failed'

class Payment(sqlmodel.SQLModel, table=True):
    __tablename__ = 'payments'

    id: int = sqlmodel.Field(sa_type=sqlmodel.Integer, primary_key=True)
    currency: Currency = sqlmodel.Field(
        Currency.RUB, sa_type=sqlmodel.Text, nullable=False,
        sa_column_kwargs={"server_default": Currency.RUB}
    )
    description: str = sqlmodel.Field(sa_type=sqlmodel.Text, nullable=True)
    meta: str = sqlmodel.Field(sa_type=sqlmodel.JSON, nullable=True)
    status: PaymentStatus = sqlmodel.Field(PaymentStatus.PENDING, sa_type=sqlmodel.Text, nullable=False)
    idempotency_key: str = sqlmodel.Field(sa_type=sqlmodel.Text, nullable=False)
    webhook_url: str = sqlmodel.Field(sa_type=sqlmodel.Text, nullable=False)
    created_at: datetime.datetime = sqlmodel.Field(
        sa_type=sqlmodel.DateTime, nullable=False, default_factory=lambda: datetime.datetime.now(),
        sa_column_kwargs={"server_default": sqlalchemy.func.now()}
    )
    updated_at: datetime.datetime = sqlmodel.Field(
        sa_type=sqlmodel.DateTime, nullable=False, default_factory=lambda: datetime.datetime.now(),
        sa_column_kwargs={"server_default": sqlalchemy.func.now()}
    )

