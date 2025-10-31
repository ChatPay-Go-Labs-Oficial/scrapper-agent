#!/usr/bin/env python3
"""
Servidor principal para executar a API do Agente de Pesquisa de Produtos.
"""

import uvicorn
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def main():
    """Função principal para iniciar o servidor."""
    
    # Configurações do servidor
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"
    log_level = os.getenv("LOG_LEVEL", "info")
    
    print(f"🚀 Iniciando servidor da API do Agente de Pesquisa de Produtos...")
    print(f"📍 Host: {host}")
    print(f"🔌 Porta: {port}")
    print(f"🔄 Reload: {reload}")
    print(f"📊 Log Level: {log_level}")
    print(f"📚 Documentação: http://{host}:{port}/docs")
    print(f"❤️  Health Check: http://{host}:{port}/health")
    
    # Iniciar servidor
    uvicorn.run(
        "api:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
        access_log=True
    )

if __name__ == "__main__":
    main()
