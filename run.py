"""Inicia o painel:  python run.py   (abre em http://127.0.0.1:8000)"""
import webbrowser
from threading import Timer

import uvicorn

from app.config import settings

if __name__ == "__main__":
    url = f"http://{settings.host}:{settings.port}"
    banco = f"Supabase (API) {settings.supabase_url}" if settings.storage_backend == "supabase" else settings.database_url.split("@")[-1]
    print(f"\n  Painel tributário rodando em {url}\n  Banco: {banco}\n  Ctrl+C para parar.\n")
    if settings.host in ("127.0.0.1", "localhost"):
        Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False, log_level="info")
