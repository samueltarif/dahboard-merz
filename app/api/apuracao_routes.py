"""Rotas da aba "Apuração & ajustes". Validam a entrada e chamam app/services/apuracao.py.

Quem está agindo vem dos cabeçalhos X-Usuario e X-Papel (sem login por enquanto).
Quando houver login, troque só `get_ator` para ler o usuário e o papel do token.
"""
from __future__ import annotations

import datetime as dt
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.services import apuracao as svc
from app.services import exporter

router = APIRouter(prefix="/api/apuracao")


def get_ator(x_usuario: str = Header(""), x_papel: str = Header("")) -> svc.Ator:
    return svc.Ator(nome=unquote(x_usuario)[:120], papel=x_papel.strip().lower())


def _run(fn, *args):
    """Converte erros de regra de negócio em respostas HTTP com mensagem em português."""
    try:
        return fn(*args)
    except svc.PermissaoNegada as exc:
        raise HTTPException(403, str(exc)) from exc
    except svc.DadoInvalido as exc:
        raise HTTPException(400, str(exc)) from exc


class LancamentoIn(BaseModel):
    tributo: str
    tipo: str
    valor: float = Field(gt=0, le=1e12)
    descricao: str = Field(min_length=1, max_length=500)
    referencia: str | None = Field(default=None, max_length=120)


class NovoLancamento(LancamentoIn):
    competencia: str
    uf: str


class SaldoIn(BaseModel):
    competencia: str
    uf: str
    tributo: str
    # Só os campos enviados são alterados; null limpa o campo.
    saldo_credor_anterior: float | None = None
    valor_declarado: float | None = None
    observacao: str | None = Field(default=None, max_length=1000)


class StatusIn(BaseModel):
    competencia: str
    uf: str
    acao: str
    motivo: str | None = Field(default=None, max_length=1000)


@router.get("/opcoes")
def opcoes() -> dict:
    return svc.opcoes()


@router.get("/competencias")
def competencias(uf: str = Query("SP")) -> dict:
    return {"competencias": svc.competencias(uf)}


@router.get("")
def painel(competencia: str, uf: str = Query("SP"), ator: svc.Ator = Depends(get_ator)) -> dict:
    return _run(svc.painel, competencia, uf, ator)


@router.post("/lancamentos")
def criar(body: NovoLancamento, ator: svc.Ator = Depends(get_ator)) -> dict:
    dados = body.model_dump(exclude={"competencia", "uf"})
    return {"lancamento": _run(svc.criar_lancamento, body.competencia, body.uf, dados, ator)}


@router.put("/lancamentos/{lanc_id}")
def alterar(lanc_id: int, body: LancamentoIn, ator: svc.Ator = Depends(get_ator)) -> dict:
    _run(svc.alterar_lancamento, lanc_id, body.model_dump(), ator)
    return {"ok": True}


@router.delete("/lancamentos/{lanc_id}")
def excluir(lanc_id: int, ator: svc.Ator = Depends(get_ator)) -> dict:
    _run(svc.excluir_lancamento, lanc_id, ator)
    return {"ok": True}


@router.put("/saldos")
def gravar_saldo(body: SaldoIn, ator: svc.Ator = Depends(get_ator)) -> dict:
    dados = body.model_dump(exclude={"competencia", "uf", "tributo"}, exclude_unset=True)
    _run(svc.gravar_saldo, body.competencia, body.uf, body.tributo, dados, ator)
    return {"ok": True}


@router.post("/status")
def mudar_status(body: StatusIn, ator: svc.Ator = Depends(get_ator)) -> dict:
    return {"status": _run(svc.mudar_status, body.competencia, body.uf, body.acao, body.motivo, ator)}


@router.get("/export")
def exportar(competencia: str, uf: str = Query("SP")) -> Response:
    content = _run(exporter.apuracao_excel, competencia, uf)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f'attachment; filename="apuracao-{uf}-{competencia}-{stamp}.xlsx"'})
