"""Regras da apuração com ajustes manuais (sem banco, sem HTTP).

Aqui ficam: tipos de lançamento manual, linhas do quadro de apuração,
papéis (lançador, validador, leitor) e o fluxo de status do mês.
Para mudar uma regra de permissão ou incluir um tipo de ajuste, mexa só aqui.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.domain.taxes import APURAVEIS, BY_KEY

# ---------------------------------------------------------------------------
# Lançamentos manuais
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TipoAjuste:
    key: str
    label: str
    lado: str          # "debito" soma aos débitos; "credito" soma aos créditos
    hint: str


TIPOS: tuple[TipoAjuste, ...] = (
    TipoAjuste("ajuste_debito", "Outros débitos (ajuste de débito)", "debito",
               "Débito que não veio das notas do SAP (ex.: diferença de alíquota apurada à parte, débito de ajuste)."),
    TipoAjuste("estorno_credito", "Estorno de crédito", "debito",
               "Crédito tomado que precisa ser anulado (ex.: mercadoria que saiu isenta, perda, uso e consumo)."),
    TipoAjuste("ajuste_credito", "Outros créditos (ajuste de crédito)", "credito",
               "Crédito que não veio das notas do SAP (ex.: crédito de ativo/CIAP, crédito extemporâneo)."),
    TipoAjuste("estorno_debito", "Estorno de débito", "credito",
               "Débito destacado indevidamente que é anulado na apuração."),
)
TIPO_BY_KEY = {t.key: t for t in TIPOS}

TRIBUTOS: tuple[str, ...] = APURAVEIS      # icms, ipi, pis, cofins
TRIBUTO_LABEL = {k: BY_KEY[k].label for k in TRIBUTOS}

UFS: tuple[str, ...] = (
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE",
    "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
)

TOLERANCIA = 0.05   # diferença até 5 centavos conta como "confere" (arredondamento)

_COMPETENCIA = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def competencia_valida(value: str) -> bool:
    return bool(_COMPETENCIA.match(value or ""))


def competencia_anterior(comp: str) -> str:
    y, m = int(comp[:4]), int(comp[5:7])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


# ---------------------------------------------------------------------------
# Quadro de apuração (mesma ordem do livro de apuração / GIA)
# ---------------------------------------------------------------------------
LINHAS: tuple[tuple[str, str, str], ...] = (
    # (chave, rótulo, estilo)  estilo: "" normal, "sub" subtotal, "total" total, "edit" campo editável
    ("debito_saidas", "Débitos pelas saídas (SAP)", ""),
    ("ajuste_debito", "Outros débitos (ajustes)", ""),
    ("estorno_credito", "Estorno de créditos", ""),
    ("total_debitos", "Total de débitos", "sub"),
    ("credito_entradas", "Créditos pelas entradas (SAP)", ""),
    ("ajuste_credito", "Outros créditos (ajustes)", ""),
    ("estorno_debito", "Estorno de débitos", ""),
    ("subtotal_creditos", "Subtotal de créditos", "sub"),
    ("saldo_credor_anterior", "Saldo credor do período anterior", "edit"),
    ("total_creditos", "Total de créditos", "sub"),
    ("saldo_devedor", "Saldo devedor (a recolher)", "total"),
    ("saldo_credor", "Saldo credor a transportar", "total"),
)


# ---------------------------------------------------------------------------
# Papéis e fluxo de status
# ---------------------------------------------------------------------------
PAPEIS = {
    "lancador": "Lançador",
    "validador": "Validador",
    "leitor": "Leitor",
}

STATUS = {
    "rascunho": "Em preparação",
    "em_validacao": "Aguardando validação",
    "devolvido": "Devolvido para correção",
    "validado": "Validado",
}

# Status em que lançamentos e saldos podem ser alterados.
EDITAVEL = ("rascunho", "devolvido")

# acao -> (papéis que podem, status de origem aceitos, status de destino)
TRANSICOES: dict[str, tuple[tuple[str, ...], tuple[str, ...], str]] = {
    "enviar": (("lancador", "validador"), ("rascunho", "devolvido"), "em_validacao"),
    "validar": (("validador",), ("em_validacao",), "validado"),
    "devolver": (("validador",), ("em_validacao", "validado"), "devolvido"),
}
ACAO_LABEL = {"enviar": "Enviar para validação", "validar": "Validar mês", "devolver": "Devolver para correção"}


def pode_editar(papel: str, status: str) -> bool:
    return papel in ("lancador", "validador") and status in EDITAVEL


def acoes_permitidas(papel: str, status: str) -> list[str]:
    return [a for a, (papeis, origem, _) in TRANSICOES.items() if papel in papeis and status in origem]
