"""Reforma tributária (EC 132/2023, LC 214/2025): IBS/CBS.

1) Mostra o IBS/CBS já destacado nos documentos (fase de teste 2026: CBS 0,9% e IBS 0,1%).
2) Simula o cenário pleno com alíquotas informadas pelo usuário, aplicando a
   redução de alíquota que o SAP já calcula por item (cClassTrib).

É uma estimativa gerencial: a base usada é a base IBS/CBS do SAP (ou o NET Sales
quando a base não veio preenchida) e as alíquotas de referência ainda serão
fixadas pelo Senado. Ajuste os parâmetros na tela.
"""
from __future__ import annotations

import pandas as pd

from app.services.metrics import _r, _ratio, to_records

CST_DESC = {
    "000": "Tributação integral",
    "200": "Alíquota reduzida",
    "410": "Imunidade e não incidência",
}

# Tributos atuais que o IBS/CBS substituem ao fim da transição (2033).
SUBSTITUIDOS = ("tx_icms", "tx_difal", "tx_fcp", "tx_pis", "tx_cofins", "tx_iss")

DEFAULT_CBS = 8.8
DEFAULT_IBS = 17.7


def simulate(df: pd.DataFrame, cbs_aliq: float = DEFAULT_CBS, ibs_aliq: float = DEFAULT_IBS) -> dict:
    if df.empty:
        return {"params": {"cbs_aliq": cbs_aliq, "ibs_aliq": ibs_aliq}, "teste_2026": {}, "simulacao": {}, "por_cst": [], "por_material": []}

    d = df.copy()
    base_cbs = d["cbs_base"].where(d["cbs_base"] > 0, d["net_sales"])
    base_ibs = d["ibs_base"].where(d["ibs_base"] > 0, d["net_sales"])
    # Itens imunes/não incidentes (CST 410) não geram IBS/CBS.
    nao_incide = d["cst_ibscbs"].fillna("").eq("410")
    d["sim_cbs"] = (base_cbs * cbs_aliq / 100 * (1 - d["cbs_red"] / 100)).where(~nao_incide, 0.0)
    d["sim_ibs"] = (base_ibs * ibs_aliq / 100 * (1 - d["ibs_red"] / 100)).where(~nao_incide, 0.0)
    d["sim_total"] = d["sim_cbs"] + d["sim_ibs"]
    d["atual_substituidos"] = d[list(SUBSTITUIDOS)].sum(axis=1)
    d["cst_desc"] = d["cst_ibscbs"].fillna("—").map(lambda c: f"{c} · {CST_DESC.get(c, 'Outros')}")

    valor_total = float(d["valor_total"].sum())
    atual = float(d["atual_substituidos"].sum())
    sim = float(d["sim_total"].sum())

    teste = {
        "base_cbs": _r(d["cbs_base"].sum()), "base_ibs": _r(d["ibs_base"].sum()),
        "cbs": _r(d["tx_cbs"].sum()), "ibs": _r(d["tx_ibs"].sum()),
        "total": _r(d["tributos_reforma"].sum()),
        "itens_com_reducao": int((d["cbs_red"] > 0).sum()),
    }
    simulacao = {
        "atual_substituidos": _r(atual), "ipi": _r(d["tx_ipi"].sum()),
        "cbs": _r(d["sim_cbs"].sum()), "ibs": _r(d["sim_ibs"].sum()), "total": _r(sim),
        "variacao": _r(sim - atual), "variacao_pct": _ratio(sim - atual, atual),
        "carga_atual": _ratio(atual, valor_total), "carga_simulada": _ratio(sim, valor_total),
    }

    g = d.groupby("cst_desc")
    por_cst = pd.DataFrame({
        "itens": g.size(), "valor_total": g["valor_total"].sum(), "base": g["cbs_base"].sum(),
        "ibs_cbs_2026": g["tributos_reforma"].sum(), "atual": g["atual_substituidos"].sum(), "simulado": g["sim_total"].sum(),
    }).reset_index().sort_values("valor_total", ascending=False)

    gm = d.groupby(["material_desc", "class_trib"], dropna=False)
    por_mat = pd.DataFrame({
        "valor_total": gm["valor_total"].sum(), "reducao": gm["cbs_red"].max(),
        "atual": gm["atual_substituidos"].sum(), "simulado": gm["sim_total"].sum(),
    }).reset_index()
    por_mat["variacao"] = por_mat["simulado"] - por_mat["atual"]
    por_mat = por_mat.sort_values("valor_total", ascending=False)

    return {
        "params": {"cbs_aliq": cbs_aliq, "ibs_aliq": ibs_aliq},
        "teste_2026": teste,
        "simulacao": simulacao,
        "por_cst": to_records(por_cst),
        "por_material": to_records(por_mat, limit=20),
    }
