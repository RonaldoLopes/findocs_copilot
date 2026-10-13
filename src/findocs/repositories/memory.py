"""Implementações em memória dos repositórios: para testes e para a API sem banco."""

from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from findocs.domain.exceptions import NaoEncontradoError
from findocs.domain.models import(
    Companhia,
    FatoRelevante,
    PontoSerie,
    Serie,
)
from findocs.repositories.base import (
CompanhiaRepository,
DemonstracaoRepository,
DocumentoRepository,
SerieRepository,
)

class InMemorySerieRepository(SerieRepository):
    def __init__(self) -> None:
        self._series: dict[int, Serie] = {}
        self._pontos: dict[tuple[int, date], PontoSerie] = {}

    def salvar_serie(self, serie: Serie) -> None:
        self._series[serie.codigo] = serie

    def salvar_pontos(self, pontos: Sequence[PontoSerie]) -> int:
        for p in pontos:
            self._pontos[(p.codigo_serie, p.data)] = p
        return len(pontos)

    def listar_series(self) -> list[Serie]:
        return sorted(self._series.values(), key=lambda s: s.codigo)

    def obter_serie(self, codigo: int) -> Serie:
        try:
            return self._series[codigo]
        except KeyError:
            raise NaoEncontradoError(f"Série {codigo} não encontrada") from None

    def buscar_pontos(self, codigo: int, inicio: date | None = None, fim: date | None = None) -> list[PontoSerie]:
        pontos = [p for (cod, _), p in self._pontos.items() if cod == codigo]
        if inicio:
            pontos = [p for p in pontos if p.data >= inicio]
        if fim:
            pontos = [p for p in pontos if p.data <= fim]
        return sorted(pontos, key=lambda p: p.data)

    def ultima_data(self, codigo: int) -> date | None:
        datas = [d for (cod, d) in self._pontos if cod == codigo]
        return max(datas) if datas else None

class InMemoryCompanhiaRepository(CompanhiaRepository):
    def __init__(self) -> None:
        self._dados: dict[str, Companhia] = {}

    def salvar_companhias(self, companhias: Sequence[Companhia]) -> int:
        for c in companhias:
            self._dado[c.cnpj] = c
        return len(companhias)

    def buscar(self, nome: str | None = None, limite: int = 20) -> list[Companhia]:
        itens = sorted(self._dados.values(), key=lambda c: c.denominacao)

        if nome:
            itens = [c for c in itens if nome.lower() in c.denominacao.lower()]
        return itens[:limite]

    def obter(self, cnpj: str) -> Companhia:
        try:
            return self._dados[cnpj]
        except KeyError:
            raise NaoEncontradoError(f"Companhia {cnpj} não encontrada") from None

class InMemoryDemonstracaoRepository(DemonstracaoRepository):
    def __init__(self) -> None:
        self._dados: dict[tuple[str, date, str], ItemDemonstracao] = {}

    def salvar_itens(self, itens: Sequence[ItemDemonstracao]) -> int:
        for i in itens:
            self._dados[(i.cnpj, i.dt_ref, i.cd_conta)] = i
        return len(itens)    
    # Parei 30

