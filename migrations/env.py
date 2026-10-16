import asyncio
import os
from logging.config import fileConfig

import sqlmodel
from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy_declarative_extensions import register_alembic_events
# from sqlmodel import SQLModel
# Add your model's MetaData oject for 'autogenerate' support
from app.core import models
from app.core import config as app_config

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


register_alembic_events(schemas=True, roles=True, grants=True, rows=True)


target_metadata = sqlmodel.SQLModel.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = app_config.settings.database.async_connection_string

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        # Other services share this same database and each keep their own
        # migration history in the default 'alembic_version' table.
        version_table='alembic_version_gateway',
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration['sqlalchemy.url'] = app_config.settings.database.async_connection_string

    connectable = async_engine_from_config(
        configuration,
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    async def run_migrations() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(
                lambda sync_conn: context.configure(
                    connection=sync_conn,
                    target_metadata=target_metadata,
                    version_table='alembic_version_gateway',
                )
            )
            async with connection.begin():
                await connection.run_sync(lambda sync_conn: context.run_migrations())

    asyncio.run(run_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
