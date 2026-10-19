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
            self._dados[c.cnpj] = c
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

    def buscar(self, cnpj: str, dt_ref: date | None = None) -> list[ItemDemonstracao]:
        itens = [i for i in self._dados.values() if i.cnpj == cnpj]
        if dt_ref:
            itens = [i for i in itens if i.dt_ref == dt_ref]
        return sorted(itens, key=lambda i: (i.dt_ref, i.cd_conta))

class InMemoryDocumentoRepository(DocumentoRepository):
    def __init__(self) -> None:
        self._dados: dict[str, FatoRelevante] = {}

    def salvar_documentos(self, documentos: Sequence[FatoRelevante]) -> int:
        for d in documentos:
            existente = self._dados.get(d.id_origem)
            if existente and existente.tem_texto and not d.tem_texto:
                d = replace(d, texto=existente.texto) # preserva o texto já extraido
            self._dados[d.id_origem] = d
        return len(documentos)

    def obter(self, id_origem: str) -> FatoRelevante:
        try:
            return self._dados[id_origem]
        except KeyError:
            raise NaoEncontradoError(f"Documento {id_origem} não encontrado") from None

    def listar(self, *, cnpj: str | None = None, busca: str | None = None, limite: int = 20, offset: int = 0) -> list[FatoRelevante]:
        itens = sorted(self._dados.values(), key=lambda d: d.data, reverse=True)
        if cnpj:
            itens = [d for d in itens if d.cnpj == cnpj]
        if busca:
            termo = busca.lower()
            itens = [d for d in itens if termo in d.assunto.lower() or termo in d.empresa.lower()]
        return itens[offset: offset + limite]

    def sem_texto(self, limite: int = 100) -> list[FatoRelevante]:
        return[d for d in self._dados.values() if not d.tem_texto][:limite]

    def com_texto(self, limite: int = 1000) -> list[FatoRelevante]:
        return [d for d in self._dados.values() if d.tem_texto][:limite]

    def atualizar_texto(self, id_origem: str, texto: str) -> None:
        self._dados[id_origem] = self.obter(id_origem).com_texto(texto)

