"""SQLAlchemy engine/session setup and DB initialization (SQLite only)."""
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings, BASE_DIR


def _resolve_database_url(url: str) -> str:
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        rel = url.replace("sqlite:///", "", 1)
        abs_path = BASE_DIR / rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{abs_path.as_posix()}"
    return url


def _make_engine(url: str):
    resolved = _resolve_database_url(url)
    return create_engine(resolved, connect_args={"check_same_thread": False})


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def run_migrations() -> None:
    """Add columns introduced after initial schema creation. Safe to call repeatedly."""
    from sqlalchemy import inspect
    inspector = inspect(engine)

    with engine.connect() as conn:
        tables = inspector.get_table_names()

        def _add_column(table: str, column: str, col_def: str) -> None:
            if table not in tables:
                return
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))

        _add_column("companies", "board_id", "VARCHAR DEFAULT ''")
        _add_column("opportunities", "is_active", "BOOLEAN DEFAULT 1")

        conn.commit()


def init_db() -> None:
    from app import models  # noqa: F401 — registers all ORM models before create_all
    Base.metadata.create_all(bind=engine)
    run_migrations()


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
