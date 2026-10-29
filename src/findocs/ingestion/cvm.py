"""Cliente dos Dados Abertos da CVM: cadastro, fatos relevantes (IPE) e DRE (DFP)."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Sequence
from typing import IO
import httpx
import pandas as pd

from findocs.domain.exceptions import ValidacaoError
from findocs.domain.models import Companhia, FatoRelevante, ItemDemonstracao, normalizar_cnpj
from findocs.ingestion.http import IngestaoError, criar_cliente, get_com_retry
from findocs.ingestion.qualidade import exigir_colunas

BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA"
URL_CADASTRO = f"{BASE}/CAD/DADOS/cad_cia_aberta.csv"
URL_IPE = f"{BASE}/DOC/IPE/DADOS/ipe_cia_aberta_{{ano}}.zip"
URL_DFP = f"{BASE}/DOC/DFP/DADOS/dfp_cia_aberta_{{ano}}.zip"
COLUNAS_CADASTRO = ["CNPJ_CIA", "DENOM_SOCIAL", "CD_CVM", "SETOR_ATIV", "SIT"]
COLUNAS_IPE = [
"CNPJ_Companhia", "Nome_Companhia", "Categoria", "Assunto",
"Data_Entrega", "Protocolo_Entrega", "Versao", "Link_Download",
]

COLUNAS_DRE = [
"CNPJ_CIA", "DT_REFER", "ORDEM_EXERC", "ESCALA_MOEDA",
"CD_CONTA", "DS_CONTA", "VL_CONTA",
]

ESCALAS = {"UNIDADE": 1, "MIL": 1_000, "MILHAO": 1_000_000, "MILHÃO": 1_000_000}

def ler_csv(fonte: IO[bytes]) -> pd.DataFrame:
    """CSV da CVM: separador ';', encoding latin-1. Tudo como texto; convertemos depois."""
    return pd.read_csv(fonte, sep=";", encoding="latin-1", dtype=str, keep_default_na=False)

def ler_csv_do_zip(conteudo: bytes, trecho_do_nome: str) ->pd.DataFrame:
    """Abre o ZIP e lê o primeiro CSV cujo nome contém 'trecho_do_nome'."""
    with zipfile.ZipFile(io.BytesIO(conteudo)) as zf:
        candidatos = [
            n for n in zf.namelist()
            if trecho_do_nome.lower in n.lower() and n.lower().endswith(".csv")
        ]
        if not candidatos:
            raise IngestaoError(
                f"Nenhum CSV com '{trecho_do_nome}' no ZIP. Arquivos: {zf.namelist()}"
            )
        with zf.open(candidatos[0]) as arquivo:
            return ler_csv(arquivo)
# --------------------------------------------------------------- limpeza
def _cnpj_ou_none(valor: str) -> str | None:
    try:
        return normalizar_cnpj(valor)        
    except ValidacaoError:
        return None

def limpar_cadastro(bruto: pd.DataFrame) -> pd.DataFrame:
    exigir_colunas(bruto, COLUNAS_CADASTRO, "CVM/cadastro")
    df = bruto[COLUNAS_CADASTRO].copy()
    df.columns = ["cnpj", "denominacao", "cd_cvm", "setor", "situacao"]
    df["cnpj"] = df["cnpj"].map(_cnpj_ou_none)
    df["cd_cvm"] = pd.to_numeric(df["cd_cvm"], errors="coerce")
    df["denominacao"] = df["denominacao"].str.strip()
    df = df.dropna(subset=["cnpj", "cd_cvm"])
    df = df[df["denominacao"] != ""]
    df["cd_cvm"] = df["cd_cvm"].astype(int)
    return df.drop_duplicates(subset="cnpj", keep="first").reset_index(drop=True)

def limpar_ipe(bruto: pd.DataFrame, categoria: str = "Fato Relevante") -> pd.DataFrame:
    exigir_colunas(bruto, COLUNAS_IPE, "CVM/IPE")
    df = bruto[COLUNAS_IPE].copy()
    df = df[df["Categoria"].str.strip().str.casefold().str.startswith(categoria.casefold())]
    df.columns = ["cnpj", "empresa", "categoria", "assunto", "data_entrega", "id_origem", "versao", "link"]
    df["cnpj"] = df["cnpj"].map(_cnpj_ou_none)
    df["data"] = pd.to_datetime(df["data_entrega"], errors="coerce", format="mixed").dt.date
    df["id_origem"] = df["id_origem"].str.strip()
    df["versao_num"] = pd.to_numeric(df["versao"], errors="coerce").fillna(0)
    df = df.dropna(subset=["cnpj", "data"])
    df = df[df["id_origem"] != ""]
    # reapresentações: o mesmo protocolo pode vir em várias versões; ficamos com a maior
    df = df.sort_values("versao_num").drop_duplicates(subset="id_origem", keep="last")
    colunas = ["id_origem", "cnpj", "empresa", "data", "assunto", "link"]
    return df[colunas].sort_values("data", ascending=False).reset_index(drop=True)

def limpar_dre(bruto: pd.DataFrame) -> pd.DataFrame:
    exigir_colunas(bruto, COLUNAS_DRE, "CVM/DFP (DRE)")
    df = bruto[COLUNAS_DRE + (["VERSAO"] if "VERSAO" in bruto.columns else [])].copy()
    # cada linha vem duas vezes (ÚLTIMO e PENÚLTIMO exercício): queremos só o atual.
    # Comparação exata: 'PENÚLTIMO' também contém 'LTIMO', então contains() erraria.
    df = df[df["ORDEM_EXERC"].str.strip().str.upper().isin({"ÚLTIMO", "ULTIMO"})]
    escala = df["ESCALA_MOEDA"].str.strip().str.upper().map(ESCALAS).fillna(1)
    df["valor"] = pd.to_numeric(df["VL_CONTA"], errors="coerce") * escala
    df["cnpj"] = df["CNPJ_CIA"].map(_cnpj_ou_none)
    df["dt_ref"] = pd.to_datetime(df["DT_REFER"], errors="coerce").dt.date
    df["versao_num"] = pd.to_numeric(df["VERSAO"], errors="coerce").fillna(0) if "VERSAO" in df else 0
    df = df.dropna(subset=["cnpj", "dt_ref", "valor"])
    df = df.rename(columns={"CD_CONTA": "cd_conta", "DS_CONTA": "ds_conta"})
    df = df.sort_values("versao_num").drop_duplicates(subset=["cnpj", "dt_ref", "cd_conta"], keep="last")
    return df[["cnpj", "dt_ref", "cd_conta", "ds_conta", "valor"]].reset_index(drop=True)


# ------------------------------------------------- DataFrame -> domínio
def _texto_ou_none(valor) -> str | None:
    if valor is None or pd.isna(valor):
        return None
    texto = str(valor).strip()
    return texto or None

def para_companhias(df: pd.DataFrame) -> list[Companhia]:
    return [
        Companhia(
            r.cnpj, int(r.cd_cvm), r.denominacao, _texto_ou_none(r.setor), _texto_ou_none(r.situacao)
        )
        for r in df.itertuples()
    ]

def para_fatos(df: pd.DataFrame) -> list[FatoRelevante]:
    return [
        FatoRelevante(r.id_origem, r.cnpj, r.empresa, r.data, r.assunto or "", r.link or "")
        for r in df.itertuples()
    ]

def para_itens_dre(df: pd.DataFrame) -> list[ItemDemonstracao]:
    return [
        ItemDemonstracao(r.cnpj, r.dt_ref, r.cd_conta, r.ds_conta, float(r.valor))
        for r in df.itertuples()
    ]

# ---------------------------------------------------------------- cliente
class CMVClient:
    def __init__(self, client: httpx.Client | None = None, espera: float = 1.0) -> None:
        self._client = client or criar_cliente()
        self._espera = espera
    
    def _baixar(self, url: str) -> bytes:
        return get_com_retry(self._client, url, espera=self._espera).content
    
    def baixar_cadastro(self) -> pd.DataFrame:
        return limpar_cadastro(ler_csv(io.BytesIO(self._baixar(URL_CADASTRO))))
    
    def baixar_fatos_relevantes(self, ano: int) -> pd.DataFrame:
        conteudo = self._baixar(URL_IPE.format(ano=ano))
        return limpar_ipe(ler_csv_do_zip(conteudo, "ipe_cia_aberta"))
    
    def baixar_dre(self, ano: int) -> pd.DataFrame:
        conteudo = self._baixar(URL_DFP.format(ano=ano))
        return limpar_dre(ler_csv_do_zip(conteudo, "DRE_con"))

def colunas_esperadas() -> Sequence[str]:
    return COLUNAS_CADASTRO