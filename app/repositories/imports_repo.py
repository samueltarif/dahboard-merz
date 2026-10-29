"""Fachada do repositório: escolhe o backend conforme a configuração.

- "sql"      -> app/repositories/sql_repo.py      (SQLite, Postgres, Supabase por connection string)
- "supabase" -> app/repositories/supabase_repo.py (Supabase pela API REST + chave de servidor)

O restante do código importa só este módulo: `from app.repositories import imports_repo`.
"""
from __future__ import annotations

from app.config import settings
from app.repositories.common import SaveResult, file_hash

if settings.storage_backend == "supabase":
    from app.repositories import supabase_repo as _backend
else:
    from app.repositories import sql_repo as _backend

ensure_schema = _backend.ensure_schema
backend_label = _backend.backend_label
find_by_hash = _backend.find_by_hash
save_import = _backend.save_import
list_imports = _backend.list_imports
delete_import = _backend.delete_import
delete_all = _backend.delete_all
load_items = _backend.load_items

__all__ = ["SaveResult", "file_hash", "ensure_schema", "backend_label", "find_by_hash", "save_import",
           "list_imports", "delete_import", "delete_all", "load_items"]
