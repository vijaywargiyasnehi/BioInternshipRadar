"""Shared pytest fixtures: an isolated temp SQLite DB per test so tests never touch
the real data/database.sqlite, and keyword/location caches are cleared between tests."""
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.database as database_module
from app.database import Base
from app.services.keyword_service import clear_keyword_cache
from app.services.scoring_service import clear_location_cache


@pytest.fixture()
def db_session(monkeypatch):
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "test.sqlite"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})

    from app import models  # noqa: F401 ensures models are registered before create_all
    Base.metadata.create_all(bind=engine)

    TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(database_module, "SessionLocal", TestSessionLocal)

    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_keyword_cache()
    clear_location_cache()
    yield
    clear_keyword_cache()
    clear_location_cache()
