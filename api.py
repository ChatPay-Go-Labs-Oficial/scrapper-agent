"""
API FastAPI para servir o agente de pesquisa de produtos.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager

from agent import agent_os, agent


# Modelos Pydantic para request/response
class ChatRequest(BaseModel):
    """Modelo para requisições de chat."""
    url: str = Field(..., description="URL do site a ser analisado")
    message: str = Field(..., description="Mensagem para enviar ao agente")
    user_id: Optional[str] = Field(None, description="ID do usuário para rastreamento")
    session_id: Optional[str] = Field(None, description="ID da sessão para manter contexto")
    stream: bool = Field(False, description="Se deve retornar resposta em streaming")


class ChatResponse(BaseModel):
    """Modelo para respostas do chat."""
    response: str = Field(..., description="Resposta do agente")
    session_id: Optional[str] = Field(None, description="ID da sessão")
    user_id: Optional[str] = Field(None, description="ID do usuário")
    success: bool = Field(True, description="Indica se a operação foi bem-sucedida")


class HealthResponse(BaseModel):
    """Modelo para resposta de health check."""
    status: str = Field(..., description="Status da API")
    agent_name: str = Field(..., description="Nome do agente")
    agent_role: str = Field(..., description="Função do agente")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""
    # Startup
    print("🚀 Iniciando API do Agente de Pesquisa de Produtos...")
    yield
    # Shutdown
    print("🛑 Encerrando API...")


# Criar aplicação FastAPI
app = FastAPI(
    title="Agente de Pesquisa de Produtos API",
    description="API para interagir com o agente especializado em análise de produtos em websites",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique domínios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.post("/chat", response_model=ChatResponse)
def chat_with_agent(request: ChatRequest):
    """
    Endpoint principal para conversar com o agente.
    
    Envia uma mensagem para o agente e retorna a resposta.
    """
    try:
        # Preparar parâmetros para o agente
        params = {
            "url": request.url,
            "message": request.message,
            "stream": request.stream,
        }
        
        # Adicionar user_id e session_id se fornecidos
        if request.user_id:
            params["user_id"] = request.user_id
        if request.session_id:
            params["session_id"] = request.session_id
        
        # Executar o agente
        response = agent.run(input=[params["url"], params["message"]], stream=params["stream"], user_id=params["user_id"], session_id=params["session_id"])
        
        # Extrair o conteúdo da resposta
        if hasattr(response, 'content'):
            response_content = response.content
        elif hasattr(response, 'response'):
            response_content = response.response
        else:
            response_content = str(response)
        
        return ChatResponse(
            response=response_content,
            session_id=request.session_id,
            user_id=request.user_id,
            success=True
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar mensagem: {str(e)}"
        )


@app.post("/chat/stream")
def chat_with_agent_stream(request: ChatRequest):
    """
    Endpoint para conversar com o agente usando streaming.
    
    Retorna a resposta em tempo real conforme o agente processa.
    """
    try:
        from fastapi.responses import StreamingResponse
        
        def generate_response():
            # Preparar parâmetros para o agente
            params = {
                "url": request.url,
                "message": request.message,
                "stream": True,
            }
            
            # Adicionar user_id e session_id se fornecidos
            if request.user_id:
                params["user_id"] = request.user_id
            if request.session_id:
                params["session_id"] = request.session_id
            
            # Executar o agente com streaming
            # Usar get() para evitar KeyError ou passar None se não existir
            response_stream = agent.run(
                input=[params["url"], params["message"]], 
                stream=True, 
                user_id=params.get("user_id"), 
                session_id=params.get("session_id")
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
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar streaming: {str(e)}"
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
