import pytest

from app.importers.errors import ImportFileError
from app.importers.sap import parse_file
from tests.conftest import make_workbook


def test_detecta_aba_sap(sample_rows):
    parsed = parse_file("rel.xlsx", make_workbook(sample_rows))
    assert parsed.sheet == "SAP"
    assert len(parsed.frame) == 4
    assert parsed.frame["valor_total"].sum() == pytest.approx(6500.0)


def test_detecta_aba_com_outro_nome(sample_rows):
    parsed = parse_file("rel.xlsx", make_workbook(sample_rows, sheet="Planilha1"))
    assert parsed.sheet == "Planilha1"


def test_csv_formato_brasileiro():
    csv = (
        "Empresa;Data de lançamento;Nº documento;Nº item do documento;Dir.movim.mercads.;CFOP;Val.total incl.imp.;ICMS Value\n"
        "5900;01/09/2026;1;10;2;5102/AA;1.234,56;222,22\n"
    ).encode("utf-8")
    parsed = parse_file("base.csv", csv)
    row = parsed.frame.iloc[0]
    assert row["valor_total"] == pytest.approx(1234.56)
    assert row["icms_valor"] == pytest.approx(222.22)
    assert str(row["data_lancamento"]) == "2026-09-01"


def test_erros_amigaveis():
    with pytest.raises(ImportFileError, match="não suportado"):
        parse_file("velho.xls", b"x")
    with pytest.raises(ImportFileError, match="obrigatórias"):
        parse_file("x.csv", b"a;b\n1;2")
