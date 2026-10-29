"""Repositório Supabase via API REST (PostgREST), autenticado com a chave de servidor.

Mesmas funções do `sql_repo`, então o resto do código não sabe qual está em uso.
As tabelas precisam existir no Supabase: rode `supabase/migrations/0001_init.sql`
uma vez no SQL Editor do projeto.

Observação: a API REST não tem transação entre várias chamadas. Se a gravação
dos itens falhar no meio, o lote criado é apagado (compensação) para não deixar
dados pela metade.
"""
from __future__ import annotations

import datetime as dt
import logging
import math
from functools import lru_cache

import httpx
import pandas as pd

from app.config import settings
from app.domain.columns import COLUMNS, NATURAL_KEY
from app.repositories.common import SaveResult, file_hash  # noqa: F401  (reexporta file_hash)

log = logging.getLogger(__name__)

CHUNK = 500        # itens por requisição de inserção
PAGE = 1000        # limite padrão de linhas por resposta do PostgREST
TIMEOUT = httpx.Timeout(60.0, connect=15.0)


class SupabaseError(RuntimeError):
    """Erro vindo da API do Supabase, com mensagem legível."""


def _headers() -> dict[str, str]:
    key = settings.supabase_service_key
    h = {"apikey": key, "Content-Type": "application/json"}
    if not key.startswith("sb_"):  # chaves legadas (JWT) também vão no Authorization
        h["Authorization"] = f"Bearer {key}"
    return h


@lru_cache(maxsize=1)
def _client() -> httpx.Client:
    if not settings.supabase_url or not settings.supabase_service_key:
        raise SupabaseError("Defina SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no arquivo .env.")
    return httpx.Client(base_url=f"{settings.supabase_url}/rest/v1", headers=_headers(), timeout=TIMEOUT)


def _check(res: httpx.Response) -> httpx.Response:
    if res.is_success:
        return res
    try:
        body = res.json()
        msg = body.get("message") or body.get("hint") or str(body)
        code = body.get("code", "")
    except ValueError:
        msg, code = res.text[:300], ""
    if code in ("PGRST205", "42P01") or "Could not find the table" in msg:
        raise SupabaseError(
            "As tabelas ainda não existem no Supabase. Abra o SQL Editor do projeto e rode o arquivo "
            "supabase/migrations/0001_init.sql (uma vez só)."
        )
    if res.status_code in (401, 403):
        raise SupabaseError(f"Supabase recusou a chave ({res.status_code}). Confira SUPABASE_SERVICE_ROLE_KEY no .env. Detalhe: {msg}")
    raise SupabaseError(f"Supabase respondeu {res.status_code}: {msg}")


def _json_value(v: object) -> object:
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return v.date().isoformat()
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    if hasattr(v, "item"):  # numpy -> python
        return v.item()
    return v


def _get_all(table: str, params: dict[str, str]) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    while True:
        res = _check(_client().get(f"/{table}", params={**params, "limit": str(PAGE), "offset": str(offset)}))
        batch = res.json()
        rows.extend(batch)
        if len(batch) < PAGE:
            return rows
        offset += PAGE


# ---------------------------------------------------------------------------
# Interface pública (igual à do sql_repo)
# ---------------------------------------------------------------------------
def ensure_schema() -> None:
    """Só verifica: a API REST não cria tabelas. Loga instrução clara se faltar."""
    try:
        _check(_client().get("/imports", params={"select": "id", "limit": "1"}))
        _check(_client().get("/fiscal_items", params={"select": "id", "limit": "1"}))
        log.info("Supabase conectado: %s", settings.supabase_url)
    except (SupabaseError, httpx.HTTPError) as exc:
        log.error("Supabase: %s", exc)


def backend_label() -> str:
    return "supabase-rest"


def find_by_hash(digest: str) -> dict | None:
    res = _check(_client().get("/imports", params={"select": "*", "file_hash": f"eq.{digest}", "limit": "1"}))
    rows = res.json()
    if not rows:
        return None
    row = rows[0]
    row["created_at"] = pd.to_datetime(row["created_at"]).to_pydatetime()
    return row


def _existing_keys() -> set[tuple]:
    rows = _get_all("fiscal_items", {"select": ",".join(NATURAL_KEY), "order": "id"})
    return {tuple(r[k] for k in NATURAL_KEY) for r in rows}


def save_import(filename: str, sheet: str, digest: str, frame: pd.DataFrame) -> SaveResult:
    fields = [c.field for c in COLUMNS]
    existing = _existing_keys()
    keys = list(frame[list(NATURAL_KEY)].itertuples(index=False, name=None))
    new_rows = frame[[k not in existing for k in keys]].drop_duplicates(subset=list(NATURAL_KEY))
    duplicated = len(frame) - len(new_rows)
    dates = pd.to_datetime(new_rows["data_lancamento"], errors="coerce")

    header = {
        "filename": filename[:255], "sheet": sheet[:120], "file_hash": digest,
        "rows_read": len(frame), "rows_inserted": len(new_rows), "rows_duplicated": duplicated,
        "periodo_ini": dates.min().date().isoformat() if dates.notna().any() else None,
        "periodo_fim": dates.max().date().isoformat() if dates.notna().any() else None,
    }
    res = _check(_client().post("/imports", json=header, headers={"Prefer": "return=representation"}))
    import_id = res.json()[0]["id"]

    try:
        records = [
            {"import_id": import_id, **{f: _json_value(v) for f, v in zip(fields, row)}}
            for row in new_rows[fields].itertuples(index=False, name=None)
        ]
        for start in range(0, len(records), CHUNK):
            _check(_client().post("/fiscal_items", json=records[start:start + CHUNK], headers={"Prefer": "return=minimal"}))
    except Exception:
        log.exception("Falha ao gravar itens; desfazendo o lote %s", import_id)
        delete_import(import_id)
        raise
    return SaveResult(import_id, len(frame), len(new_rows), duplicated)


def list_imports() -> list[dict]:
    rows = _get_all("imports", {"select": "*", "order": "created_at.desc,id.desc"})
    for r in rows:
        r["rows_current"] = r.get("rows_inserted", 0)
    return rows


def delete_import(import_id: int) -> bool:
    _check(_client().delete("/fiscal_items", params={"import_id": f"eq.{import_id}"}))
    res = _check(_client().delete("/imports", params={"id": f"eq.{import_id}"}, headers={"Prefer": "return=representation"}))
    return bool(res.json())


def delete_all() -> None:
    # O PostgREST exige um filtro em DELETE; id > 0 cobre todas as linhas.
    _check(_client().delete("/fiscal_items", params={"id": "gt.0"}))
    _check(_client().delete("/imports", params={"id": "gt.0"}))


def load_items() -> pd.DataFrame:
    rows = _get_all("fiscal_items", {"select": "*", "order": "id"})
    if not rows:
        return pd.DataFrame(columns=["id", "import_id", *[c.field for c in COLUMNS]])
    return pd.DataFrame(rows)
