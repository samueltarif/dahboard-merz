"""Agregações do painel.

Cada função recebe um DataFrame já filtrado e devolve estruturas simples
(listas/dicts) prontas para virar JSON. Nenhuma função aqui conhece HTTP.
"""
from __future__ import annotations

import pandas as pd

from app.domain.taxes import APURAVEIS, BY_KEY, CONSUMO_KEYS, TAXES

MONEY = ["valor_total", "valor", "net_sales", "tributos", "tributos_reforma", *[f"tx_{t.key}" for t in TAXES]]


def _r(v: float, nd: int = 2) -> float:
    try:
        return round(float(v), nd)
    except (TypeError, ValueError):
        return 0.0


def brl(v: float) -> str:
    """1234.5 -> 'R$ 1.234,50'"""
    s = f"{float(v):,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"R$ {s}"


def pct(v: float, nd: int = 1) -> str:
    """0.2245 -> '22,4%'"""
    return f"{v * 100:.{nd}f}%".replace(".", ",")


def _ratio(a: float, b: float) -> float:
    return float(a) / float(b) if b else 0.0


def aggregate(df: pd.DataFrame, by: list[str] | str) -> pd.DataFrame:
    """Agrupa somando valores e tributos; acrescenta documentos, itens e carga."""
    by = [by] if isinstance(by, str) else by
    if df.empty:
        return pd.DataFrame(columns=[*by, "documentos", "itens", "quantidade", *MONEY, "carga"])
    g = df.groupby(by, dropna=False)
    out = g[MONEY + ["quantidade"]].sum()
    out["documentos"] = g["doc_key"].nunique()
    out["itens"] = g.size()
    out = out.reset_index()
    out["carga"] = [_ratio(t, v) for t, v in zip(out["tributos"], out["valor_total"])]
    return out


def to_records(frame: pd.DataFrame, *, limit: int | None = None) -> list[dict]:
    if limit is not None:
        frame = frame.head(limit)
    recs = []
    for row in frame.to_dict(orient="records"):
        clean = {}
        for k, v in row.items():
            key = k[3:] if k.startswith("tx_") else k
            if isinstance(v, float):
                clean[key] = round(v, 6 if key == "carga" else 2)
            elif hasattr(v, "item"):
                clean[key] = v.item()
            else:
                clean[key] = v
        recs.append(clean)
    return recs


