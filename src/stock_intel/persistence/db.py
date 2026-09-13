"""Postgres persistence (Specification.md Section 3/14 — Phase 4).

Every function here degrades gracefully: if DATABASE_URL isn't set or the DB
isn't reachable, callers get a clear warning and the pipeline keeps running
off the JSON report alone, exactly like the provider_factory fallback
pattern used for live market-data/news providers.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

_engine = None
_SessionLocal = None


def is_configured() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        database_url = os.environ["DATABASE_URL"]
        _engine = create_engine(database_url, pool_pre_ping=True)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def init_db() -> None:
    """Creates tables if they don't exist. Simple create_all for v1 — swap
    for Alembic migrations once the schema needs to evolve carefully."""
    engine = get_engine()
    Base.metadata.create_all(engine)


@contextmanager
def get_session() -> Iterator[Session]:
    get_engine()  # ensures _SessionLocal is initialized
    assert _SessionLocal is not None
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
