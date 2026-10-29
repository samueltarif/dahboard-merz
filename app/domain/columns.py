"""Mapa único das colunas do relatório SAP (J1BNFE / livro fiscal) -> campos internos.

Esta é a ÚNICA fonte da verdade sobre colunas. O importador, a tabela do banco
e a exportação são gerados a partir daqui. Se o SAP mudar o nome de uma coluna,
basta acrescentar o novo nome em `aliases`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Kind = Literal["text", "date", "num"]


@dataclass(frozen=True)
class Col:
    field: str            # nome interno (snake_case) usado no banco e no código
    sap: str              # cabeçalho no SAP
    kind: Kind = "text"
    label: str = ""       # rótulo para exportação/tela (padrão = cabeçalho SAP)
    aliases: tuple[str, ...] = ()
    required: bool = False

    @property
    def headers(self) -> tuple[str, ...]:
        return (self.sap, *self.aliases)

    @property
    def display(self) -> str:
        return self.label or self.sap


COLUMNS: tuple[Col, ...] = (
    # --- Identificação do documento ---------------------------------------
    Col("empresa", "Empresa", required=True),
    Col("local_negocio", "Local de negócios"),
    Col("data_documento", "Data documento", "date", "Data do documento"),
    Col("data_lancamento", "Data de lançamento", "date", "Data de lançamento", required=True),
    Col("categoria_nf", "Ctg.nota fiscal", label="Categoria NF"),
    Col("numero_documento", "Nº documento", label="Nº documento SAP", required=True),
    Col("item_documento", "Nº item do documento", label="Item", required=True),
    Col("estornado", "Estornado"),
    Col("direcao", "Dir.movim.mercads.", label="Direção (1=entrada, 2=saída)", required=True),
    Col("natureza_operacao", "Natureza da Operação", label="Natureza da operação"),
    Col("cfop_raw", "CFOP", label="CFOP (SAP)", required=True),
    Col("modelo", "Modelo nota fiscal", label="Modelo"),
    Col("chave_acesso", "Chave de acesso da NF-e", label="Chave de acesso"),
    Col("numero_nfe", "Nº da nota fiscal eletrônica", label="Nº NF-e/CT-e"),
    Col("serie", "Séries", label="Série"),
    # --- Parceiro -------------------------------------------------------------
    Col("parceiro_id", "ID parceiro", label="ID parceiro"),
    Col("parceiro_nome", "Name", label="Parceiro", aliases=("Nome",)),
    Col("parceiro_cnpj", "CPF/CNPJ"),
    Col("pais", "País"),
    Col("cidade", "Cidade"),
    Col("uf", "Região", label="UF"),
    # --- Item -----------------------------------------------------------------
    Col("pedido", "Pedido"),
    Col("centro_lucro", "Centro de lucro"),
    Col("material", "Material"),
    Col("material_desc", "Txt.brv.material", label="Descrição do material"),
    Col("quantidade", "Quantidade", "num"),
    Col("ncm", "Código de controle", label="NCM"),
    Col("origem_material", "Origem de material", label="Origem"),
    # --- Valores --------------------------------------------------------------
    Col("net_sales", "NET Sales", "num", "Receita líquida (NET)"),
    Col("valor", "Valor", "num", "Valor dos produtos"),
    Col("frete", "Frete", "num"),
    Col("seguro", "Seguros", "num", "Seguro"),
    Col("despesas", "Despesas", "num"),
    Col("total", "Total", "num"),
    Col("valor_total", "Val.total incl.imp.", "num", "Valor total c/ impostos", required=True),
    # --- IPI ------------------------------------------------------------------
    Col("cst_ipi", "Sit.tributária IPI", label="CST IPI"),
    Col("ipi_base", "IPI Base", "num", "Base IPI"),
    Col("ipi_aliq", "IPI Rate", "num", "Alíq. IPI"),
    Col("ipi_valor", "IPI Value", "num", "IPI"),
    # --- ICMS -----------------------------------------------------------------
    Col("cst_icms", "Sit.tributária ICMS", label="CST ICMS"),
    Col("icms_base", "ICMS Base", "num", "Base ICMS"),
    Col("icms_aliq", "ICMS Rate", "num", "Alíq. ICMS"),
    Col("icms_valor", "ICMS Value", "num", "ICMS"),
    Col("icms_difal", "ICMSDestVa", "num", "DIFAL (ICMS UF destino)"),
    Col("icms_fcp_dest", "ICMSFundVl", "num", "FCP UF destino"),
    Col("fcp_valor", "FCP Value", "num", "FCP"),
    Col("icms_st_valor", "ICST Value", "num", "ICMS-ST"),
    Col("fcp_st_valor", "FCPST Vl", "num", "FCP-ST"),
    # --- PIS / COFINS -----------------------------------------------------------
    Col("cst_pis", "Situação fiscal PI", label="CST PIS"),
    Col("pis_base", "PIS Base", "num", "Base PIS"),
    Col("pis_aliq", "PIS Rate", "num", "Alíq. PIS"),
    Col("pis_valor", "PIS Value", "num", "PIS"),
    Col("cst_cofins", "SituaçãoFisc.COFINS", label="CST COFINS"),
    Col("cofins_base", "COFI Base", "num", "Base COFINS"),
    Col("cofins_aliq", "COFI Rate", "num", "Alíq. COFINS"),
    Col("cofins_valor", "COFI Value", "num", "COFINS"),
    # --- Outros tributos --------------------------------------------------------
    Col("ii_valor", "II Value", "num", "II"),
    Col("iss_valor", "ISSS Value", "num", "ISS"),
    Col("issp_valor", "ISSP Value", "num", "ISS (prestador)"),
    Col("pis_ret", "PISWH VL", "num", "PIS retido"),
    Col("cofins_ret", "COFWH VL", "num", "COFINS retido"),
    Col("csll_ret", "CSLLW VL", "num", "CSLL retida"),
    Col("irrf_ret", "IRRFWH Val", "num", "IRRF retido"),
    # --- Reforma tributária (IBS/CBS) ------------------------------------------
    Col("cst_ibscbs", "CBSIBS CST", label="CST IBS/CBS"),
    Col("class_trib", "Tax Clfn", label="cClassTrib"),
    Col("ibs_base", "IBS Base Value", "num", "Base IBS"),
    Col("ibs_valor", "IBS Value", "num", "IBS UF"),
    Col("ibs_aliq", "State IBS Rate", "num", "Alíq. IBS UF"),
    Col("ibs_red", "Rate Reduction Percentage for State IBS", "num", "Redução IBS %"),
    Col("ibs_mun_valor", "IBSMun Value", "num", "IBS Município"),
    Col("cbs_base", "CBS Base Value", "num", "Base CBS"),
    Col("cbs_valor", "CBS Value", "num", "CBS"),
    Col("cbs_aliq", "CBS Rate", "num", "Alíq. CBS"),
    Col("cbs_red", "CBS Rate Reduction", "num", "Redução CBS %"),
)

BY_FIELD: dict[str, Col] = {c.field: c for c in COLUMNS}
NUMERIC_FIELDS: tuple[str, ...] = tuple(c.field for c in COLUMNS if c.kind == "num")
DATE_FIELDS: tuple[str, ...] = tuple(c.field for c in COLUMNS if c.kind == "date")
TEXT_FIELDS: tuple[str, ...] = tuple(c.field for c in COLUMNS if c.kind == "text")
REQUIRED_HEADERS: tuple[str, ...] = tuple(c.sap for c in COLUMNS if c.required)

# Chave natural de um item: evita duplicar linhas ao importar o mesmo período duas vezes.
NATURAL_KEY: tuple[str, ...] = ("empresa", "numero_documento", "item_documento")
