"""Testes de contrato: o comportamento que TODA implementação de repositório deve ter.
As funções não começam com 'test_' de propósito: elas são chamadas por testes concretos
(memória agora; SQL Server e MongoDB nas próximas aulas).
"""

from datetime import date
import pytest

from findocs.domain.exceptions import NaoEncontradoError
from findocs.domain.models import Companhia, FatoRelevante, ItemDemonstracao, PontoSerie, Serie
from findocs.repositories.base import (
    CompanhiaRepository,
    DemonstracaoRepository,
    DocumentoRepository,
    SerieRepository,
)

CNPJ_TESTE = "11111111000111"

def contrato_serie(repo: SerieRepository) -> None:
    serie = Serie(999001, "Série de teste", "%", "D")
    repo.salvar_serie(serie)
    repo.salvar_serie(serie) #idempotente
    assert repo.obter_serie(999001) == serie
    assert serie in repo.listar_series()

    pontos = [PontoSerie(999001, date(2024, 1, dia), float(dia)) for dia in range(1, 6)]
    assert repo.salvar_pontos(pontos) == 5

    #upsert; mesma chave (serie + data) substitui o valor, nao duplica
    repo.salvar_pontos([PontoSerie(999001, date(2024, 1, 5), 50.0)])
    achados = repo.buscar_pontos(999001)
    assert len(achados) == 5
    assert achados[-1].valor == 50.0
    assert [p.data for p in achados] == sorted(p.data for p in achados)

    recorte = repo.buscar_pontos(999001, inicio=date(2024, 1, 2), fim=date(2024, 1, 3))
    assert [p.data for p in recorte] == [date(2024, 1, 2), date(2024, 1, 3)]
    assert repo.ultima_data(999001) == date(2024, 1, 5)

    assert repo.ultima_data(123456789) is None
    with pytest.raises(NaoEncontradoError):
        repo.obter_serie(123456789)

def contrato_companhias(repo: CompanhiaRepository) -> None:
    alfa = Companhia(CNPJ_TESTE, 9991, "Alfa Energia S.A.", "Energia", "ATIVO")
    beta = Companhia("22.222.222/0001-22", 9992, "Beta Bank S.A.")
    assert repo.salvar_companhias([alfa, beta]) == 2
    assert repo.salvar_companhias([alfa, beta]) == 2 # idempotente
    assert repo.obter(CNPJ_TESTE) == alfa
    assert [c.cnpj for c in repo.buscar("alfa energia")] == [CNPJ_TESTE]
    assert len(repo.buscar("s.a.", limite=1)) == 1
    with pytest.raises(NaoEncontradoError):
        repo.obter("00000000000000")

def contrato_demonstracoes(repo: DemonstracaoRepository) -> None:
    itens = [
        ItemDemonstracao(CNPJ_TESTE, date(2024, 12, 31), "3.01", "Receita", 1000.0),
        ItemDemonstracao(CNPJ_TESTE, date(2024, 12, 31), "3.02", "Custos", -400.0),
        ItemDemonstracao(CNPJ_TESTE, date(2023, 12, 31), "3.01", "Receita", 900.0),
    ]
    assert repo.salvar_itens(itens) == 3
    repo.salvar_itens([ItemDemonstracao(CNPJ_TESTE, date(2024, 12, 31), "3.01", "Receita", 1100.0)])
    de_2024 = repo.buscar(CNPJ_TESTE, date(2024, 12, 31))
    assert [i.cd_conta for i in de_2024] == ["3.01", "3.02"]
    assert de_2024[0].valor == 1100.0 # upsert substituiu
    assert len(repo.buscar(CNPJ_TESTE)) == 3

def contrato_documentos(repo: DocumentoRepository) -> None:
    d1 = FatoRelevante("TESTE-1", CNPJ_TESTE, "Alfa Energia", date(2024, 3, 1), "Aquisição de ativos")
    d2 = FatoRelevante(
        "TESTE-2", CNPJ_TESTE, "Alfa Energia", date(2024, 4, 1), "Dividendos extraordinários",
        texto="A companhia aprovou dividendos extraordinários.",
    )
    assert repo.salvar_documentos([d1, d2]) == 2
    assert repo.salvar_documentos([d1, d2]) == 2 # idempotente
    assert repo.obter("TESTE-1").assunto == "Aquisição de ativos"
    ids_sem_texto = [d.id_origem for d in repo.sem_texto(limite=1000)]
    assert "TESTE-1" in ids_sem_texto and "TESTE-2" not in ids_sem_texto
    assert "TESTE-2" in [d.id_origem for d in repo.com_texto(limite=1000)]
    repo.atualizar_texto("TESTE-1", "texto extraído")
    assert repo.obter("TESTE-1").texto == "texto extraído"
    # re-ingerir só os metadados não pode apagar o texto que já extraímos
    repo.salvar_documentos([d1])
    assert repo.obter("TESTE-1").texto == "texto extraído"
    achados = repo.listar(cnpj=CNPJ_TESTE, busca="dividendos")
    assert [d.id_origem for d in achados] == ["TESTE-2"]
    recentes = repo.listar(cnpj=CNPJ_TESTE)
    assert [d.id_origem for d in recentes][:2] == ["TESTE-2", "TESTE-1"] # mais recente primeiro
