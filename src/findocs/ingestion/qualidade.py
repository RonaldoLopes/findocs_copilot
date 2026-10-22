"""Verificações simples de qualidade para DataFrames."""

from __future__ import annotations
from collections.abc import Sequence
import pandas as pd
from findocs.domain.exceptions import ValidacaoError

def exigir_colunas(df: pd.DataFrame, colunas: Sequence[str], origem: str) -> None:
    """Falha cedo, e com mensagem útil, se a fonte mudou o layout."""
    faltando = [c for c in colunas if c not in df.columns]
    if faltando:
        raise ValidacaoError(
            f"{origem}: colunas ausentes {faltando}. Colunas recebidas: {list(df.columns)}"
        )

def relatorio_qualidade(df: pd.DataFrame) -> dict:
    """Resumo rápido para logar depois de uma carga."""
    nulos = df.isna().sum()
    return{
        "linhas": int(len(df)),
        "colunas": list(df.columns),
        "nulos": {c: int(n) for c, n in nulos.items() if n > 0},
    }

