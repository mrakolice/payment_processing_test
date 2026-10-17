from __future__ import annotations

import datetime
import decimal

import sqlalchemy
import sqlmodel

from app.core import enums


class Payment(sqlmodel.SQLModel, table=True):
    __tablename__ = 'payments'

    id: int = sqlmodel.Field(sa_type=sqlmodel.Integer, primary_key=True)
    amount: decimal.Decimal = sqlmodel.Field(sa_type=sqlmodel.Numeric(12, 2), nullable=False)
    currency: enums.Currency = sqlmodel.Field(
        enums.Currency.RUB, sa_type=sqlmodel.Text, nullable=False,
        sa_column_kwargs={"server_default": enums.Currency.RUB}
    )
    description: str | None = sqlmodel.Field(default=None, sa_type=sqlmodel.Text, nullable=True)
    meta: dict | None = sqlmodel.Field(default=None, sa_type=sqlmodel.JSON, nullable=True)
    status: enums.PaymentStatus = sqlmodel.Field(default=enums.PaymentStatus.PENDING, sa_type=sqlmodel.Text, nullable=False)
    idempotency_key: str = sqlmodel.Field(sa_type=sqlmodel.Text, nullable=False, unique=True)
    webhook_url: str = sqlmodel.Field(sa_type=sqlmodel.Text, nullable=False)
    created_at: datetime.datetime = sqlmodel.Field(
        sa_type=sqlmodel.DateTime, nullable=False, default_factory=lambda: datetime.datetime.now(),
        sa_column_kwargs={"server_default": sqlalchemy.func.now()}
    )
    updated_at: datetime.datetime = sqlmodel.Field(
        sa_type=sqlmodel.DateTime, nullable=False, default_factory=lambda: datetime.datetime.now(),
        sa_column_kwargs={"server_default": sqlalchemy.func.now()}
    )
    processed_at: datetime.datetime | None = sqlmodel.Field(default=None, sa_type=sqlmodel.DateTime, nullable=True)

class Outbox(sqlmodel.SQLModel, table=True):
    __tablename__ = 'outbox'
    id: int = sqlmodel.Field(sa_type=sqlmodel.Integer, primary_key=True)
    payload: dict = sqlmodel.Field(sa_type=sqlmodel.JSON, nullable=False)
    created_at: datetime.datetime = sqlmodel.Field(
        sa_type=sqlmodel.DateTime, nullable=False, default_factory=lambda: datetime.datetime.now(),
        sa_column_kwargs={"server_default": sqlalchemy.func.now()}
    )
    published_at: datetime.datetime = sqlmodel.Field(sa_type=sqlmodel.DateTime, nullable=True)
