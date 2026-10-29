"""Tabelas do banco (SQLAlchemy Core).

`fiscal_items` é gerada automaticamente a partir de `app.domain.columns`, assim
uma coluna nova no mapa já vira coluna no banco. O SQL equivalente para o
Supabase está em `supabase/migrations/0001_init.sql`.
"""
from __future__ import annotations

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    func,
)

from app.domain.columns import COLUMNS, NATURAL_KEY

metadata = MetaData()

imports = Table(
    "imports",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("filename", String(255), nullable=False),
    Column("sheet", String(120), nullable=False),
    Column("file_hash", String(64), nullable=False, unique=True),
    Column("rows_read", Integer, nullable=False, default=0),
    Column("rows_inserted", Integer, nullable=False, default=0),
    Column("rows_duplicated", Integer, nullable=False, default=0),
    Column("periodo_ini", Date),
    Column("periodo_fim", Date),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)

_TYPE = {"text": lambda: String(255), "date": lambda: Date(), "num": lambda: Float()}

fiscal_items = Table(
    "fiscal_items",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("import_id", Integer, ForeignKey("imports.id", ondelete="CASCADE"), nullable=False, index=True),
    *[Column(c.field, _TYPE[c.kind](), nullable=True) for c in COLUMNS],
    UniqueConstraint(*NATURAL_KEY, name="uq_fiscal_items_natural_key"),
)
