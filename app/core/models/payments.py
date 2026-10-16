from __future__ import annotations

import datetime

import sqlalchemy
import sqlmodel

from app.core import enums


class Payment(sqlmodel.SQLModel, table=True):
    __tablename__ = 'payments'

    id: int = sqlmodel.Field(sa_type=sqlmodel.Integer, primary_key=True)
    currency: enums.Currency = sqlmodel.Field(
        enums.Currency.RUB, sa_type=sqlmodel.Text, nullable=False,
        sa_column_kwargs={"server_default": enums.Currency.RUB}
    )
    description: str = sqlmodel.Field(sa_type=sqlmodel.Text, nullable=True)
    meta: str = sqlmodel.Field(sa_type=sqlmodel.JSON, nullable=True)
    status: enums.PaymentStatus = sqlmodel.Field(enums.PaymentStatus.PENDING, sa_type=sqlmodel.Text, nullable=False)
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

class Outbox(sqlmodel.SQLModel, table=True):
    __tablename__ = 'outbox'
    id: int = sqlmodel.Field(sa_type=sqlmodel.Integer, primary_key=True)

    payment: Payment = sqlmodel.Field(Payment)
    created_at: datetime.datetime = sqlmodel.Field(
        sa_type=sqlmodel.DateTime, nullable=False, default_factory=lambda: datetime.datetime.now(),
        sa_column_kwargs={"server_default": sqlalchemy.func.now()}
    )
    published_at: datetime.datetime = sqlmodel.Field(
        sa_type=sqlmodel.DateTime, nullable=False, default_factory=lambda: datetime.datetime.now(),
        sa_column_kwargs={"server_default": sqlalchemy.func.now()}
    )