"""Tabelas do banco (SQLAlchemy Core).

`fiscal_items` é gerada automaticamente a partir de `app.domain.columns`, assim
uma coluna nova no mapa já vira coluna no banco. O SQL equivalente para o
Supabase está em `supabase/migrations/0001_init.sql` (itens) e
`0002_apuracao.sql` (apuração com ajustes manuais).
"""
from __future__ import annotations

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
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


# ---------------------------------------------------------------------------
# Apuração com ajustes manuais (aba "Apuração & ajustes")
# Regras e textos ficam em app/domain/apuracao.py.
# ---------------------------------------------------------------------------
apuracao_lancamentos = Table(
    "apuracao_lancamentos",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("competencia", String(7), nullable=False),       # "2026-10"
    Column("uf", String(2), nullable=False),                # UF do estabelecimento (ex.: SP)
    Column("tributo", String(20), nullable=False),          # icms | ipi | pis | cofins
    Column("tipo", String(30), nullable=False),             # ajuste_debito | estorno_credito | ajuste_credito | estorno_debito
    Column("valor", Float, nullable=False),
    Column("descricao", String(500), nullable=False),
    Column("referencia", String(120)),                      # código de ajuste, processo, nota...
    Column("criado_por", String(120), nullable=False),
    Column("criado_em", DateTime(timezone=True), nullable=False),
    Column("atualizado_por", String(120)),
    Column("atualizado_em", DateTime(timezone=True)),
    Index("ix_apuracao_lancamentos_comp_uf", "competencia", "uf"),
)

apuracao_saldos = Table(
    "apuracao_saldos",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("competencia", String(7), nullable=False),
    Column("uf", String(2), nullable=False),
    Column("tributo", String(20), nullable=False),
    Column("saldo_credor_anterior", Float),                 # vazio = transporta do mês anterior
    Column("valor_declarado", Float),                       # resultado da apuração oficial: + a recolher, - credor
    Column("observacao", String(1000)),                     # justificativa de diferença
    Column("atualizado_por", String(120)),
    Column("atualizado_em", DateTime(timezone=True)),
    UniqueConstraint("competencia", "uf", "tributo", name="uq_apuracao_saldos"),
)

apuracao_competencias = Table(
    "apuracao_competencias",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("competencia", String(7), nullable=False),
    Column("uf", String(2), nullable=False),
    Column("status", String(20), nullable=False, default="rascunho"),
    Column("enviado_por", String(120)),
    Column("enviado_em", DateTime(timezone=True)),
    Column("validado_por", String(120)),
    Column("validado_em", DateTime(timezone=True)),
    Column("motivo_devolucao", String(1000)),
    Column("atualizado_em", DateTime(timezone=True)),
    UniqueConstraint("competencia", "uf", name="uq_apuracao_competencias"),
)

apuracao_historico = Table(
    "apuracao_historico",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("competencia", String(7), nullable=False),
    Column("uf", String(2), nullable=False),
    Column("acao", String(40), nullable=False),
    Column("detalhe", String(1000)),
    Column("usuario", String(120), nullable=False),
    Column("papel", String(20), nullable=False),
    Column("criado_em", DateTime(timezone=True), nullable=False),
    Index("ix_apuracao_historico_comp_uf", "competencia", "uf"),
)
