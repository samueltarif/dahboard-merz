import pytest

from tests.conftest import _row, make_workbook


def _upload(client, *files):
    return client.post("/api/imports", files=[("files", (name, content)) for name, content in files]).json()["results"]


def test_importa_varios_arquivos_e_ignora_duplicados(client, sample_rows):
    a = make_workbook(sample_rows[:2])
    b = make_workbook(sample_rows[1:])  # 1 item repetido
    res = _upload(client, ("a.xlsx", a), ("b.xlsx", b))
    assert [r["status"] for r in res] == ["ok", "ok"]
    assert res[1]["rows_duplicated"] == 1
    assert _upload(client, ("a-de-novo.xlsx", a))[0]["status"] == "skipped"
    assert client.get("/api/health").json()["itens"] == 4


def test_overview_e_apuracao(client, sample_rows):
    _upload(client, ("a.xlsx", make_workbook(sample_rows)))
    d = client.get("/api/overview", params={"fluxo": "Saída"}).json()
    assert d["kpis"]["valor_total"]["value"] == pytest.approx(3000.0)
    icms = next(a for a in d["apuracao"] if a["key"] == "icms")
    assert icms["debito"] == pytest.approx(180 + 240)
    assert icms["credito"] == pytest.approx(360)      # transferência
    assert icms["sem_credito"] == pytest.approx(90)   # uso e consumo
    assert {r["fluxo"] for r in d["flux"]} == {"Saída", "Entrada"}


def test_filtros_uf_e_busca(client, sample_rows):
    _upload(client, ("a.xlsx", make_workbook(sample_rows)))
    assert client.get("/api/items", params={"uf": "MG"}).json()["total"] == 1
    assert client.get("/api/items", params={"busca": "parceiro 1004"}).json()["total"] == 1


def test_conformidade_detecta_difal_ausente(client, sample_rows):
    sem_difal = _row("2001", "10", "6108", "2", "BA", 1000.0, 12)
    _upload(client, ("a.xlsx", make_workbook([*sample_rows, sem_difal])))
    checks = {c["id"]: c for c in client.get("/api/compliance").json()["checks"]}
    assert checks["difal_ausente"]["count"] == 1
    assert checks["icms_calc"]["count"] == 0


def test_exportacao_reimportavel(client, sample_rows):
    _upload(client, ("a.xlsx", make_workbook(sample_rows)))
    xlsx = client.get("/api/export").content
    csv = client.get("/api/export", params={"formato": "csv"}).content
    client.delete("/api/imports")
    assert _upload(client, ("export.xlsx", xlsx))[0]["rows_inserted"] == 4
    client.delete("/api/imports")
    assert _upload(client, ("export.csv", csv))[0]["rows_inserted"] == 4


def test_reforma(client, sample_rows):
    _upload(client, ("a.xlsx", make_workbook(sample_rows)))
    r = client.get("/api/reform", params={"fluxo": "Saída", "cbs_aliq": 10, "ibs_aliq": 0}).json()
    assert r["simulacao"]["cbs"] == pytest.approx(3000 * 0.8 * 0.10)


def test_remover_lote(client, sample_rows):
    res = _upload(client, ("a.xlsx", make_workbook(sample_rows)))
    assert client.delete(f"/api/imports/{res[0]['import_id']}").json()["ok"]
    assert client.get("/api/meta").json()["empty"] is True
