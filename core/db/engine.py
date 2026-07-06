from collections.abc import Iterator

from sqlalchemy import Engine
from sqlmodel import Session, SQLModel, create_engine

from configs.settings import get_settings


def create_db_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine, applying SQLite-friendly connect args."""
    connect_args: dict[str, object] = {}
    if database_url.startswith("sqlite"):
        # Allow the connection to be shared across threads (FastAPI threadpool).
        connect_args["check_same_thread"] = False
    return create_engine(database_url, connect_args=connect_args)


_engine: Engine | None = None


def get_engine() -> Engine:
    """Return the process-wide engine, building it from settings on first use."""
    global _engine
    if _engine is None:
        _engine = create_db_engine(get_settings().database_url)
    return _engine


def reset_engine() -> None:
    """Drop the cached engine so a later call rebuilds it (used by tests)."""
    global _engine
    _engine = None


def init_db(engine: Engine | None = None) -> None:
    """Create all known tables. Importing models registers them on metadata."""
    from core.db import models  # noqa: F401  (import for table registration)

    SQLModel.metadata.create_all(engine or get_engine())


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a session bound to the process engine."""
    with Session(get_engine()) as session:
        yield session
