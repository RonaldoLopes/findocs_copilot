"""Exceções do domínio. Todas herdam de FinDocsError."""

class FinDocsError(Exception):
    """Base de todos os erros do projeto."""

class ValidacaoError(FinDocsError):
    """Dado inválido (CNPJ malformado, série sem nome, SQL inseguro...)"""

class NaoEncontradoError(FinDocsError):
    """Registro não existe."""