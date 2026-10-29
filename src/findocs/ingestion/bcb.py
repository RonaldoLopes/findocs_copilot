"""Cliente da API SGS do Banco Central: séries temporais."""
from __future__ import annotations
from collections.abc import Iterator, Sequence
from datetime import date, timedelta
import httpx
import pandas as pd
from findocs.domain.exceptions import ValidacaoError
from findocs.domain.models import PontoSerie, Serie
from findocs.ingestion.http import IngestaoError, criar_cliente, get_com_retry
from findocs.ingestion.qualidade import exigir_colunas

URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
JANELA_DIAS = 3600 # a API rejeita períodos maiores que 10 anos (3650 dias)

SERIES_PADRAO: tuple[Serie, ...] = (
    Serie(432, "Meta Selic", "% a.a.", "D"),
    Serie(433, "IPCA", "% a.m.", "M"),
    Serie(1, "Dólar comercial (venda)", "R$", "D"),
    Serie(12, "CDI", "% a.d.", "D"),
)

def janelas(inicio: date, fim: date, dias: int = JANELA_DIAS) -> Iterator[tuple[date, date]]:
    """Divide [inicio, fim] em janelas consecutivas de no máximo 'dias' dias."""
    atual = inicio
    while atual <= fim:
        termino = min(atual + timedelta(days=dias), fim)
        yield atual, termino
        atual = termino + timedelta(days=1)

def limpar_serie(bruto: pd.DataFrame) -> pd.DataFrame:
    """Recebe o JSON cru (texto) e devolve colunas tipadas: data (date) e valor (float)."""
    exigir_colunas(bruto, ["data", "valor"], "BCB/SGS")
    df = bruto[["data", "valor"]].copy()
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"].astype(str).str.replace(",", "."), errors="coerce")
    df = df.dropna(subset=["data", "valor"])
    df["data"] = df["data"].dt.date
    df = df.drop_duplicates(subset="data", keep="last").sort_values("data")
    return df.reset_index(drop=True)

def para_pontos(codigo: int, df: pd.DataFrame) -> list[PontoSerie]:
    return [PontoSerie(codigo, linha.data, float(linha.valor)) for linha in df.itertuples()]

class BCBClient:
    
    def __init__(self, client: httpx.Client | None = None, espera: float = 1.0) -> None:
        self._client = client or criar_cliente()
        self._espera = espera

    def baixar_serie(self, codigo: int, inicio: date, fim: date) -> pd.DataFrame:
        if inicio > fim:
            raise ValidacaoError("A data inicial deve ser anterior à final")
        registros: list[dict] = []
        for ini, ter in janelas(inicio, fim):
            resposta = get_com_retry(
                self._client,
                URL_SGS.format(codigo=codigo),
                params={
                    "formato": "json",
                    "dataInicial": ini.strftime("%d/%m/%Y"),
                    "dataFinal": ter.strftime("%d/%m/%Y"),
                },
                espera=self._espera,
            )
            corpo = resposta.json()
            if not isinstance(corpo, list):
                raise IngestaoError(f"Resposta inesperada do SGS para a série {codigo}: {corpo!r}")
            registros.extend(corpo)
        bruto = pd.DataFrame(registros, columns=["data", "valor"]) if not registros else pd.DataFrame(registros)
        return limpar_serie(bruto)

    def baixar_pontos(self, codigo: int, inicio: date, fim: date) -> list[PontoSerie]:
        return para_pontos(codigo, self.baixar_serie(codigo, inicio, fim))

def series_padrao() -> Sequence[Serie]:
    return SERIES_PADRAO
