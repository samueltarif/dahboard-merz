"""Verificações de conformidade item a item.

Cada regra é um `Check` com uma máscara (quais linhas violam) e um texto
explicativo. Para criar uma regra nova basta acrescentar um Check na lista.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from app.services.metrics import to_records

TOL = 0.05  # tolerância de arredondamento em R$


@dataclass(frozen=True)
class Check:
    id: str
    title: str
    detail: str
    severity: str  # "alta" | "media" | "info"
    mask: Callable[[pd.DataFrame], pd.Series]
    value: Callable[[pd.DataFrame], pd.Series]
    extra_cols: tuple[str, ...] = ()


def _recalc(base: str, aliq: str, valor: str, red: str | None = None) -> Callable[[pd.DataFrame], pd.Series]:
    def f(df: pd.DataFrame) -> pd.Series:
        fator = 1 - df[red] / 100 if red else 1
        esperado = df[base] * df[aliq] / 100 * fator
        return (esperado - df[valor]).abs() > TOL
    return f


def _diff(base: str, aliq: str, valor: str, red: str | None = None) -> Callable[[pd.DataFrame], pd.Series]:
    def f(df: pd.DataFrame) -> pd.Series:
        fator = 1 - df[red] / 100 if red else 1
        return (df[base] * df[aliq] / 100 * fator - df[valor]).abs()
    return f


def _month(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, errors="coerce").dt.strftime("%Y-%m")


CHECKS: tuple[Check, ...] = (
    Check("icms_calc", "ICMS ≠ base × alíquota", "Valor do ICMS diverge do recálculo base × alíquota.", "alta",
          _recalc("icms_base", "icms_aliq", "icms_valor"), _diff("icms_base", "icms_aliq", "icms_valor"),
          ("icms_base", "icms_aliq", "icms_valor")),
    Check("ipi_calc", "IPI ≠ base × alíquota", "Valor do IPI diverge do recálculo.", "alta",
          _recalc("ipi_base", "ipi_aliq", "ipi_valor"), _diff("ipi_base", "ipi_aliq", "ipi_valor"),
          ("ipi_base", "ipi_aliq", "ipi_valor")),
    Check("pis_calc", "PIS ≠ base × alíquota", "Valor do PIS diverge do recálculo.", "alta",
          _recalc("pis_base", "pis_aliq", "pis_valor"), _diff("pis_base", "pis_aliq", "pis_valor"),
          ("pis_base", "pis_aliq", "pis_valor")),
    Check("cofins_calc", "COFINS ≠ base × alíquota", "Valor da COFINS diverge do recálculo.", "alta",
          _recalc("cofins_base", "cofins_aliq", "cofins_valor"), _diff("cofins_base", "cofins_aliq", "cofins_valor"),
          ("cofins_base", "cofins_aliq", "cofins_valor")),
    Check("ibs_calc", "IBS ≠ base × alíquota × (1 − redução)", "IBS destacado diverge do recálculo com a redução de alíquota.", "media",
          _recalc("ibs_base", "ibs_aliq", "ibs_valor", "ibs_red"), _diff("ibs_base", "ibs_aliq", "ibs_valor", "ibs_red"),
          ("ibs_base", "ibs_aliq", "ibs_red", "ibs_valor")),
    Check("cbs_calc", "CBS ≠ base × alíquota × (1 − redução)", "CBS destacada diverge do recálculo com a redução de alíquota.", "media",
          _recalc("cbs_base", "cbs_aliq", "cbs_valor", "cbs_red"), _diff("cbs_base", "cbs_aliq", "cbs_valor", "cbs_red"),
          ("cbs_base", "cbs_aliq", "cbs_red", "cbs_valor")),
    Check("cst_isento_com_icms", "CST isento/não tributado com ICMS", "CST ICMS 30/40/41/50/60 com valor de ICMS destacado.", "alta",
          lambda d: d["cst_icms"].isin(["30", "40", "41", "50", "60"]) & (d["icms_valor"] > TOL),
          lambda d: d["icms_valor"], ("cst_icms", "icms_valor")),
    Check("cst00_sem_icms", "CST 00 sem ICMS na saída", "Saída com CST 00 (tributada integralmente) e ICMS zerado.", "media",
          lambda d: d["fluxo"].eq("Saída") & d["cst_icms"].eq("00") & (d["icms_valor"] <= TOL) & (d["valor_total"] > 0),
          lambda d: d["valor_total"], ("cst_icms", "icms_base", "icms_valor")),
    Check("difal_ausente", "Venda a não contribuinte sem DIFAL", "CFOP 6107/6108 com ICMS e sem DIFAL (EC 87/15).", "alta",
          lambda d: d["cfop"].isin(["6107", "6108"]) & (d["icms_valor"] > TOL) & (d["tx_difal"] <= TOL),
          lambda d: d["valor_total"], ("cfop", "icms_valor", "tx_difal")),
    Check("aliq_4_importado", "Importado em operação interestadual fora dos 4%", "Origem 1/2/3/8 em saída interestadual com alíquota ≠ 4% (Res. SF 13/2012).", "alta",
          lambda d: d["fluxo"].eq("Saída") & d["operacao"].eq("Interestadual") & d["origem_material"].isin(["1", "2", "3", "8"])
          & (d["icms_valor"] > TOL) & ((d["icms_aliq"] - 4).abs() > 0.001),
          lambda d: d["icms_valor"], ("origem_material", "icms_aliq", "icms_valor")),
    Check("pis_base_com_icms", "PIS/COFINS sem exclusão do ICMS da base", "CST 01/02 com base de PIS igual ao valor do item mesmo havendo ICMS (Tema 69 STF).", "media",
          lambda d: d["fluxo"].eq("Saída") & d["cst_pis"].isin(["01", "02"]) & (d["icms_valor"] > TOL)
          & ((d["pis_base"] - d["valor"]).abs() <= TOL),
          lambda d: d["icms_valor"] * 0.0925, ("pis_base", "valor", "icms_valor")),
    Check("sem_chave", "Documento eletrônico sem chave de acesso", "Modelo 55/57 sem chave de acesso informada.", "media",
          lambda d: d["modelo"].isin(["55", "57"]) & d["chave_acesso"].isna(),
          lambda d: d["valor_total"], ("modelo", "numero_nfe")),
    Check("extemporaneo", "Documento de outro mês lançado no período", "Data do documento em mês diferente da data de lançamento (comum em CT-e e entradas).", "info",
          lambda d: _month(d["data_documento"]).ne(_month(d["data_lancamento"])) & d["data_documento"].notna(),
          lambda d: d["valor_total"], ("data_documento", "data_lancamento")),
)

BASE_COLS = ("numero_nfe", "serie", "modelo", "cfop", "fluxo", "parceiro_nome", "uf_op", "material_desc", "valor_total")


def run(df: pd.DataFrame, sample: int = 50) -> dict:
    results = []
    for chk in CHECKS:
        if df.empty:
            mask = pd.Series(dtype=bool)
        else:
            mask = chk.mask(df).fillna(False).astype(bool)
        hits = df[mask] if not df.empty else df
        valor = float(chk.value(hits).sum()) if not hits.empty else 0.0
        cols = list(dict.fromkeys([*BASE_COLS, *chk.extra_cols]))
        rows = hits[cols].copy() if not hits.empty else pd.DataFrame(columns=cols)
        for c in ("data_documento", "data_lancamento"):
            if c in rows:
                rows[c] = pd.to_datetime(rows[c]).dt.strftime("%d/%m/%Y")
        results.append({
            "id": chk.id, "title": chk.title, "detail": chk.detail, "severity": chk.severity,
            "count": int(mask.sum()) if len(mask) else 0, "documentos": int(hits["doc_key"].nunique()) if not hits.empty else 0,
            "valor": round(valor, 2), "columns": cols, "rows": to_records(rows, limit=sample),
        })
    order = {"alta": 0, "media": 1, "info": 2}
    results.sort(key=lambda r: (r["count"] == 0, order[r["severity"]], -r["count"]))
    alerts = [r for r in results if r["count"] and r["severity"] != "info"]
    return {
        "checks": results,
        "resumo": {
            "itens_analisados": int(len(df)),
            "regras": len(CHECKS),
            "regras_com_alerta": len(alerts),
            "itens_com_alerta": int(sum(r["count"] for r in alerts)),
        },
    }
