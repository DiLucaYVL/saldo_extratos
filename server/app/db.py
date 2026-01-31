"""Camada de acesso ao banco centralizada (fase 1 do plano)."""
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from server.app.config import get_settings
from server.app.models.base import Base

settings = get_settings()

engine = create_engine(settings.database_url, future=True, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_database() -> None:
    """Cria as tabelas basicas usadas para auditoria de conciliacao."""
    from server.app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session() -> Iterator[Session]:
    """Entrega uma sessao transacional para reuso seguro em todos os modulos."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
