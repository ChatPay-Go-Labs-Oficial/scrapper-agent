#!/usr/bin/env python3
"""
Script para iniciar o chat com Streamlit.
"""

import subprocess
import sys
import os
import time
import requests
from pathlib import Path

def check_api_running():
    """Verifica se a API está rodando."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False

def start_api():
    """Inicia a API em background."""
    print("🚀 Iniciando API do agente...")
    api_process = subprocess.Popen([
        sys.executable, "main.py"
    ], cwd=Path(__file__).parent)
    return api_process

def wait_for_api():
    """Aguarda a API ficar disponível."""
    print("⏳ Aguardando API ficar disponível...")
    for i in range(30):  # Aguarda até 30 segundos
        if check_api_running():
            print("✅ API está rodando!")
            return True
        time.sleep(1)
        print(f"   Tentativa {i+1}/30...")
    
    print("❌ Timeout: API não ficou disponível em 30 segundos")
    return False

def start_streamlit():
    """Inicia o Streamlit."""
    print("🌐 Iniciando interface de chat...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "chat_app.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0"
    ], cwd=Path(__file__).parent)

def main():
    """Função principal."""
    print("🤖 Agente de Pesquisa de Produtos - Chat Interface")
    print("=" * 60)
    
    # Verificar se a API já está rodando
    if check_api_running():
        print("✅ API já está rodando!")
    else:
        # Iniciar API
        api_process = start_api()
        
        # Aguardar API ficar disponível
        if not wait_for_api():
            print("❌ Falha ao iniciar a API. Encerrando...")
            api_process.terminate()
            return
        
        print("📝 Para parar a API, pressione Ctrl+C")
    
    # Iniciar Streamlit
    try:
        start_streamlit()
    except KeyboardInterrupt:
        print("\n🛑 Encerrando aplicação...")
        if 'api_process' in locals():
            api_process.terminate()

if __name__ == "__main__":
    main()
