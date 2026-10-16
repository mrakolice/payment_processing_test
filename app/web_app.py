from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import sqlmodel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import main
from app.core import brokers
from app.core import config
from app.core.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create database tables and the shared upstream HTTP client on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(sqlmodel.SQLModel.metadata.create_all)

    try:
        await brokers.rabbit_mq_broker.start()
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=300.0, write=300.0, pool=5.0),
        ) as http_client:
            app.state.http_client = http_client
            yield
    finally:
        await brokers.rabbit_mq_broker.stop()


app = FastAPI(
    title='Connectors',
    description='Connector to ads statistics',
    version='0.1.0',
    lifespan=lifespan,
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.settings.server.allowed_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(main.router)

@app.get('/health')
async def health_check() -> dict:
    """Health check endpoint."""
    return {'status': 'ok'}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host=config.settings.server.listen_address, port=config.settings.server.port)
