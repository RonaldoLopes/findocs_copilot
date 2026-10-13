"""Interfaces (contratos) de acesso a dados. O domínio depende delas, não dos bancos."""
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date

from findocs.domain.models import(
    Companhia,
    FatoRelevante,
    ItemDemonstracao,
    PontoSerie,
    Serie,
)

class SerieRepository(ABC):

    @abstractmethod
    def salvar_serie(cls, serie: Serie) -> None:
        """Insere ou atualiza (upsert) os metadados da série."""

    @abstractmethod
    def salvar_pontos(self, pontos: Sequence[PontoSerie]) -> int:
        """Upsert por (codigo_serie, data). Devolve quantos pontos foram processados."""

    @abstractmethod
    def listar_series(self) -> list[Serie]: ...

    @abstractmethod
    def obter_serie(self, codigo: int) -> Serie:
        """Levanta NaoEncontradoError se não existir."""   

    @abstractmethod
    def buscar_pontos(
        self, codigo: int, inicio: date | None = None, fim: date | None = None
    ) -> list[PontoSerie]:
        """Pontos ordenados por data crescente."""

    @abstractmethod
    def ultima_data(self, codigo: int) -> date | None:
        """Data do último ponto gravado, ou None se a série ainda não tem pontos.
        Base da carga incremental: só pedimos ao BCB o que ainda não temos."""

class CompanhiaRepository(ABC):
    @abstractmethod
    def salvar_companhias(self, companhias: Sequence[Companhia]) -> int: ...

    @abstractmethod
    def salvar_companhias(self, companhias: Sequence[Companhia]) -> int: ...

    @abstractmethod
    def buscar(self, nome: str | None = None, limite: int = 20) -> list[Companhia]:
        """Busca por trecho da denominação (sem diferenciar maiúsculas)."""

    @abstractmethod
    def obter(self, cnpj: str) -> Companhia:
        """Levanta NaoEncontradoError se não existir."""

class DemonstracaoRepository(ABC):
    @abstractmethod
    def salvar_itens(self, itens: Sequence[ItemDemonstracao]) -> int: ...

    @abstractmethod
    def buscar(self, cnpj: str, dt_ref: date | None = None) -> list[ItemDemonstracao]: ...

class DocumentoRepository(ABC):

    @abstractmethod
    def salvar_documentos(self, documentos: Sequence[FatoRelevante]) -> int:
        """Upsert por id_origem. Re-ingerir metadados NÃO apaga um texto já extraído."""

    @abstractmethod
    def obter(self, id_origem: str) -> FatoRelevante:
        """Levanta NaoEncontradoError se não existir."""

    @abstractmethod
    def listar(
        self,
        *,
        cnpj: str | None = None,
        busca: str | None = None,
        limite: int = 20,
        offset: int = 0,
    ) -> list[FatoRelevante]:
        """Mais recentes primeiro. 'busca' procura no assunto e no nome da empresa."""

    @abstractmethod
    def sem_texto(self, limite: int = 100) -> list[FatoRelevante]:
        """Documentos cujo texto ainda não foi extraído."""

    @abstractmethod
    def com_texto(self, limite: int = 1000) -> list[FatoRelevante]:
        """Documentos com texto (candidatos à indexação do RAG)."""

    @abstractmethod
    def atualizar_texto(self, id_origem: str, texto: str) -> None: ...