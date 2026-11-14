"""Alembic migration environment for the authorized local SQLite H-04 baseline."""

from alembic import context

from app.db.engine import create_sqlite_engine


def run_migrations_online() -> None:
    engine = create_sqlite_engine()
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=None,
                render_as_batch=True,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline H-04 migration requires a separate approved design")

run_migrations_online()
