"""Persistência da apuração com ajustes manuais.

Só lê e grava; regras e cálculos ficam em `app/services/apuracao.py`.
Funciona com qualquer backend (SQL ou Supabase) através de `store`.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from app.repositories import store

LANC = "apuracao_lancamentos"
SALDOS = "apuracao_saldos"
COMP = "apuracao_competencias"
HIST = "apuracao_historico"

_DATETIME_FIELDS = ("criado_em", "atualizado_em", "enviado_em", "validado_em")


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _out(row: dict | None) -> dict | None:
    """Datas em ISO (o SQL devolve datetime; o Supabase já devolve texto)."""
    if row is None:
        return None
    row = dict(row)
    for k in _DATETIME_FIELDS:
        v = row.get(k)
        if isinstance(v, dt.datetime):
            row[k] = (v if v.tzinfo else v.replace(tzinfo=dt.timezone.utc)).isoformat()
        elif isinstance(v, str) and v:
            row[k] = pd.Timestamp(v).isoformat()
    return row


def _many(rows: list[dict]) -> list[dict]:
    return [_out(r) for r in rows]


# --- Lançamentos -------------------------------------------------------------
def lancamentos(competencia: str | None = None, uf: str | None = None) -> list[dict]:
    eq = {k: v for k, v in (("competencia", competencia), ("uf", uf)) if v}
    return _many(store.rows(LANC, order="criado_em", **eq))


def lancamento(lanc_id: int) -> dict | None:
    found = store.rows(LANC, id=lanc_id)
    return _out(found[0]) if found else None


def criar_lancamento(values: dict) -> dict:
    return _out(store.insert_row(LANC, values))


def alterar_lancamento(lanc_id: int, values: dict) -> None:
    store.update_rows(LANC, values, id=lanc_id)


def excluir_lancamento(lanc_id: int) -> None:
    store.delete_rows(LANC, id=lanc_id)


# --- Saldos por tributo (saldo anterior, valor declarado, justificativa) ------
def saldos(uf: str, competencia: str | None = None) -> list[dict]:
    eq = {"uf": uf, **({"competencia": competencia} if competencia else {})}
    return _many(store.rows(SALDOS, order="competencia", **eq))


def gravar_saldo(competencia: str, uf: str, tributo: str, values: dict) -> None:
    key = {"competencia": competencia, "uf": uf, "tributo": tributo}
    if store.rows(SALDOS, **key):
        store.update_rows(SALDOS, values, **key)
    else:
        store.insert_row(SALDOS, {**key, **values})


# --- Status do mês ------------------------------------------------------------
def status(competencia: str, uf: str) -> dict | None:
    found = store.rows(COMP, competencia=competencia, uf=uf)
    return _out(found[0]) if found else None


def todos_status(uf: str | None = None) -> list[dict]:
    return _many(store.rows(COMP, order="competencia", **({"uf": uf} if uf else {})))


def gravar_status(competencia: str, uf: str, values: dict) -> None:
    key = {"competencia": competencia, "uf": uf}
    values = {**values, "atualizado_em": now()}
    if store.rows(COMP, **key):
        store.update_rows(COMP, values, **key)
    else:
        store.insert_row(COMP, {**key, **values})


# --- Histórico ---------------------------------------------------------------
def registrar(competencia: str, uf: str, acao: str, detalhe: str, usuario: str, papel: str) -> None:
    store.insert_row(HIST, {
        "competencia": competencia, "uf": uf, "acao": acao, "detalhe": detalhe[:1000],
        "usuario": usuario[:120], "papel": papel, "criado_em": now(),
    })


def historico(competencia: str, uf: str) -> list[dict]:
    return _many(store.rows(HIST, order="criado_em.desc", competencia=competencia, uf=uf))
