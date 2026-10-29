"""Testa o repositório Supabase (API REST) contra um PostgREST simulado em memória."""
from __future__ import annotations

import datetime as dt
import json
from urllib.parse import parse_qsl

import httpx
import pytest

from app.repositories import supabase_repo
from tests.conftest import make_workbook


class FakePostgrest:
    """Implementa o pedaço do PostgREST que o repositório usa: select/eq/gt/order/limit/offset, insert, delete."""

    def __init__(self, tables=("imports", "fiscal_items")):
        self.tables = {t: [] for t in tables}
        self.seq = {t: 0 for t in tables}
        self.calls: list[tuple[str, str]] = []

    def _filter(self, rows, params):
        for key, value in params:
            if key in ("select", "order", "limit", "offset"):
                continue
            op, _, arg = value.partition(".")
            if op == "eq":
                rows = [r for r in rows if str(r.get(key)) == arg]
            elif op == "gt":
                rows = [r for r in rows if r.get(key) is not None and float(r[key]) > float(arg)]
        return rows

    def __call__(self, request: httpx.Request) -> httpx.Response:
        assert request.headers["apikey"] == "test-key"
        assert request.headers["authorization"] == "Bearer test-key"
        table = request.url.path.rsplit("/", 1)[-1]
        self.calls.append((request.method, table))
        if table not in self.tables:
            return httpx.Response(404, json={"code": "PGRST205", "message": f"Could not find the table 'public.{table}'"})
        params = parse_qsl(request.url.query.decode())
        rows = self.tables[table]
        if request.method == "GET":
            out = self._filter(rows, params)
            q = dict(params)
            if q.get("order", "").startswith("created_at.desc"):
                out = sorted(out, key=lambda r: (r["created_at"], r["id"]), reverse=True)
            off, lim = int(q.get("offset", 0)), int(q.get("limit", 10_000))
            out = out[off:off + lim]
            if q.get("select", "*") != "*":
                cols = q["select"].split(",")
                out = [{c: r.get(c) for c in cols} for r in out]
            return httpx.Response(200, json=out)
        if request.method == "POST":
            body = json.loads(request.content)
            body = body if isinstance(body, list) else [body]
            created = []
            for r in body:
                self.seq[table] += 1
                rec = {"id": self.seq[table], **r}
                if table == "imports":
                    rec["created_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
                rows.append(rec)
                created.append(rec)
            return httpx.Response(201, json=created if "representation" in request.headers.get("prefer", "") else None)
        if request.method == "DELETE":
            gone = self._filter(rows, params)
            self.tables[table] = [r for r in rows if r not in gone]
            return httpx.Response(200, json=gone if "representation" in request.headers.get("prefer", "") else [])
        return httpx.Response(405)


@pytest.fixture
def fake(monkeypatch):
    server = FakePostgrest()
    client = httpx.Client(base_url="https://x.supabase.co/rest/v1", transport=httpx.MockTransport(server),
                          headers={"apikey": "test-key", "Authorization": "Bearer test-key", "Content-Type": "application/json"})
    monkeypatch.setattr(supabase_repo, "_client", lambda: client)
    monkeypatch.setattr(supabase_repo, "PAGE", 3)  # força paginação mesmo com poucas linhas
    return server


def test_ciclo_completo(fake, sample_rows):
    from app.importers.sap import parse_file

    frame = parse_file("a.xlsx", make_workbook(sample_rows)).frame
    res = supabase_repo.save_import("a.xlsx", "SAP", "hash-a", frame)
    assert (res.rows_inserted, res.rows_duplicated) == (4, 0)
    assert len(fake.tables["fiscal_items"]) == 4
    assert fake.tables["fiscal_items"][0]["data_lancamento"] == "2026-09-10"   # data em ISO

    # segundo arquivo com 1 item repetido -> paginação de chaves existentes (PAGE=3)
    res2 = supabase_repo.save_import("b.xlsx", "SAP", "hash-b", frame.iloc[2:])
    assert (res2.rows_inserted, res2.rows_duplicated) == (0, 2)

    assert supabase_repo.find_by_hash("hash-a")["filename"] == "a.xlsx"
    assert supabase_repo.find_by_hash("nao-existe") is None
    assert [i["filename"] for i in supabase_repo.list_imports()] == ["b.xlsx", "a.xlsx"]

    items = supabase_repo.load_items()
    assert len(items) == 4 and items["valor_total"].sum() == pytest.approx(6500.0)

    assert supabase_repo.delete_import(res.import_id) is True
    assert supabase_repo.load_items().empty
    supabase_repo.delete_all()
    assert fake.tables["imports"] == []


def test_api_inteira_sobre_supabase(fake, monkeypatch, sample_rows, client):
    """O painel completo funciona com o backend Supabase plugado na fachada."""
    from app.repositories import imports_repo
    from app.services import dataset

    for name in ("find_by_hash", "save_import", "list_imports", "delete_import", "delete_all", "load_items"):
        monkeypatch.setattr(imports_repo, name, getattr(supabase_repo, name))
    dataset.invalidate()
    r = client.post("/api/imports", files=[("files", ("a.xlsx", make_workbook(sample_rows)))]).json()["results"][0]
    assert r["status"] == "ok" and r["rows_inserted"] == 4
    ov = client.get("/api/overview", params={"fluxo": "Saída"}).json()
    assert ov["kpis"]["valor_total"]["value"] == pytest.approx(3000.0)
    assert client.get("/api/export").status_code == 200


def test_tabela_ausente_mensagem_clara(monkeypatch):
    server = FakePostgrest(tables=())
    client = httpx.Client(base_url="https://x.supabase.co/rest/v1", transport=httpx.MockTransport(server),
                          headers={"apikey": "test-key", "Authorization": "Bearer test-key"})
    monkeypatch.setattr(supabase_repo, "_client", lambda: client)
    with pytest.raises(supabase_repo.SupabaseError, match="0001_init.sql"):
        supabase_repo.list_imports()
