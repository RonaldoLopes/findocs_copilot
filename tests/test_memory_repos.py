import pytest

from findocs.repositories.memory import (
    InMemoryCompanhiaRepository,
    InMemoryDemonstracaoRepository,
    InMemoryDocumentoRepository,
    InMemorySerieRepository,
)
from tests import (
    contrato_companhias,
    contrato_demonstracoes,
    contrato_documentos,
    contrato_serie,
)

pytestmark = pytest.mark.unit

def test_serie_cumpre_contrato():
    contrato_serie(InMemorySerieRepository())

def test_companhia_cumpre_contrato():
    contrato_companhias(InMemoryCompanhiaRepository())

def test_demonstracao_cumpre_contrato():
    contrato_demonstracoes(InMemoryDemonstracaoRepository())

def test_documento_cumpre_contrato():
    contrato_documentos(InMemoryDocumentoRepository())
