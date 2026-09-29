from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from .config import DATA_ROOT, get_settings


def _resolve_db_path(url: str) -> str:
    if url.startswith("sqlite:///"):
        path = Path(url.replace("sqlite:///", "", 1))
        path.parent.mkdir(parents=True, exist_ok=True)
    return url


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        DATA_ROOT.mkdir(parents=True, exist_ok=True)
        url = _resolve_db_path(get_settings().underdog_db_url)
        _engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})
    return _engine


def init_db() -> None:
    from . import models  # noqa: F401  ensure tables register

    SQLModel.metadata.create_all(get_engine())


def session_scope() -> Iterator[Session]:
    engine = get_engine()
    with Session(engine) as session:
        yield session
