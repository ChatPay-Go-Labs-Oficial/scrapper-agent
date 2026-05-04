"""
API FastAPI para servir o agente de pesquisa de produtos.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import asyncio
import os
from contextlib import asynccontextmanager
import logging

from agent import agent_os, agent
from knowledge.scraping_cache import get_or_fetch
from guards.security import validate_url, create_safe_prompt, detect_suspicious_patterns
from guards.auth import verify_internal_token

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Modelos Pydantic para request/response
class ChatRequest(BaseModel):
    """Modelo para requisições de chat."""
    url: str = Field(..., description="URL do site a ser analisado")
    message: str = Field(..., description="Mensagem para enviar ao agente")
    user_id: Optional[str] = Field(None, description="ID do usuário para rastreamento")
    session_id: Optional[str] = Field(None, description="ID da sessão para manter contexto")
    stream: bool = Field(False, description="Se deve retornar resposta em streaming")
    prompt_ai: Optional[str] = Field(None, description="Prompt customizado da persona do vendedor")
    product_id: Optional[str] = Field(None, description="ID do produto para cache de scraping")


class InferenceRequest(BaseModel):
    """Modelo para requisições internas de inferência (novo formato)."""
    product_id: str = Field(..., description="UUID do produto")
    seller_id: str = Field(..., description="UUID do vendedor")
    message: str = Field(..., description="Mensagem do comprador")
    session_id: str = Field(..., description="ID da sessão para manter contexto")
    prompt_ai: Optional[str] = Field(None, description="Prompt customizado da persona do vendedor")


class ChatResponse(BaseModel):
    """Modelo para respostas do chat."""
    response: str = Field(..., description="Resposta do agente")
    session_id: Optional[str] = Field(None, description="ID da sessão")
    user_id: Optional[str] = Field(None, description="ID do usuário")
    success: bool = Field(True, description="Indica se a operação foi bem-sucedida")


class InferenceResponse(BaseModel):
    """Modelo para respostas de inferência não-streaming."""
    response: str = Field(..., description="Resposta do agente")
    session_id: Optional[str] = Field(None, description="ID da sessão")
    knowledge_source: Optional[str] = Field(None, description="Fonte de conhecimento usada")
    model_used: Optional[str] = Field(None, description="Modelo de IA utilizado")


class HealthResponse(BaseModel):
    """Modelo para resposta de health check."""
    status: str = Field(..., description="Status da API")
    agent_name: str = Field(..., description="Nome do agente")
    agent_role: str = Field(..., description="Função do agente")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""
    logger.info("🚀 Iniciando API do Agente de Pesquisa de Produtos...")
    yield
    logger.info("🛑 Encerrando API...")


# Criar aplicação FastAPI
app = FastAPI(
    title="Agente de Pesquisa de Produtos API",
    description="API para interagir com o agente especializado em análise de produtos em websites",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
# ALLOWED_ORIGINS deve conter apenas o domínio do Backend NestJS
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
_allowed_origins = [o.strip() for o in _allowed_origins if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/", response_model=Dict[str, str])
def root():
    """Endpoint raiz da API."""
    return {
        "message": "API do Agente de Pesquisa de Produtos",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Endpoint para verificar o status da API e do agente."""
    return HealthResponse(
        status="healthy",
        agent_name=agent.name,
        agent_role=agent.role
    )


@app.get("/inference/health", response_model=HealthResponse)
def inference_health_check():
    """Health check específico para as rotas internas de inferência."""
    return HealthResponse(
        status="healthy",
        agent_name=agent.name,
        agent_role=agent.role
    )


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_internal_token)])
def chat_with_agent(request: ChatRequest):
    """
    Endpoint principal para conversar com o agente.
    
    Envia uma mensagem para o agente e retorna a resposta.
    """
    try:
        # 1. Validar a URL PRIMEIRO
        is_valid, error_msg = validate_url(request.url)
        if not is_valid:
            logger.warning(f"Tentativa de URL inválida: {request.url} - Erro: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"URL inválida: {error_msg}"
            )

        # 2. Detectar padrões suspeitos na mensagem
        is_suspicious, patterns = detect_suspicious_patterns(request.message)
        if is_suspicious:
            logger.warning(f"Padrões suspeitos detectados do usuário {request.user_id}: {patterns}")

        # 3. Chamar a ferramenta de scraping APENAS na URL validada
        logger.info(f"Buscando conteúdo da URL: {request.url}")
        site_content = get_or_fetch(product_id=request.product_id, url=request.url)

        # Verificar se houve erro no scraping
        if site_content.startswith("Erro") or site_content.startswith("O site demorou"):
            return ChatResponse(
                response=site_content,
                session_id=request.session_id,
                user_id=request.user_id,
                success=False
            )

        # 4. Criar prompt seguro com o conteúdo já extraído
        # NÃO passamos a URL bruta para o agente, apenas o conteúdo
        safe_prompt = create_safe_prompt(
            site_content=site_content,
            user_message=request.message,
            url=request.url,
            prompt_ai=request.prompt_ai
        )

        # 5. Executar o agente APENAS com o prompt seguro
        response = agent.run(
            input=safe_prompt,
            stream=request.stream,
            user_id=request.user_id,
            session_id=request.session_id
        )

        # 6. Extrair o conteúdo da resposta
        if hasattr(response, 'content'):
            response_content = response.content
        elif hasattr(response, 'response'):
            response_content = response.response
        else:
            response_content = str(response)

        # Adicionar aviso se houve tentativa de injection
        if is_suspicious:
            response_content = f"⚠️ **Nota**: Foram detectadas e bloqueadas tentativas de manipulação na sua mensagem.\n\n{response_content}"

        return ChatResponse(
            response=response_content,
            session_id=request.session_id,
            user_id=request.user_id,
            success=True
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar mensagem: {str(e)}"
        )


