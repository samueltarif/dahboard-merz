"""Filtros do painel: um objeto só, lido da query string e aplicado ao DataFrame."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd


def _split(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass
class Filters:
    fluxo: str | None = None              # "Saída" | "Entrada"
    operacao: list[str] = field(default_factory=list)   # Interna | Interestadual | Exterior
    natureza: list[str] = field(default_factory=list)
    uf: list[str] = field(default_factory=list)
    modelo: list[str] = field(default_factory=list)     # 55 (NF-e) | 57 (CT-e)
    imports: list[int] = field(default_factory=list)
    periodo_ini: str | None = None        # "YYYY-MM"
    periodo_fim: str | None = None
    busca: str | None = None              # parceiro, material, NCM, CFOP ou nº da nota

    @classmethod
    def from_query(cls, q: dict[str, str]) -> "Filters":
        fluxo = q.get("fluxo") or None
        return cls(
            fluxo=fluxo if fluxo in ("Saída", "Entrada") else None,
            operacao=_split(q.get("operacao")),
            natureza=_split(q.get("natureza")),
            uf=_split(q.get("uf")),
            modelo=_split(q.get("modelo")),
            imports=[int(v) for v in _split(q.get("imports")) if v.isdigit()],
            periodo_ini=q.get("periodo_ini") or None,
            periodo_fim=q.get("periodo_fim") or None,
            busca=(q.get("busca") or "").strip() or None,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def apply(self, df: pd.DataFrame, *, ignore: tuple[str, ...] = ()) -> pd.DataFrame:
        """Aplica os filtros. `ignore` permite calcular totais sem um dos filtros
        (ex.: comparar Entradas x Saídas mesmo com 'Saída' selecionado)."""
        if df.empty:
            return df
        m = pd.Series(True, index=df.index)
        if self.fluxo and "fluxo" not in ignore:
            m &= df["fluxo"].eq(self.fluxo)
        if self.operacao and "operacao" not in ignore:
            m &= df["operacao"].isin(self.operacao)
        if self.natureza and "natureza" not in ignore:
            m &= df["natureza"].isin(self.natureza)
        if self.uf and "uf" not in ignore:
            m &= df["uf_op"].isin(self.uf)
        if self.modelo and "modelo" not in ignore:
            m &= df["modelo"].isin(self.modelo)
        if self.imports and "imports" not in ignore:
            m &= df["import_id"].isin(self.imports)
        if self.periodo_ini and "periodo" not in ignore:
            m &= df["periodo"].ge(self.periodo_ini)
        if self.periodo_fim and "periodo" not in ignore:
            m &= df["periodo"].le(self.periodo_fim)
        if self.busca and "busca" not in ignore:
            term = self.busca.lower()
            hay = (
                df["parceiro_nome"].str.lower() + " " + df["material_desc"].str.lower() + " "
                + df["ncm"].astype(str) + " " + df["cfop"] + " " + df["numero_nfe"].fillna("").astype(str)
                + " " + df["parceiro_cnpj"].fillna("").astype(str) + " " + df["material"].fillna("").astype(str)
            )
            m &= hay.str.contains(term, regex=False)
        return df[m]
