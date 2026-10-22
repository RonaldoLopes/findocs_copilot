"""Cliente HTTP compartilhado pelas fontes de dados, com retry para erros temporários."""

from __future__ import annotations

import logging
import time
import httpx
from findocs.domain.exceptions import FinDocsError

log = logging.getLogger(__name__)

STATUS_TEMPORARIOS = {429, 500, 502, 503, 504}

class IngestaoError(FinDocsError):
    """Falha ao baixar ou interpretar dados de uma fonte externa."""

class _ErroTemporario(Exception):
    """Uso interno: sinaliza que vale a pena tentar de novo."""

def criar_cliente(
        timeout: float = 60.0, transport: httpx.BaseTransport | None = None
)-> httpx.Client:
    return httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "findocs-copilot/0.1 (projeto de estudo)"},
        transport=transport,
    )

def get_com_retry(
        client: httpx.Client,
        url: str,
        *,
        params: dict | None = None,
        tentativas: int = 3,
        espera: float = 1.0,
) -> httpx.Response:
    """GET com backoff exponencial. Só repete erros temporários (rede, 429, 5xx)."""
    ultimo_erro: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        try:
            resposta = client.get(url, params=params)
            if resposta.status_code in STATUS_TEMPORARIOS:
                raise _ErroTemporario(f"HTTP {resposta.status_code}")
            resposta.raise_for_status()
            return resposta
        except httpx.HTTPStatusError as exc:
            # 4xx (exceto 429): o problema é o pedido, repetir não adianta
            raise IngestaoError(f"HTTP {exc.response.status_code} em {url}") from exc  
        except(httpx.TransportError, _ErroTemporario) as exc:
            ultimo_erro = exc
            log.warning("Tentativa %s/%s falhou em %s: %s", tentativa, tentativas, url, exc)
            if tentativa < tentativas:
                time.sleep(espera * 2 ** (tentativa -1))
    raise IngestaoError(f"Falha ao acessar {url} após {tentativas} tentativas") from ultimo_erro
