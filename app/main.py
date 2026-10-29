"""Ponto de entrada da aplicação web (FastAPI)."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router
from app.config import settings
from app.repositories import imports_repo

WEB = Path(__file__).parent / "web"
log = logging.getLogger("painel")


@asynccontextmanager
async def lifespan(_: FastAPI):
    imports_repo.ensure_schema()
    if settings.storage_backend == "supabase":
        log.info("Armazenamento: Supabase (API REST) %s", settings.supabase_url)
    else:
        log.info("Armazenamento: %s", settings.database_url.split("@")[-1])
    yield


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(router)
    app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")
    templates = Jinja2Templates(directory=WEB / "templates")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request):
        return templates.TemplateResponse(request, "index.html", {"settings": settings})

    from app.repositories.supabase_repo import SupabaseError

    @app.exception_handler(SupabaseError)
    async def supabase_error(_: Request, exc: SupabaseError):  # tabela ausente, chave errada, etc.
        log.error("Supabase: %s", exc)
        return JSONResponse({"detail": str(exc)}, status_code=503)

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception):  # erro inesperado -> JSON legível + log
        log.exception("Erro não tratado")
        return JSONResponse({"detail": f"Erro interno: {exc}"}, status_code=500)

    return app


app = create_app()
