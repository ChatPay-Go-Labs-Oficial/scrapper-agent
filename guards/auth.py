"""
Guard de autenticação interna do AI Service.

Valida o Bearer token enviado pelo Backend NestJS em todas as rotas protegidas.
O token é compartilhado via variável de ambiente AI_SERVICE_INTERNAL_TOKEN
e nunca é logado em nenhum nível de log.
"""

import os
import logging
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

# auto_error=False para que possamos retornar 401 manualmente quando não há
# Authorization header — o padrão auto_error=True retorna 403 incorretamente.
_security = HTTPBearer(auto_error=False)


def verify_internal_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_security),
) -> None:
    """
    Valida o Bearer token interno enviado pelo Backend NestJS.

    Deve ser injetado como dependência (Depends) em todas as rotas de inferência.
    Rotas públicas (/, /health) NÃO devem usar este guard.

    Raises:
        HTTPException 401: Se o header Authorization estiver ausente.
        HTTPException 401: Se o token fornecido for inválido.
        HTTPException 503: Se AI_SERVICE_INTERNAL_TOKEN não estiver configurado.
    """
    # Sem header Authorization → 401 (não autenticado)
    if not credentials:
        logger.warning("Requisição sem header Authorization rejeitada.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    internal_token = os.getenv("AI_SERVICE_INTERNAL_TOKEN")

    if not internal_token:
        # Erro de configuração — não vazar detalhes na resposta
        logger.error("AI_SERVICE_INTERNAL_TOKEN não configurado no ambiente.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço temporariamente indisponível.",
        )

    if credentials.credentials != internal_token:
        # Não logar o token recebido — apenas que houve tentativa inválida
        logger.warning("Tentativa de acesso com Bearer token inválido rejeitada.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
