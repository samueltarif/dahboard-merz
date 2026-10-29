"""Definição dos tributos exibidos no painel.

Cada tributo diz de quais colunas é somado e a que grupo pertence. As métricas,
os gráficos e a exportação leem esta lista: para acrescentar um tributo novo,
basta incluí-lo aqui.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tax:
    key: str
    label: str
    sources: tuple[str, ...]
    group: str            # "consumo" (atual), "reforma" (IBS/CBS), "retido"
    hint: str = ""


TAXES: tuple[Tax, ...] = (
    Tax("icms", "ICMS", ("icms_valor",), "consumo", "ICMS próprio destacado"),
    Tax("difal", "DIFAL", ("icms_difal",), "consumo", "ICMS partilhado UF destino (EC 87/15)"),
    Tax("fcp", "FCP", ("icms_fcp_dest", "fcp_valor"), "consumo", "Fundo de Combate à Pobreza"),
    Tax("icms_st", "ICMS-ST", ("icms_st_valor", "fcp_st_valor"), "consumo", "Substituição tributária + FCP-ST"),
    Tax("ipi", "IPI", ("ipi_valor",), "consumo"),
    Tax("pis", "PIS", ("pis_valor",), "consumo"),
    Tax("cofins", "COFINS", ("cofins_valor",), "consumo"),
    Tax("ii", "II", ("ii_valor",), "consumo", "Imposto de Importação"),
    Tax("iss", "ISS", ("iss_valor", "issp_valor"), "consumo"),
    Tax("ibs", "IBS", ("ibs_valor", "ibs_mun_valor"), "reforma", "IBS UF + município (fase de teste 2026)"),
    Tax("cbs", "CBS", ("cbs_valor",), "reforma", "CBS (fase de teste 2026)"),
    Tax("retidos", "Retenções", ("pis_ret", "cofins_ret", "csll_ret", "irrf_ret"), "retido", "PIS/COFINS/CSLL/IRRF retidos"),
)

TAX_KEYS: tuple[str, ...] = tuple(t.key for t in TAXES)
CONSUMO_KEYS: tuple[str, ...] = tuple(t.key for t in TAXES if t.group == "consumo")
REFORMA_KEYS: tuple[str, ...] = tuple(t.key for t in TAXES if t.group == "reforma")
BY_KEY: dict[str, Tax] = {t.key: t for t in TAXES}

# Tributos para os quais faz sentido comparar débito (saída) x crédito (entrada).
APURAVEIS: tuple[str, ...] = ("icms", "ipi", "pis", "cofins")
