"""Configuração da aplicação, lida do ambiente e do arquivo .env."""
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    #LLM
    llm_provider: str = "gemini"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-2.5-flash"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    #sql server
    mssql_host: str = "localhost"
    mssql_port: int = 1433
    mssql_db: str = "findocs"
    mssql_driver: str = "ODBC Driver 18 for SQL Server"
    mssql_sa_password: SecretStr = SecretStr("")
    mssql_app_user: str = "findocs_app"
    mssql_app_password: SecretStr = SecretStr("")
    mssql_ro_user: str = "findocs_ro"
    mssql_ro_password: SecretStr = SecretStr("")

    # MongoDB
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "findocs"

    # Embeddings
    embedding_model: str = "intfloat/multilingual-e5-small"

    def _odbc(self, usuario: str, senha: SecretStr, database: str) -> str:
        # Chaves protegem senhas com caracteres especiais; "}" vira "}}
        pwd = "{" + senha.get_secret_value().replace("}", "}}") + "}"
        return (
            f"DRIVER={{{self.mssql_driver}}};"
            f"SERVER={self.mssql_host},{self.mssql_port};"
            f"DATABASE={database};UID={usuario};PWD={pwd};"
            "Encrypt=yes;TrustServerCertificate=yes"
        )

    def odbc_admin(self, database: str = "master") -> str:
        """Conexão do administrador (sa). Só para criar banco e schema."""
        return self._odbc("sa", self.mssql_sa_password, database)

    def odbc_app(self) -> str:
        """Conexão da aplicação: lê e grava nas tabelas."""
        return self._odbc(self.mssql_app_user, self.mssql_app_password, self.mssql_db)

    def odbc_readonly(self) -> str:
        """Conexão somente leitura, usada pelo text-to-SQL."""
        return self._odbc(self.mssql_ro_user, self.mssql_ro_password, self.mssql_db)

@lru_cache
def get_settings() -> Settings:
    return Settings()