"""Entidades do domínio. Sem dependência de banco, rede ou framework."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date

from findocs.domain.exceptions import ValidacaoError

# 12 caracteres (dígitos ou letras) + 2 dígitos verificadores, sempre numéricos
_CNPJ = re.compile(r"^[A-Z0-9]{12}[0-9]{2}$")

def normalizar_cnpj(valor: str) -> str:
    """Devolve os 14 caracteres do CNPJ, sem pontuação e em maiúsculas.
    Aceita '12.345.678/0001-95', '12345678000195' e também o CNPJ alfanumérico, emitido
    desde julho de 2026 (por exemplo '12.ABC.345/01DE-35').
    """
    limpo = re.sub(r"[^0-9A-Za-z]", "", valor or "").upper()
    if not _CNPJ.match(limpo):
        raise ValidacaoError(f"CNPJ inválido: {valor!r}")
    return limpo

@dataclass(frozen=True, slots=True)
class Serie:
    """Metadados de uma série temporal (ex.: Meta Selic)."""

    codigo: int
    nome: str
    unidade: str
    periodicidade: str # "D" = diária, "M" = mensal

    def __post_init__(self) -> None:
        if self.codigo <= 0:
            raise ValidacaoError("O código da série deve ser positivo")
        if not self.nome.strip():
            raise ValidacaoError("O nome da sério é obrigatório")
        if self.periodicidade not in {"D", "M"}:
            raise ValidacaoError("Periodicidade deve ser 'D' ou 'M'")

@dataclass(frozen=True, slots=True)
class PontoSerie:
    """Um valor de uma série em uma data (value object)."""

    codigo_serie: int
    data: date
    valor: float

@dataclass(frozen=True, slots=True)
class Companhia:
    """Companhia aberta registrada na CVM."""
    cnpj: str
    cd_cvm: int
    denominacao: str
    setor: str | None = None
    situacao: str | None = None

    def __post_init__(self) -> None:
        # A classe é frozen: para normalizar o campo usamos object.__setattr__
        object.__setattr__(self, "cnpj", normalizar_cnpj(self.cnpj))
        if not self.denominacao.strip():
            raise ValidacaoError("A denominação da companhia é obrigatória")

@dataclass(frozen=True, slots=True)
class FatoRelevante:
    """Fato relevante (ou outro documento) publicado por uma companhia."""

    id_origem: str # identificador no sistema de origem (protocolo da CVM)
    cnpj: str
    empresa: str
    data: date
    assunto: str
    link: str = ""
    texto: str = ""

    def __post_init__(self) -> None:
        if not self.id_origem.strip():
            raise ValidacaoError("id_origem é obrigatório")
        object.__setattr__(self, "cnpj", normalizar_cnpj(self.cnpj))

    @property
    def tem_texto(self) -> bool:
        return bool(self.texto.strip())

    def com_texto(self, texto: str) -> FatoRelevante:
        """Objetos imutáveis não mudam: devolvemos uma cópia com o texto."""
        return replace(self, texto=texto)

@dataclass(frozen=True, slots=True)
class ItemDemonstracao:
    """Uma linha de demonstração financeira (ex.: DRE) de uma companhia."""

    cnpj: str
    dt_ref: date
    cd_conta: str
    ds_conta: str
    valor: float # sempre em reais (a escala da CVM já vem aplicada)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cnpj", normalizar_cnpj(self.cnpj))

