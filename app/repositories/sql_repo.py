"""Repositório SQL (SQLAlchemy): SQLite local, Postgres do Docker ou Supabase via connection string.

Toda leitura/escrita SQL passa por aqui. Os serviços só recebem/entregam
DataFrames e dicts, então trocar de banco não afeta o resto do código.
"""
from __future__ import annotations

import datetime as dt
import math

import pandas as pd
from sqlalchemy import delete, func, insert, select

from app.db.engine import backend_name, get_engine, init_db
from app.db.models import fiscal_items, imports
from app.domain.columns import COLUMNS, NATURAL_KEY
from app.repositories.common import SaveResult, file_hash  # noqa: F401  (reexporta file_hash)

CHUNK = 500


def ensure_schema() -> None:
    init_db()


def backend_label() -> str:
    return backend_name()


def find_by_hash(digest: str) -> dict | None:
    with get_engine().connect() as conn:
        row = conn.execute(select(imports).where(imports.c.file_hash == digest)).mappings().first()
        return dict(row) if row else None


def _existing_keys(conn) -> set[tuple]:
    cols = [fiscal_items.c[k] for k in NATURAL_KEY]
    return {tuple(r) for r in conn.execute(select(*cols))}


def _clean(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    return value


def save_import(filename: str, sheet: str, digest: str, frame: pd.DataFrame) -> SaveResult:
    """Grava o lote e os itens numa única transação, ignorando itens já existentes."""
    fields = [c.field for c in COLUMNS]
    engine = get_engine()
    with engine.begin() as conn:
        existing = _existing_keys(conn)
        keys = list(frame[list(NATURAL_KEY)].itertuples(index=False, name=None))
        is_new = [k not in existing for k in keys]
        new_rows = frame[is_new].drop_duplicates(subset=list(NATURAL_KEY))
        duplicated = len(frame) - len(new_rows)

        dates = pd.to_datetime(new_rows["data_lancamento"], errors="coerce") if len(new_rows) else pd.Series(dtype="datetime64[ns]")
        result = conn.execute(
            insert(imports).values(
                filename=filename[:255],
                sheet=sheet[:120],
                file_hash=digest,
                rows_read=len(frame),
                rows_inserted=len(new_rows),
                rows_duplicated=duplicated,
                periodo_ini=dates.min().date() if dates.notna().any() else None,
                periodo_fim=dates.max().date() if dates.notna().any() else None,
                created_at=dt.datetime.now(dt.timezone.utc),
            )
        )
        import_id = result.inserted_primary_key[0]

        records = [
            {"import_id": import_id, **{f: _clean(v) for f, v in zip(fields, row)}}
            for row in new_rows[fields].itertuples(index=False, name=None)
        ]
        for start in range(0, len(records), CHUNK):
            conn.execute(insert(fiscal_items), records[start:start + CHUNK])

    return SaveResult(import_id, len(frame), len(new_rows), duplicated)


def list_imports() -> list[dict]:
    with get_engine().connect() as conn:
        rows = conn.execute(select(imports).order_by(imports.c.created_at.desc(), imports.c.id.desc())).mappings().all()
        counts = dict(
            conn.execute(select(fiscal_items.c.import_id, func.count()).group_by(fiscal_items.c.import_id)).all()
        )
    out = []
    for r in rows:
        d = dict(r)
        d["rows_current"] = counts.get(d["id"], 0)
        out.append(d)
    return out


def delete_import(import_id: int) -> bool:
    with get_engine().begin() as conn:
        conn.execute(delete(fiscal_items).where(fiscal_items.c.import_id == import_id))
        res = conn.execute(delete(imports).where(imports.c.id == import_id))
        return res.rowcount > 0


def delete_all() -> None:
    with get_engine().begin() as conn:
        conn.execute(delete(fiscal_items))
        conn.execute(delete(imports))


def load_items() -> pd.DataFrame:
    """Carrega todos os itens como DataFrame (colunas = campos internos + import_id)."""
    with get_engine().connect() as conn:
        rows = conn.execute(select(fiscal_items)).mappings().all()
    if not rows:
        return pd.DataFrame(columns=["id", "import_id", *[c.field for c in COLUMNS]])
    return pd.DataFrame([dict(r) for r in rows])
