"""Regras de classificação por CFOP.

- Movimento: 1/2/3 = Entrada, 5/6/7 = Saída.
- Operação: 1/5 = Interna, 2/6 = Interestadual, 3/7 = Exterior.
- Natureza: agrupamento gerencial (Venda, Compra, Remessa...).

As regras ficam em tabelas (dicts) para serem fáceis de revisar e ajustar.
A classificação é aplicada ao carregar os dados, então mudar uma regra aqui
vale para todo o histórico sem precisar reimportar.
"""
from __future__ import annotations

from dataclasses import dataclass

MOVIMENTO = {"1": "Entrada", "2": "Entrada", "3": "Entrada", "5": "Saída", "6": "Saída", "7": "Saída"}
OPERACAO = {"1": "Interna", "2": "Interestadual", "3": "Exterior", "5": "Interna", "6": "Interestadual", "7": "Exterior"}

# Natureza pelos 3 últimos dígitos do CFOP (o 1º dígito já dá movimento/operação).
# Ex.: 5102, 6102 -> "102" = Venda.  1556, 2556 -> "556" = Uso e consumo.
NATUREZA_POR_SUFIXO: dict[str, str] = {
    # Saídas
    "101": "Venda", "102": "Venda", "103": "Venda", "104": "Venda", "105": "Venda", "106": "Venda",
    "107": "Venda", "108": "Venda", "109": "Venda", "110": "Venda", "116": "Venda", "117": "Venda",
    "118": "Venda", "119": "Venda", "120": "Venda", "122": "Venda", "123": "Venda",
    "401": "Venda", "403": "Venda", "405": "Venda",
    "151": "Transferência", "152": "Transferência", "153": "Transferência", "155": "Transferência",
    "156": "Transferência", "409": "Transferência",
    "201": "Devolução", "202": "Devolução", "208": "Devolução", "209": "Devolução", "210": "Devolução",
    "410": "Devolução", "411": "Devolução", "412": "Devolução", "413": "Devolução",
    "910": "Bonificação/brinde", "911": "Amostra grátis",
    "912": "Demonstração", "913": "Demonstração",
    "915": "Conserto/reparo", "916": "Conserto/reparo",
    "908": "Comodato", "909": "Comodato",
    "949": "Outras", "920": "Outras", "921": "Outras", "901": "Industrialização", "902": "Industrialização",
    # Entradas específicas
    "353": "Frete (CT-e)", "352": "Frete (CT-e)", "351": "Frete (CT-e)", "354": "Frete (CT-e)",
    "556": "Uso e consumo", "407": "Uso e consumo",
    "551": "Ativo imobilizado", "406": "Ativo imobilizado",
    "933": "Serviço",
}

# Para entradas, alguns sufixos de "venda" significam compra.
NATUREZA_ENTRADA_OVERRIDE: dict[str, str] = {
    "101": "Compra", "102": "Compra", "403": "Compra", "401": "Compra",
    "201": "Devolução de venda", "202": "Devolução de venda", "410": "Devolução de venda", "411": "Devolução de venda",
    "908": "Comodato", "909": "Comodato", "912": "Demonstração", "913": "Demonstração",
    "915": "Conserto/reparo", "916": "Conserto/reparo", "910": "Bonificação/brinde",
}

# Naturezas cujo imposto destacado na entrada NÃO gera crédito de ICMS/IPI.
# (Regra simplificada: uso e consumo não dá crédito de ICMS até 2033 - LC 87/96 art. 33.)
SEM_CREDITO_ICMS_IPI: frozenset[str] = frozenset({"Uso e consumo"})


@dataclass(frozen=True)
class CfopInfo:
    cfop: str
    movimento: str
    operacao: str
    natureza: str


def normalize_cfop(raw: object) -> str:
    """'5102/AA' -> '5102'.  Valores inválidos -> ''."""
    if raw is None:
        return ""
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    return digits[:4] if len(digits) >= 4 else ""


def classify(raw_cfop: object, direcao: object = None) -> CfopInfo:
    cfop = normalize_cfop(raw_cfop)
    if not cfop:
        mov = {"1": "Entrada", "2": "Saída"}.get(str(direcao or ""), "Indefinido")
        return CfopInfo("", mov, "Indefinida", "Sem CFOP")

    first, suffix = cfop[0], cfop[1:]
    movimento = MOVIMENTO.get(first)
    if movimento is None:  # CFOP fora do padrão: usa a direção do SAP
        movimento = {"1": "Entrada", "2": "Saída"}.get(str(direcao or ""), "Indefinido")
    operacao = OPERACAO.get(first, "Indefinida")

    natureza = None
    if movimento == "Entrada":
        natureza = NATUREZA_ENTRADA_OVERRIDE.get(suffix)
        if natureza is None and suffix.startswith("9"):
            natureza = "Retorno/outras" if suffix not in NATUREZA_POR_SUFIXO else NATUREZA_POR_SUFIXO[suffix]
    if natureza is None:
        natureza = NATUREZA_POR_SUFIXO.get(suffix)
    if natureza is None:
        natureza = "Compra" if (movimento == "Entrada" and suffix.startswith("1")) else "Outras"
    return CfopInfo(cfop, movimento, operacao, natureza)