# ---------------------------------------------------------------------------
# Indicadores principais
# ---------------------------------------------------------------------------
def _series(df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """Série temporal para os mini-gráficos: por mês se houver >1 mês, senão por dia."""
    if df["periodo"].nunique() > 1:
        return "periodo", aggregate(df, "periodo").sort_values("periodo")
    return "dia", aggregate(df, "dia").sort_values("dia")


def kpis(df: pd.DataFrame) -> dict:
    total = float(df["valor_total"].sum())
    trib = float(df["tributos"].sum())
    grain, ser = _series(df) if not df.empty else ("dia", pd.DataFrame())

    def spark(col: str) -> list[float]:
        return [] if ser.empty else [_r(v) for v in ser[col]]

    def delta(col: str) -> float | None:
        if grain != "periodo" or len(ser) < 2:
            return None
        prev, last = float(ser[col].iloc[-2]), float(ser[col].iloc[-1])
        return _r(_ratio(last - prev, abs(prev)) * 100, 1) if prev else None

    docs = int(df["doc_key"].nunique()) if not df.empty else 0
    return {
        "grain": grain,
        "labels": [] if ser.empty else ser[grain].tolist(),
        "valor_total": {"value": _r(total), "spark": spark("valor_total"), "delta": delta("valor_total")},
        "tributos": {"value": _r(trib), "spark": spark("tributos"), "delta": delta("tributos")},
        "carga": {"value": _ratio(trib, total), "spark": [] if ser.empty else [round(x, 6) for x in ser["carga"]]},
        "documentos": {"value": docs, "spark": [] if ser.empty else [int(x) for x in ser["documentos"]]},
        "itens": int(len(df)),
        "parceiros": int(df["parceiro_id"].nunique()) if not df.empty else 0,
        "ticket_medio": _r(_ratio(total, docs)),
        "net_sales": _r(df["net_sales"].sum()),
        "valor_produtos": _r(df["valor"].sum()),
        "tributos_reforma": _r(df["tributos_reforma"].sum()),
    }


def taxes(df: pd.DataFrame) -> list[dict]:
    total_consumo = float(df["tributos"].sum()) if not df.empty else 0.0
    out = []
    for t in TAXES:
        value = float(df[f"tx_{t.key}"].sum()) if not df.empty else 0.0
        out.append({
            "key": t.key, "label": t.label, "group": t.group, "hint": t.hint, "value": _r(value),
            "share": _ratio(value, total_consumo) if t.key in CONSUMO_KEYS else None,
            "base_carga": _ratio(value, float(df["valor_total"].sum())) if not df.empty else 0.0,
        })
    return out


def apuracao(df_sem_fluxo: pd.DataFrame) -> list[dict]:
    """Débitos (saídas) x créditos (entradas) destacados - visão gerencial."""
    out = []
    if df_sem_fluxo.empty:
        return out
    saidas = df_sem_fluxo[df_sem_fluxo["fluxo"].eq("Saída")]
    entradas = df_sem_fluxo[df_sem_fluxo["fluxo"].eq("Entrada")]
    for key in APURAVEIS:
        col = f"tx_{key}"
        debito = float(saidas[col].sum())
        ent = entradas[entradas["gera_credito_icms_ipi"]] if key in ("icms", "ipi") else entradas
        credito = float(ent[col].sum())
        sem_credito = float(entradas[col].sum()) - credito
        out.append({
            "key": key, "label": BY_KEY[key].label, "debito": _r(debito), "credito": _r(credito),
            "sem_credito": _r(sem_credito), "saldo": _r(debito - credito),
        })
    return out


def insights(df: pd.DataFrame, apur: list[dict]) -> list[dict]:
    """Frases curtas para apoiar decisão. Só entram as que têm dado para sustentar."""
    notes: list[dict] = []
    if df.empty:
        return notes
    total = float(df["valor_total"].sum())
    trib = float(df["tributos"].sum())
    if total:
        notes.append({"tone": "neutral", "text": f"Carga efetiva de {pct(_ratio(trib, total))} sobre o valor total dos documentos."})

    tx = sorted(taxes(df), key=lambda t: t["value"], reverse=True)
    top = next((t for t in tx if t["group"] == "consumo" and t["value"] > 0), None)
    if top and trib:
        notes.append({"tone": "neutral", "text": f"{top['label']} responde por {pct(top['value'] / trib, 0)} dos tributos sobre consumo."})

    difal = df[df["tx_difal"] > 0]
    if not difal.empty:
        by_uf = difal.groupby("uf_op")["tx_difal"].sum().sort_values(ascending=False)
        notes.append({"tone": "warn", "text": f"DIFAL concentrado em {by_uf.index[0]} ({pct(by_uf.iloc[0] / by_uf.sum(), 0)} do total): vendas a não contribuintes."})

    parts = df.groupby("parceiro_nome")["valor_total"].sum().sort_values(ascending=False)
    if len(parts) >= 5 and total:
        notes.append({"tone": "neutral", "text": f"Os 5 maiores parceiros somam {pct(parts.head(5).sum() / total, 0)} do valor."})

    icms = next((a for a in apur if a["key"] == "icms"), None)
    if icms and (icms["debito"] or icms["credito"]):
        tone = "warn" if icms["saldo"] > 0 else "good"
        word = "a recolher" if icms["saldo"] > 0 else "credor"
        notes.append({"tone": tone, "text": f"Saldo estimado de ICMS {word}: {brl(abs(icms['saldo']))} (débitos − créditos destacados)."})
    return notes


def overview(df: pd.DataFrame, df_sem_fluxo: pd.DataFrame, df_apuracao: pd.DataFrame | None = None) -> dict:
    """Tudo que a tela principal precisa num único payload.

    df            -> base com todos os filtros
    df_sem_fluxo  -> mesma base sem o filtro de movimento (tabela Entradas x Saídas)
    df_apuracao   -> base sem movimento e natureza (débitos x créditos)
    """
    apur = apuracao(df_sem_fluxo if df_apuracao is None else df_apuracao)
    by_uf = aggregate(df, ["uf_op"]).sort_values("valor_total", ascending=False)
    by_cfop = aggregate(df, ["cfop", "natureza_operacao", "fluxo", "operacao", "natureza"]).sort_values(["cfop"])
    timeline = aggregate(df, "dia").sort_values("dia")
    flux = aggregate(df_sem_fluxo, "fluxo").sort_values("fluxo", ascending=False)
    return {
        "kpis": kpis(df),
        "taxes": taxes(df),
        "apuracao": apur,
        "insights": insights(df, apur),
        "flux": to_records(flux),
        "by_operacao": to_records(aggregate(df, ["fluxo", "operacao"]).sort_values(["fluxo", "valor_total"], ascending=[False, False])),
        "by_natureza": to_records(aggregate(df, ["fluxo", "natureza"]).sort_values("valor_total", ascending=False)),
        "by_uf": to_records(by_uf),
        "by_cfop": to_records(by_cfop),
        "timeline": to_records(timeline),
        "by_periodo": to_records(aggregate(df, "periodo").sort_values("periodo")),
    }


def products(df: pd.DataFrame, limit: int = 25) -> dict:
    mat = aggregate(df, ["material", "material_desc", "ncm"]).sort_values("valor_total", ascending=False)
    mat["preco_medio"] = [_ratio(v, q) for v, q in zip(mat["valor_total"], mat["quantidade"])]
    par = aggregate(df, ["parceiro_id", "parceiro_nome", "uf_op"]).sort_values("valor_total", ascending=False)
    ncm = aggregate(df, ["ncm"]).sort_values("valor_total", ascending=False)
    total = float(df["valor_total"].sum()) if not df.empty else 0.0
    # Curva ABC de parceiros (acumulado do valor)
    abc = []
    if total:
        acc = 0.0
        for i, v in enumerate(par["valor_total"].tolist(), start=1):
            acc += v
            abc.append({"rank": i, "share_acum": round(acc / total, 6)})
    return {
        "materiais": to_records(mat, limit=limit),
        "parceiros": to_records(par, limit=limit),
        "ncm": to_records(ncm, limit=limit),
        "abc_parceiros": abc,
        "totais": {"materiais": int(len(mat)), "parceiros": int(len(par)), "ncm": int(len(ncm)), "valor_total": _r(total)},
    }
