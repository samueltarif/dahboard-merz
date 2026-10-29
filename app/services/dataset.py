"""Base analítica em memória.

Carrega os itens do banco uma vez, aplica as classificações (CFOP, tributos)
e guarda em cache. Qualquer importação/exclusão chama `invalidate()`.
"""
from __future__ import annotations

import threading

import pandas as pd

from app.domain import cfop as cfop_rules
from app.domain.columns import NUMERIC_FIELDS
from app.domain.taxes import CONSUMO_KEYS, REFORMA_KEYS, TAXES
from app.repositories import imports_repo

_lock = threading.Lock()
_cache: pd.DataFrame | None = None


def invalidate() -> None:
    global _cache
    with _lock:
        _cache = None


def get_dataset() -> pd.DataFrame:
    global _cache
    with _lock:
        if _cache is None:
            _cache = enrich(imports_repo.load_items())
        return _cache


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta colunas derivadas usadas por todo o painel."""
    df = df.copy()
    for f in NUMERIC_FIELDS:
        df[f] = pd.to_numeric(df.get(f), errors="coerce").fillna(0.0)

    # Classificação por CFOP (feita por CFOP único -> rápido mesmo com muitos itens)
    pairs = df[["cfop_raw", "direcao"]].astype(str).drop_duplicates()
    info = {(r, d): cfop_rules.classify(r, d) for r, d in pairs.itertuples(index=False, name=None)}
    keys = list(zip(df["cfop_raw"].astype(str), df["direcao"].astype(str)))
    df["cfop"] = [info[k].cfop for k in keys]
    df["fluxo"] = [info[k].movimento for k in keys]
    df["operacao"] = [info[k].operacao for k in keys]
    df["natureza"] = [info[k].natureza for k in keys]

    exterior = df["operacao"].eq("Exterior") | (df["pais"].fillna("BR").ne("BR"))
    df["uf_op"] = df["uf"].fillna("—").where(~exterior, "EX")

    lanc = pd.to_datetime(df["data_lancamento"], errors="coerce")
    df["data_lancamento"] = lanc
    df["data_documento"] = pd.to_datetime(df["data_documento"], errors="coerce")
    df["periodo"] = lanc.dt.strftime("%Y-%m").fillna("sem data")
    df["dia"] = lanc.dt.strftime("%Y-%m-%d")

    for tax in TAXES:
        df[f"tx_{tax.key}"] = df[list(tax.sources)].sum(axis=1)
    df["tributos"] = df[[f"tx_{k}" for k in CONSUMO_KEYS]].sum(axis=1)
    df["tributos_reforma"] = df[[f"tx_{k}" for k in REFORMA_KEYS]].sum(axis=1)

    df["gera_credito_icms_ipi"] = ~df["natureza"].isin(cfop_rules.SEM_CREDITO_ICMS_IPI)
    df["doc_key"] = df["chave_acesso"].fillna(df["numero_documento"].astype(str))
    for col in ("parceiro_nome", "material_desc", "ncm", "natureza_operacao", "modelo"):
        df[col] = df[col].fillna("—")
    return df
