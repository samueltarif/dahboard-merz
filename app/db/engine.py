"""Conexão com o banco.

O mesmo código funciona com:
- SQLite local (padrão, arquivo em data/dashboard.db) - zero configuração;
- Postgres do docker-compose;
- Supabase (é Postgres: use a connection string do painel do Supabase).
"""
from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from app.config import settings


def _normalize_url(url: str) -> str:
    # Supabase/Heroku entregam "postgres://" ou "postgresql://"; usamos o driver psycopg 3.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = _normalize_url(settings.database_url)
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False}, future=True)

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _):  # habilita ON DELETE CASCADE no SQLite
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

        return engine
    return create_engine(url, pool_pre_ping=True, future=True)


def init_db() -> None:
    from app.db.models import metadata

    metadata.create_all(get_engine())


def backend_name() -> str:
    return get_engine().dialect.name
