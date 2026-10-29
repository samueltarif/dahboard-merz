"""Rotas HTTP. Cada rota só valida a entrada e chama um serviço."""
from __future__ import annotations

import datetime as dt
import math

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response

from app.api.deps import apuracao_slice, get_filters, slices
from app.config import settings
from app.domain.taxes import TAXES
from app.repositories import imports_repo
from app.services import compliance, dataset, exporter, import_service, metrics, reform
from app.services.filters import Filters

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "database": imports_repo.backend_label(), "itens": int(len(dataset.get_dataset()))}


# ---------------------------------------------------------------------------
# Importações
# ---------------------------------------------------------------------------
@router.post("/imports")
async def upload(files: list[UploadFile] = File(...)) -> dict:
    if not files:
        raise HTTPException(400, "Nenhum arquivo enviado.")
    limit = settings.max_upload_mb * 1024 * 1024
    payload: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        if len(content) > limit:
            raise HTTPException(413, f"{f.filename}: maior que {settings.max_upload_mb} MB.")
        payload.append((f.filename or "arquivo", content))
    return {"results": import_service.import_files(payload)}


@router.get("/imports")
def list_imports() -> dict:
    return {"imports": imports_repo.list_imports()}


@router.delete("/imports/{import_id}")
def remove_import(import_id: int) -> dict:
    if not imports_repo.delete_import(import_id):
        raise HTTPException(404, "Lote não encontrado.")
    dataset.invalidate()
    return {"ok": True}


@router.delete("/imports")
def remove_all() -> dict:
    imports_repo.delete_all()
    dataset.invalidate()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Dados do painel
# ---------------------------------------------------------------------------
@router.get("/meta")
def meta() -> dict:
    """Opções disponíveis para os filtros."""
    df = dataset.get_dataset()
    if df.empty:
        return {"empty": True, "empresa": settings.empresa_label, "taxes": [t.__dict__ for t in TAXES]}

    def uniq(col: str) -> list[str]:
        return sorted(v for v in df[col].dropna().astype(str).unique() if v)

    nat = df.groupby(["fluxo", "natureza"]).size().reset_index(name="n")
    return {
        "empty": False,
        "empresa": settings.empresa_label,
        "periodos": uniq("periodo"),
        "ufs": df.groupby("uf_op")["valor_total"].sum().sort_values(ascending=False).index.tolist(),
        "operacoes": [o for o in ("Interna", "Interestadual", "Exterior") if o in set(df["operacao"])],
        "naturezas": {f: nat[nat.fluxo == f].sort_values("n", ascending=False)["natureza"].tolist() for f in ("Saída", "Entrada")},
        "modelos": uniq("modelo"),
        "imports": [{"id": i["id"], "filename": i["filename"]} for i in imports_repo.list_imports()],
        "taxes": [t.__dict__ for t in TAXES],
        "atualizado_em": dt.datetime.now().isoformat(timespec="seconds"),
    }


@router.get("/overview")
def overview(filters: Filters = Depends(get_filters)) -> dict:
    df, df_sem_fluxo = slices(filters)
    return {"filters": filters.to_dict(), **metrics.overview(df, df_sem_fluxo, apuracao_slice(filters))}


@router.get("/products")
def products(filters: Filters = Depends(get_filters), limit: int = Query(25, ge=1, le=500)) -> dict:
    df, _ = slices(filters)
    return metrics.products(df, limit=limit)


@router.get("/reform")
def reform_sim(
    filters: Filters = Depends(get_filters),
    cbs_aliq: float = Query(reform.DEFAULT_CBS, ge=0, le=50),
    ibs_aliq: float = Query(reform.DEFAULT_IBS, ge=0, le=50),
) -> dict:
    df, _ = slices(filters)
    return reform.simulate(df, cbs_aliq, ibs_aliq)


@router.get("/compliance")
def compliance_checks(filters: Filters = Depends(get_filters)) -> dict:
    df, _ = slices(filters)
    return compliance.run(df)


ITEM_COLS = ["data_lancamento", "numero_nfe", "serie", "modelo", "cfop", "fluxo", "operacao", "natureza", "parceiro_nome",
             "uf_op", "material_desc", "ncm", "quantidade", "valor_total", "tx_icms", "tx_ipi", "tx_pis", "tx_cofins",
             "tx_difal", "tx_ibs", "tx_cbs", "tributos"]


@router.get("/items")
def items(
    filters: Filters = Depends(get_filters),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=500),
    sort: str = Query("valor_total"),
    desc: bool = Query(True),
) -> dict:
    df, _ = slices(filters)
    sort = sort if sort in ITEM_COLS else "valor_total"
    df = df.sort_values(sort, ascending=not desc)
    total = len(df)
    chunk = df.iloc[(page - 1) * page_size: page * page_size][ITEM_COLS].copy()
    chunk["data_lancamento"] = chunk["data_lancamento"].dt.strftime("%d/%m/%Y")
    return {"total": total, "page": page, "pages": max(1, math.ceil(total / page_size)),
            "rows": metrics.to_records(chunk)}


# ---------------------------------------------------------------------------
# Exportação
# ---------------------------------------------------------------------------
@router.get("/export")
def export(filters: Filters = Depends(get_filters), formato: str = Query("xlsx", pattern="^(xlsx|csv)$")) -> Response:
    df, df_sem_fluxo = slices(filters)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    if formato == "csv":
        return Response(exporter.to_csv(df), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="base-sap-{stamp}.csv"'})
    content = exporter.to_excel(df, df_sem_fluxo, apuracao_slice(filters), filters)
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="painel-tributario-{stamp}.xlsx"'})
