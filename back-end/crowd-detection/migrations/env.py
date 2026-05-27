import json
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_secrets_path = os.path.join(_root, "keys", "secrets.json")

with open(_secrets_path) as _f:
    _s = json.load(_f)

_DB_URL = "postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}".format(
    user=_s["DB_USER"],
    password=_s["DB_PASSWORD"],
    host=_s["DB_HOST"],
    port=int(_s.get("PORT", 5432)),
    dbname=_s["DB_NAME"],
)

config = context.config
config.set_main_option("sqlalchemy.url", _DB_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Модели SQLAlchemy не используются — миграции написаны на raw SQL
target_metadata = None


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
