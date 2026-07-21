"""SQLAlchemy engine/session setup and DB initialization."""
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings, BASE_DIR


def _resolve_database_url(url: str) -> str:
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        rel = url.replace("sqlite:///", "", 1)
        abs_path = BASE_DIR / rel
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{abs_path.as_posix()}"
    return url


engine = create_engine(
    _resolve_database_url(settings.database_url),
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def run_migrations() -> None:
    """Add columns introduced after initial schema creation — safe to call repeatedly."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    with engine.connect() as conn:
        for table, column, col_def in [
            ("companies", "board_id", "VARCHAR DEFAULT ''"),
        ]:
            if table in inspector.get_table_names():
                existing = {c["name"] for c in inspector.get_columns(table)}
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))
        conn.commit()


def init_db() -> None:
    from app import models  # noqa: F401 ensures models are registered
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
