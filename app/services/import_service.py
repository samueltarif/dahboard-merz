"""Orquestra a importação de um ou vários arquivos."""
from __future__ import annotations

import logging

from app.importers.errors import ImportFileError
from app.importers.sap import parse_file
from app.repositories import imports_repo
from app.services import dataset

log = logging.getLogger(__name__)


def import_files(files: list[tuple[str, bytes]]) -> list[dict]:
    """Importa cada arquivo de forma independente: um erro não derruba os outros."""
    results: list[dict] = []
    for filename, content in files:
        res = {"filename": filename, "status": "ok", "message": "", "rows_read": 0, "rows_inserted": 0, "rows_duplicated": 0}
        try:
            digest = imports_repo.file_hash(content)
            already = imports_repo.find_by_hash(digest)
            if already:
                res.update(status="skipped", import_id=already["id"],
                           message=f"Arquivo idêntico já importado em {already['created_at']:%d/%m/%Y %H:%M}.")
                results.append(res)
                continue

            parsed = parse_file(filename, content)
            saved = imports_repo.save_import(filename, parsed.sheet, digest, parsed.frame)
            res.update(import_id=saved.import_id, sheet=parsed.sheet, rows_read=saved.rows_read,
                       rows_inserted=saved.rows_inserted, rows_duplicated=saved.rows_duplicated)
            msg = f"{saved.rows_inserted} itens importados da aba '{parsed.sheet}'."
            if saved.rows_duplicated:
                msg += f" {saved.rows_duplicated} já existiam e foram ignorados."
            res["message"] = msg
        except ImportFileError as exc:
            res.update(status="error", message=exc.message)
        except Exception as exc:  # noqa: BLE001 - erro inesperado vira mensagem + log completo
            log.exception("Falha ao importar %s", filename)
            res.update(status="error", message=f"Erro inesperado ao ler o arquivo: {exc}")
        results.append(res)

    if any(r["status"] == "ok" for r in results):
        dataset.invalidate()
    return results
