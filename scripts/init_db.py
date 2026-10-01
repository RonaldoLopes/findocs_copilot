"""Executa os scripts de docker/mssql/*.sql no SQL Server, em ordem.
Uso: python scripts/init_db.py
"""
import re
import pyodbc
from pathlib import Path
from findocs.config import get_settings

PASTA_SQL = Path(__file__).resolve().parents[1] / "docker" / "mssql"

def dividir_lotes(sql: str) -> list[str]:
    """O pyodbc não entende 'GO' (que é do sqlcmd). Dividimos o arquivo nele."""
    lotes = re.split(r"^\s*GO\s*$", sql, flags=re.IGNORECASE | re.MULTILINE)
    return [lote.strip() for lote in lotes if lote.strip()]

def _literal(valor: str) -> str:
    """Escapa aspas simples para uso dentro de literais T-SQL."""
    return valor.replace("'", "''")

def main() -> None:
    cfg = get_settings()
    variaveis = {
        "DB_NAME": cfg.mssql_db,
        "APP_USER": cfg.mssql_app_user,
        "APP_PASSWORD": cfg.mssql_app_password.get_secret_value(),
        "RO_USER": cfg.mssql_ro_user,
        "RO_PASSWORD": cfg.mssql_ro_password.get_secret_value(),
    }
    # autocommit: CREATE DATABASE não pode rodar dentro de uma transação
    conn = pyodbc.connect(cfg.odbc_admin("master"), autocommit=True, timeout=10)
    cursor = conn.cursor()

    for arquivo in sorted(PASTA_SQL.glob("*.sql")):
        sql = arquivo.read_text(encoding="utf-8")
        for chave, valor in variaveis.items():
            sql = sql.replace("{{" + chave + "}}", _literal(valor))
        lotes = dividir_lotes(sql)
        for lote in lotes:
            cursor.execute(lote)
        print(f"OK {arquivo.name} ({len(lotes)} lotes)")


if __name__ == "__main__":
    main()