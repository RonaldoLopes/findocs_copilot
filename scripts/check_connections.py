"""Confirma que o Python consegue falar com o SQL Server e o MongoDB."""
import sys

import pyodbc
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from findocs.config import get_settings

def checar_sqlserver() -> bool:
    cfg = get_settings()
    try:
        conn = pyodbc.connect(cfg.odbc_app(), timeout=5)
        versao = conn.cursor().execute("SELECT @@VERSION").fetchone()[0]
        conn.close()
        print(f"SQL Server OK: {versao.splitlines()[0]}")
        return True
    except pyodbc.Error as exc:
        print(f"SQL Server FALHOU: {exc}")
        return False

def checar_mongo() -> bool:
    cfg = get_settings()
    try:
        client = MongoClient(cfg.mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")
        versao = client.server_info()["version"]
        client.close()
        print(f"MongoDB OK: versão {versao}")
        return True
    except PyMongoError as exc:
        print(f"MongoDB FALHOU: {exc}")
        return False

if __name__ == "__main__":
    resultados = [checar_sqlserver(), checar_mongo()]
    sys.exit(0 if all(resultados) else 1)