@app.post("/chat/stream", dependencies=[Depends(verify_internal_token)])
def chat_with_agent_stream(request: ChatRequest):
    """
    Endpoint para conversar com o agente usando streaming.
    
    Retorna a resposta em tempo real conforme o agente processa.
    """
    try:
        # 1. Validar a URL PRIMEIRO
        is_valid, error_msg = validate_url(request.url)
        if not is_valid:
            logger.warning(f"Tentativa de URL inválida: {request.url} - Erro: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"URL inválida: {error_msg}"
            )

        # 2. Detectar padrões suspeitos na mensagem
        is_suspicious, patterns = detect_suspicious_patterns(request.message)
        if is_suspicious:
            logger.warning(f"Padrões suspeitos detectados do usuário {request.user_id}: {patterns}")

        # 3. Chamar a ferramenta de scraping APENAS na URL validada
        logger.info(f"Buscando conteúdo da URL: {request.url}")
        site_content = get_or_fetch(product_id=request.product_id, url=request.url)

        # Verificar se houve erro no scraping
        if site_content.startswith("Erro") or site_content.startswith("O site demorou"):
            def error_generator():
                yield f"data: {site_content}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(
                error_generator(),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )

        # 4. Criar prompt seguro com o conteúdo já extraído
        safe_prompt = create_safe_prompt(
            site_content=site_content,
            user_message=request.message,
            url=request.url,
            prompt_ai=request.prompt_ai
        )

        def generate_response():
            # Adicionar aviso de segurança se necessário
            if is_suspicious:
                warning_msg = "⚠️ **Nota**: Foram detectadas e bloqueadas tentativas de manipulação na sua mensagem.\n\n"
                yield f"data: {warning_msg}\n\n"

            # Executar o agente com o prompt seguro
            response_stream = agent.run(
                input=safe_prompt,
                stream=True,
                user_id=request.user_id,
                session_id=request.session_id
            )

            for event in response_stream:
                if hasattr(event, 'event') and event.event == "RunContent":
                    yield f"data: {event.content}\n\n"
                elif hasattr(event, 'content'):
                    yield f"data: {event.content}\n\n"

            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar streaming: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar streaming: {str(e)}"
        )


@app.post("/inference/stream", dependencies=[Depends(verify_internal_token)])
def inference_stream(request: InferenceRequest):
    """
    Endpoint interno para inferência com o novo schema.

    Observação: nesta fase, ainda não há RAG integrado.
    O conteúdo do produto é vazio e o agente responde apenas com o que estiver disponível.
    """
    try:
        # 1. Detectar padrões suspeitos na mensagem
        is_suspicious, patterns = detect_suspicious_patterns(request.message)
        if is_suspicious:
            logger.warning(
                "Padrões suspeitos detectados do seller %s (product_id=%s): %s",
                request.seller_id,
                request.product_id,
                patterns,
            )

        # 2. Conteúdo do produto ainda não disponível (RAG será integrado na F2-KNW-001)
        site_content = ""

        # 3. Criar prompt seguro com o conteúdo disponível
        safe_prompt = create_safe_prompt(
            site_content=site_content,
            user_message=request.message,
            url="N/A",
            prompt_ai=request.prompt_ai,
        )

        def generate_response():
            if is_suspicious:
                warning_msg = (
                    "⚠️ **Nota**: Foram detectadas e bloqueadas tentativas de manipulação na sua mensagem.\n\n"
                )
                yield f"data: {warning_msg}\n\n"

            response_stream = agent.run(
                input=safe_prompt,
                stream=True,
                user_id=request.seller_id,
                session_id=request.session_id,
            )

            for event in response_stream:
                if hasattr(event, 'event') and event.event == "RunContent":
                    yield f"data: {event.content}\n\n"
                elif hasattr(event, 'content'):
                    yield f"data: {event.content}\n\n"

            yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar inferência: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar inferência: {str(e)}"
        )


@app.get("/agent/info")
def get_agent_info():
    """Retorna informações sobre o agente configurado."""
    return {
        "name": agent.name,
        "role": agent.role,
        "tools": [tool.__name__ if hasattr(tool, '__name__') else str(tool) for tool in agent.tools],
        "model": str(agent.model),
        "markdown_enabled": agent.markdown,
        "user_memories_enabled": agent.enable_user_memories,
        "history_enabled": agent.add_history_to_context
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
