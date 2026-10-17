import typing

import fastapi
from sqlalchemy.ext import asyncio as sa_async

from app.core import config, database

DBSession = typing.Annotated[sa_async.AsyncSession, fastapi.Depends(database.get_db)]

StrHeader = typing.Annotated[str | None, fastapi.Header()]


async def verify_api_key(x_api_key: StrHeader = None) -> None:
    """Статический API-ключ, обязательный для всех эндпоинтов (см. ТЗ)."""
    if x_api_key is None or x_api_key != config.settings.server.api_key:
        raise fastapi.HTTPException(status_code=403, detail='Invalid or missing X-API-Key')
