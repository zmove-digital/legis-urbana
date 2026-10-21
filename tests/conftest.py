"""Fixtures de teste: banco temporário carregado com as cidades de exemplo."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TMP_DIR = Path(tempfile.mkdtemp(prefix="legisurb-tests-"))

os.environ["LEGIS_DB_URL"] = f"sqlite:///{(TMP_DIR / 'test.db').as_posix()}"
os.environ["LEGIS_DATA_DIR"] = str(ROOT / "data")

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed.loader import seed_all  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _prepare_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        seed_all(session)
    finally:
        session.close()
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)
