"""Fachada de acesso genérico por tabela (linhas simples, filtros de igualdade).

Escolhe o mesmo backend do `imports_repo`: SQL (SQLite/Postgres) ou Supabase REST.
Usado pela apuração com ajustes manuais (`app/repositories/apuracao_repo.py`).
"""
from __future__ import annotations

from app.config import settings

if settings.storage_backend == "supabase":
    from app.repositories import supabase_repo as _backend
else:
    from app.repositories import sql_repo as _backend

rows = _backend.rows
insert_row = _backend.insert_row
update_rows = _backend.update_rows
delete_rows = _backend.delete_rows

__all__ = ["rows", "insert_row", "update_rows", "delete_rows"]
