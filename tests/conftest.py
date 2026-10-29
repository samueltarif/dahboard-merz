"""Configuração dos testes: banco SQLite temporário e uma planilha SAP sintética."""
from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

# O banco precisa ser definido ANTES de importar a aplicação.
_TMP = Path(tempfile.mkdtemp(prefix="painel-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'test.db').as_posix()}"

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.domain.columns import COLUMNS  # noqa: E402


def _row(doc: str, item: str, cfop: str, direcao: str, uf: str, valor: float, icms_aliq: float, **extra) -> dict:
    icms = round(valor * icms_aliq / 100, 2)
    base = {c.sap: (0 if c.kind == "num" else None) for c in COLUMNS}
    base.update({
        "Empresa": "5900", "Local de negócios": "0003", "Data documento": "2026-09-10", "Data de lançamento": "2026-09-10",
        "Nº documento": doc, "Nº item do documento": item, "Dir.movim.mercads.": direcao, "CFOP": f"{cfop}/AA",
        "Modelo nota fiscal": "55", "Chave de acesso da NF-e": f"CH{doc}", "Nº da nota fiscal eletrônica": doc,
        "ID parceiro": f"P{doc}", "Name": f"Parceiro {doc}", "País": "BR", "Região": uf, "Material": "M1",
        "Txt.brv.material": "Produto teste", "Quantidade": 1, "Código de controle": "3002.49.92", "Origem de material": "0",
        "NET Sales": valor * 0.8, "Valor": valor, "Total": valor, "Val.total incl.imp.": valor,
        "Sit.tributária ICMS": "00", "ICMS Base": valor, "ICMS Rate": icms_aliq, "ICMS Value": icms,
        "Situação fiscal PI": "01", "PIS Base": valor - icms, "PIS Rate": 1.65, "PIS Value": round((valor - icms) * 0.0165, 2),
        "SituaçãoFisc.COFINS": "01", "COFI Base": valor - icms, "COFI Rate": 7.6, "COFI Value": round((valor - icms) * 0.076, 2),
        "CBSIBS CST": "000", "CBS Base Value": valor * 0.8, "CBS Rate": 0.9, "CBS Value": round(valor * 0.8 * 0.009, 2),
        "IBS Base Value": valor * 0.8, "State IBS Rate": 0.1, "IBS Value": round(valor * 0.8 * 0.001, 2),
    })
    base.update(extra)
    return base


def make_workbook(rows: list[dict], sheet: str = "SAP", extra_sheets: bool = True) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        if extra_sheets:
            pd.DataFrame({"x": [1]}).to_excel(w, sheet_name="Resumo", index=False)
        pd.DataFrame(rows).to_excel(w, sheet_name=sheet, index=False)
    return buf.getvalue()


@pytest.fixture
def sample_rows() -> list[dict]:
    return [
        _row("1001", "10", "5102", "2", "SP", 1000.0, 18),          # venda interna
        _row("1002", "10", "6108", "2", "MG", 2000.0, 12, **{"ICMSDestVa": 120.0}),  # venda não contribuinte c/ DIFAL
        _row("1003", "10", "1556", "1", "SP", 500.0, 18),           # uso e consumo (sem crédito ICMS)
        _row("1004", "10", "2152", "1", "SC", 3000.0, 12),          # transferência (gera crédito)
    ]


@pytest.fixture
def client():
    from app.main import app
    from app.repositories import imports_repo
    from app.services import dataset

    with TestClient(app) as c:
        imports_repo.delete_all()
        dataset.invalidate()
        yield c
