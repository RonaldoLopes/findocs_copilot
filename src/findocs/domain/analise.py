"""Análise de séries: Strategy para o cálculo e Factory para escolher a estratégia."""

from __future__ import annotations
import calendar
from abc import ABC, abstractmethod
from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import ClassVar

from findocs.domain.exceptions import NaoEncontradoError, ValidacaoError
from findocs.domain.models import PontoSerie

def subtrair_meses(data: date, meses: int) -> date:
    """12 meses antes de 29/02/2024 é 28/02/2023: o dia é ajustado ao mês de destino."""
    total = data.year * 12 + (data.month - 1) - meses
    ano, mes_zero = divmod(total, 12)
    mes = mes_zero + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(data.day, ultimo_dia))

class EstrategiaVariacao(ABC):
    """Contrato: recebe valor inicial e final, devolve a variação."""

    nome: ClassVar[str]

    @abstractmethod
    def calcular(self, inicial: float, final: float) -> float: ...

class EstrategiaFactory:
    """Registro de estratégias. Criar por nome evita if/elif espalhado pelo código."""

    _registro: ClassVar[dict[str, type[EstrategiaVariacao]]] = {}

    @classmethod
    def registrar(cls, estrategia: type[EstrategiaVariacao]) -> type[EstrategiaVariacao]:
        cls._registro[estrategia.nome] = estrategia
        return estrategia

    @classmethod
    def criar(cls, nome: str) -> EstrategiaVariacao:
        try:
            return cls._registro[nome.lower()]()
        except KeyError:
            opcoes = ", ".join(sorted(cls._registro))
            raise ValidacaoError(f"Método desconhecido: {nome!r}. Opções: {opcoes}") from None

@EstrategiaFactory.registrar
class VariacaoAbsoluta(EstrategiaVariacao):
    nome = "absoluta"

    def calcular(self, inicial: float, final: float) -> float:
        return final - inicial

@EstrategiaFactory.registrar
class VariacaoPercentual(EstrategiaVariacao):
    nome = "percentual"

    def calcular(self, inicial: float, final: float) -> float:
        if inicial == 0:
            raise ValidacaoError("Variação percentual indefinida: valor inicial é zero")
        return (final - inicial) / abs(inicial) * 100

@dataclass(frozen=True, slots=True)
class ResultadoVariacao:
    metodo: str
    data_inicial: date
    data_final: date
    valor_inicial: float
    valor_final: float
    variacao: float

class AnalisadorSerie:
    """Composição: o analisador *recebe* uma estratégia, em vez de herdar de uma."""

    def __init__(self, estrategia: EstrategiaVariacao) -> None:
        self._estrategia = estrategia

    def variacao(self, pontos: Sequence[PontoSerie], inicio: date, fim: date) -> ResultadoVariacao:
        ordenados = sorted(pontos, key=lambda p: p.data)
        datas = [p.data for p in ordenados]
        i = bisect_left(datas, inicio) # primeiro ponto em ou depois de 'inicio'
        j = bisect_right(datas, fim) - 1 # último ponto em ou antes de 'fim'
        if i >= len(ordenados) or j < 0 or i >= j:
            raise NaoEncontradoError("Pontos insuficientes no período informado")
        primeiro, ultimo = ordenados[i], ordenados[j]

        return ResultadoVariacao(
            metodo=self._estrategia.nome,
            data_inicial=primeiro.data,
            data_final=ultimo.data,
            valor_inicial=primeiro.valor,
            valor_final=ultimo.valor,
            variacao=self._estrategia.calcular(primeiro.valor, ultimo.valor),
        )
