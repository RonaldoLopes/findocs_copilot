from datetime import date
import pytest

from findocs.domain.analise import (
    AnalisadorSerie,
    EstrategiaFactory,
    VariacaoPercentual,
    subtrair_meses,
)
from findocs.domain.exceptions import NaoEncontradoError, ValidacaoError
from findocs.domain.models import PontoSerie

pytestmark = pytest.mark.unit

def _pontos():
    return [
        PontoSerie(432, date(2023, 6, 1), 13.75),
        PontoSerie(432, date(2023, 12, 1), 11.75),
        PontoSerie(432, date(2024, 6, 1), 10.50),
    ]

def test_subtrair_meses_ajusta_fim_de_mes():
    assert subtrair_meses(date(2024, 2, 29), 12) == date(2023, 2, 28)
    assert subtrair_meses(date(2024, 3, 31), 1) == date(2024, 2, 29)
    assert subtrair_meses(date(2024, 1, 15), 2) == date(2023, 11, 15)

def test_variacao_absoluta():
    analisador = AnalisadorSerie(EstrategiaFactory.criar("absoluta"))
    r = analisador.variacao(_pontos(), date(2023, 6, 1), date(2024, 6, 1))
    assert r.variacao == pytest.approx(-3.25)
    assert (r.data_inicial, r.data_final) == (date(2023, 6, 1), date(2024, 6, 1))

def test_variacao_percentual():
    analisador = AnalisadorSerie(VariacaoPercentual())
    r = analisador.variacao(_pontos(), date(2023, 6, 1), date(2024, 6, 1))
    assert r.variacao == pytest.approx((10.50 - 13.75) / 13.75 * 100)

def test_periodo_usa_pontos_mais_proximos_dentro_da_janela():
    analisador = AnalisadorSerie(EstrategiaFactory.criar("absoluta"))
    r = analisador.variacao(_pontos(), date(2023, 7, 15), date(2024, 12, 31))
    assert (r.data_inicial, r.data_final) == (date(2023, 12, 1), date(2024, 6, 1))

def test_sem_pontos_suficientes():
    analisador = AnalisadorSerie(EstrategiaFactory.criar("absoluta"))
    with pytest.raises(NaoEncontradoError):
        analisador.variacao(_pontos(), date(2025, 1, 1), date(2025, 12, 31))

def test_percentual_com_valor_inicial_zero():
    with pytest.raises(ValidacaoError):
        VariacaoPercentual().calcular(0, 5)

def test_factory_metodo_desconhecido_lista_opcoes():
    with pytest.raises(ValidacaoError, match="absoluta"):
        EstrategiaFactory.criar("logaritmica")
    assert EstrategiaFactory.nomes() == ["absoluta", "percentual"]
