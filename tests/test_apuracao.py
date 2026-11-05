"""Aba "Apuração & ajustes": quadro, lançamentos manuais, conciliação, papéis e status."""
from __future__ import annotations

import io
from urllib.parse import quote

import pandas as pd
import pytest

from tests.conftest import make_workbook

LANCADOR = {"X-Usuario": quote("Ana Lançadora"), "X-Papel": "lancador"}
VALIDADOR = {"X-Usuario": "Chefe", "X-Papel": "validador"}
LEITOR = {"X-Usuario": "Paulo", "X-Papel": "leitor"}
COMP = "2026-09"


@pytest.fixture
def ap(client, sample_rows):
    """Base SAP de setembro importada e tabelas da apuração vazias."""
    from sqlalchemy import delete

    from app.db.engine import get_engine
    from app.db import models

    with get_engine().begin() as conn:
        for t in (models.apuracao_lancamentos, models.apuracao_saldos, models.apuracao_competencias, models.apuracao_historico):
            conn.execute(delete(t))
    client.post("/api/imports", files=[("files", ("set.xlsx", make_workbook(sample_rows)))])
    return client


def icms(painel: dict) -> dict:
    return next(t for t in painel["quadro"] if t["tributo"] == "icms")


def get(client, comp=COMP, headers=LANCADOR):
    r = client.get("/api/apuracao", params={"competencia": comp, "uf": "SP"}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def lancar(client, headers=LANCADOR, **kw):
    body = {"competencia": COMP, "uf": "SP", "tributo": "icms", "tipo": "estorno_credito", "valor": 25.0,
            "descricao": "Estorno de crédito de uso e consumo", **kw}
    return client.post("/api/apuracao/lancamentos", json=body, headers=headers)


def test_quadro_usa_debitos_e_creditos_do_sap(ap):
    d = get(ap)
    t = icms(d)
    # saídas: 1000*18% + 2000*12% = 420 · entradas com crédito: 3000*12% = 360 (uso e consumo não credita)
    assert t["linhas"]["debito_saidas"] == pytest.approx(420.0)
    assert t["linhas"]["credito_entradas"] == pytest.approx(360.0)
    assert t["resultado"] == pytest.approx(60.0) and t["linhas"]["saldo_devedor"] == pytest.approx(60.0)
    assert d["status"]["status"] == "rascunho"
    assert d["permissoes"] == {"editar": True, "acoes": ["enviar"]}
    assert {c["id"] for c in d["checklist"]} >= {"base", "conformidade", "declarado", "diferencas", "validacao"}


def test_papel_e_nome_obrigatorios(ap):
    assert lancar(ap, headers={}).status_code == 403
    assert lancar(ap, headers={"X-Papel": "lancador"}).status_code == 403          # sem nome
    r = lancar(ap, headers=LEITOR)
    assert r.status_code == 403 and "Leitor" in r.json()["detail"]
    assert get(ap, headers=LEITOR)["permissoes"] == {"editar": False, "acoes": []}


def test_lancamentos_entram_no_quadro_e_no_historico(ap):
    r = lancar(ap)
    assert r.status_code == 200, r.text
    lanc = r.json()["lancamento"]
    assert lanc["criado_por"] == "Ana Lançadora"            # nome com acento chega certo
    lancar(ap, tipo="ajuste_credito", valor=10.0, descricao="Crédito CIAP 1/48")

    t = icms(get(ap))
    assert t["linhas"]["estorno_credito"] == pytest.approx(25.0)
    assert t["linhas"]["ajuste_credito"] == pytest.approx(10.0)
    assert t["resultado"] == pytest.approx(60 + 25 - 10)

    upd = ap.put(f"/api/apuracao/lancamentos/{lanc['id']}", headers=LANCADOR,
                 json={"tributo": "icms", "tipo": "estorno_credito", "valor": 30.0, "descricao": "Valor corrigido"})
    assert upd.status_code == 200
    assert icms(get(ap))["resultado"] == pytest.approx(60 + 30 - 10)
    assert ap.delete(f"/api/apuracao/lancamentos/{lanc['id']}", headers=LANCADOR).status_code == 200

    hist = get(ap)["historico"]
    assert [h["acao"] for h in hist][:4] == ["lancamento_excluido", "lancamento_alterado", "lancamento_criado", "lancamento_criado"]


def test_validacoes_de_entrada(ap):
    assert lancar(ap, valor=0).status_code == 422
    assert lancar(ap, tipo="qualquer").status_code == 400
    assert lancar(ap, descricao="  ").status_code == 400
    assert lancar(ap, tributo="iss").status_code == 400
    r = ap.get("/api/apuracao", params={"competencia": "2026-13"}, headers=LANCADOR)
    assert r.status_code == 400


def test_conciliacao_e_fluxo_de_validacao(ap):
    lancar(ap)                                                     # resultado ICMS = 85
    saldo = {"competencia": COMP, "uf": "SP", "tributo": "icms"}
    ap.put("/api/apuracao/saldos", headers=LANCADOR, json={**saldo, "valor_declarado": 100.0})
    t = icms(get(ap))
    assert t["diferenca"] == pytest.approx(-15.0) and t["situacao"] == "divergente"

    r = ap.post("/api/apuracao/status", headers=LANCADOR, json={**saldo, "acao": "enviar"})
    assert r.status_code == 400 and "justificativa" in r.json()["detail"]

    ap.put("/api/apuracao/saldos", headers=LANCADOR, json={**saldo, "observacao": "Ajuste manual de ICMS conforme memória"})
    assert icms(get(ap))["situacao"] == "justificada"
    assert icms(get(ap))["declarado"] == pytest.approx(100.0)           # observação não apagou o valor declarado

    assert ap.post("/api/apuracao/status", headers=LANCADOR, json={**saldo, "acao": "enviar"}).status_code == 200
    assert lancar(ap).status_code == 403                               # travado aguardando validação
    assert ap.post("/api/apuracao/status", headers=LANCADOR, json={**saldo, "acao": "validar"}).status_code == 403

    assert ap.post("/api/apuracao/status", headers=VALIDADOR, json={**saldo, "acao": "devolver"}).status_code == 400
    r = ap.post("/api/apuracao/status", headers=VALIDADOR, json={**saldo, "acao": "devolver", "motivo": "Anexar memória"})
    assert r.json()["status"]["status"] == "devolvido"
    assert lancar(ap, valor=1.0).status_code == 200                    # destravou

    ap.put("/api/apuracao/saldos", headers=LANCADOR, json={**saldo, "valor_declarado": 86.0, "observacao": None})
    assert icms(get(ap))["situacao"] == "confere"
    ap.post("/api/apuracao/status", headers=LANCADOR, json={**saldo, "acao": "enviar"})
    r = ap.post("/api/apuracao/status", headers=VALIDADOR, json={**saldo, "acao": "validar"})
    assert r.status_code == 200 and r.json()["status"]["validado_por"] == "Chefe"
    d = get(ap)
    assert next(c for c in d["checklist"] if c["id"] == "validacao")["status"] == "ok"
    assert get(ap, headers=VALIDADOR)["permissoes"]["acoes"] == ["devolver"]


def test_saldo_credor_transporta_para_o_mes_seguinte(ap):
    saldo = {"competencia": COMP, "uf": "SP", "tributo": "icms"}
    ap.put("/api/apuracao/saldos", headers=LANCADOR, json={**saldo, "saldo_credor_anterior": 200.0})
    set_ = icms(get(ap))
    assert set_["saldo_anterior_origem"] == "informado"
    assert set_["linhas"]["saldo_credor"] == pytest.approx(140.0)     # 200 - 60

    out = icms(get(ap, comp="2026-10"))                                 # outubro ainda sem base SAP
    assert out["saldo_anterior_origem"] == "transportado" and out["saldo_anterior_de"] == COMP
    assert out["linhas"]["saldo_credor_anterior"] == pytest.approx(140.0)

    ap.post("/api/apuracao/lancamentos", headers=LANCADOR, json={
        "competencia": "2026-10", "uf": "SP", "tributo": "icms", "tipo": "ajuste_debito", "valor": 50.0, "descricao": "Débito de ajuste"})
    out = icms(get(ap, comp="2026-10"))
    assert out["linhas"]["saldo_credor"] == pytest.approx(90.0)
    comps = [c["competencia"] for c in ap.get("/api/apuracao/competencias").json()["competencias"]]
    assert comps == ["2026-10", "2026-09"]


def test_exportacoes(ap):
    lancar(ap)
    r = ap.get("/api/apuracao/export", params={"competencia": COMP, "uf": "SP"})
    assert r.status_code == 200
    xls = pd.ExcelFile(io.BytesIO(r.content))
    assert xls.sheet_names == ["Quadro de apuração", "Conciliação", "Ajustes manuais", "Checklist", "Histórico"]
    assert len(pd.read_excel(xls, "Ajustes manuais")) == 1

    full = pd.ExcelFile(io.BytesIO(ap.get("/api/export").content))
    assert {"Apuração e ajustes", "Ajustes manuais"} <= set(full.sheet_names)
    assert full.sheet_names[-1] == "SAP"                                # reimportação continua funcionando
