"""Configuração central da aplicação.

Tudo que muda entre ambientes (banco, porta, limites) vem de variáveis de
ambiente ou do arquivo `.env`. Para trocar SQLite local -> Postgres (Docker)
-> Supabase basta mudar `DATABASE_URL`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Carrega um `.env` simples (CHAVE=valor) sem depender de bibliotecas."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def _default_sqlite_url() -> str:
    # No Vercel só /tmp é gravável. Localmente continua usando data/.
    base = Path("/tmp") if os.getenv("VERCEL") else BASE_DIR / "data"
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError:
        base = Path("/tmp")
        base.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(base / 'dashboard.db').as_posix()}"


@dataclass(frozen=True)
class Settings:
    app_name: str = "Painel Tributário"
    empresa_label: str = os.getenv("EMPRESA_LABEL", "Filial SP")
    database_url: str = os.getenv("DATABASE_URL") or _default_sqlite_url()
    database_url_is_default: bool = not os.getenv("DATABASE_URL")

    # --- Supabase via API REST (usa as chaves do painel: Settings > API Keys) ---
    supabase_url: str = os.getenv("SUPABASE_URL", "").rstrip("/")
    # Chave de servidor (service_role ou sb_secret_...). Fica só no servidor, nunca vai ao navegador.
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    # Guardadas para quando houver login (Supabase Auth); o painel ainda não usa.
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_jwt_secret: str = os.getenv("SUPABASE_JWT_SECRET", "")
    # "auto" (padrão): usa Supabase REST se SUPABASE_URL + chave existirem e DATABASE_URL não;
    # "sql": força DATABASE_URL (SQLite/Postgres/Supabase via connection string);
    # "supabase": força a API REST do Supabase.
    storage_backend_cfg: str = os.getenv("STORAGE_BACKEND", "auto").lower()
    host: str = os.getenv("HOST", "127.0.0.1")
    port: int = int(os.getenv("PORT", "8000"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "80"))
    # Nome preferido da aba com os dados do SAP. Se não existir, o importador
    # procura qualquer aba que tenha as colunas obrigatórias.
    sap_sheet_names: tuple[str, ...] = field(default_factory=lambda: ("SAP", "sap", "Sap"))


    @property
    def storage_backend(self) -> str:
        if self.storage_backend_cfg in ("sql", "supabase"):
            return self.storage_backend_cfg
        has_rest = bool(self.supabase_url and self.supabase_service_key)
        return "supabase" if has_rest and self.database_url_is_default else "sql"


settings = Settings()
