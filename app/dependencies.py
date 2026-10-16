import typing

import fastapi
from sqlalchemy.ext import asyncio as sa_async


from app.core import database

DBSession = typing.Annotated[sa_async.AsyncSession, fastapi.Depends(database.get_db)]

StrHeader = typing.Annotated[str | None, fastapi.Header()]