from dataclasses import FrozenInstanceError
from datetime import date

import pytest
from findocs.domain.exceptions import ValidacaoError
from findocs.domain.models import Companhia, FatoRelevante, Serie, normalizar_cnpj

pytestmark = pytest.mark.unit

@pytest.mark.parametrize(
    "entrada", ["12.345.678/0001-95", "12345678000195", " 12345678000195 "]
)
def test_normalizar_cnpj_aceita_varios_formatos(entrada):
    assert normalizar_cnpj(entrada) == "12345678000195"

@pytest.mark.parametrize(
    "entrada", ["12.ABC.345/01DE-35", "12abc34501de35", " 12ABC34501DE35 "]
)
def test_normalizar_cnpj_aceita_o_formato_alfanumerico(entrada):
    assert normalizar_cnpj(entrada) == "12ABC34501DE35"

@pytest.mark.parametrize(
    "entrada", ["", "123", "abc", "1234567800019", "12ABC34501DEXX", "12.345.678/0001-9X"]
)
def test_normalizar_cnpj_rejeita_invalidos(entrada):
    with pytest.raises(ValidacaoError):
        normalizar_cnpj(entrada)

def test_companhia_normaliza_cnpj_na_criacao():
    c = Companhia("11.111.111/0001-11", 1, "Alfa S.A.")
    assert c.cnpj == "11111111000111"

def test_entidades_sao_imutaveis():
    s = Serie(432, "Meta Selic", "% a.a.", "D")
    with pytest.raises(FrozenInstanceError):
        s.nome = "outro" # type: ignore[misc]

def test_serie_valida_campos():
    with pytest.raises(ValidacaoError):
        Serie(0, "x", "%", "D")
    with pytest.raises(ValidacaoError):
        Serie(1, " ", "%", "D")
    with pytest.raises(ValidacaoError):
        Serie(1, "x", "%", "Z")

def test_fato_relevante_com_texto_devolve_copia():
    original = FatoRelevante("1", "11111111000111", "Alfa", date(2024, 1, 1), "Assunto")
    novo = original.com_texto("conteúdo")
    assert not original.tem_texto
    assert novo.tem_texto and novo.texto == "conteúdo"
    assert novo is not original
