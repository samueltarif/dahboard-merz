"""Funções compartilhadas pelas rotas: filtros e recortes da base."""
from __future__ import annotations

import pandas as pd
from fastapi import Request

from app.services.dataset import get_dataset
from app.services.filters import Filters


def get_filters(request: Request) -> Filters:
    return Filters.from_query(dict(request.query_params))


def slices(filters: Filters) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(base filtrada, base filtrada sem o filtro de movimento)."""
    base = get_dataset()
    return filters.apply(base), filters.apply(base, ignore=("fluxo",))


def apuracao_slice(filters: Filters) -> pd.DataFrame:
    """Base para débito x crédito: ignora movimento e natureza (precisa ver os dois lados)."""
    return filters.apply(get_dataset(), ignore=("fluxo", "natureza"))
