"""Alembic environment (async)."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from openrange.api.db.base import Base
from openrange.api.labs import models as labs_models  # noqa: F401 - register tables
from openrange.api.learning import models as learning_models  # noqa: F401 - register tables
from openrange.api.notifications import (
    models as notifications_models,  # noqa: F401 - register tables
)
from openrange.api.orgs import models as orgs_models  # noqa: F401 - register tables
from openrange.api.scoring import models as scoring_models  # noqa: F401 - register tables
from openrange.api.studio import models as studio_models  # noqa: F401 - register tables
from openrange.api.users import models  # noqa: F401 - register tables
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    from openrange.api.config import get_settings

    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(configuration, prefix="sqlalchemy.")
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
