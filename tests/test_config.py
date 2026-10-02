import pytest

from findocs.config import Settings

pytestmark = pytest.mark.unit

def _settings(**extra) -> Settings:
    # _env_file=None: o teste não deve depender do .env da sua máquina
    return Settings(_env_file=None, **extra)

def test_valores_padrao():
    s = _settings()
    assert s.llm_provider == "gemini"
    assert s.mssql_port == 1433
    assert s.mongo_db == "findocs"

def test_senha_nao_aparece_no_repr():
    s = _settings(mssql_sa_password="segredo-123")
    assert "segredo-123" not in repr(s)
    assert s.mssql_sa_password.get_secret_value() == "segredo-123"

def test_string_odbc_protege_chaves_na_senha():
    s = _settings(mssql_sa_password="ab}cd")
    assert "PWD={ab}}cd}" in s.odbc_admin()

def test_odbc_da_aplicacao_usa_banco_e_usuario_da_app():
    s = _settings(mssql_app_user="meu_app", mssql_db="meubanco")
    conexao = s.odbc_app()
    assert "UID=meu_app" in conexao
    assert "DATABASE=meubanco" in conexao