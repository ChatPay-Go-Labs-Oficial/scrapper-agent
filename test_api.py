#!/usr/bin/env python3
"""
Exemplo de uso da API do Agente de Pesquisa de Produtos.
"""

import requests
import json
import time

# Configurações da API
API_BASE_URL = "http://localhost:8000"

def test_health():
    """Testa o endpoint de health check."""
    print("🔍 Testando health check...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API está funcionando!")
            print(f"   Status: {data['status']}")
            print(f"   Agente: {data['agent_name']}")
            print(f"   Função: {data['agent_role']}")
        else:
            print(f"❌ Erro no health check: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao conectar com a API: {e}")

def test_agent_info():
    """Testa o endpoint de informações do agente."""
    print("\n🔍 Testando informações do agente...")
    try:
        response = requests.get(f"{API_BASE_URL}/agent/info")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Informações do agente:")
            print(f"   Nome: {data['name']}")
            print(f"   Função: {data['role']}")
            print(f"   Ferramentas: {data['tools']}")
            print(f"   Modelo: {data['model']}")
        else:
            print(f"❌ Erro ao obter informações: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro ao conectar com a API: {e}")

def test_chat():
    """Testa o endpoint de chat."""
    print("\n🔍 Testando chat com o agente...")
    
    # Exemplo de mensagem
    message = "Analise este produto: https://www.amazon.com.br/dp/B08N5WRWNW"
    
    payload = {
        "message": message,
        "user_id": "test_user_123",
        "session_id": "test_session_456"
    }
    
    try:
        print(f"📤 Enviando mensagem: {message[:50]}...")
        response = requests.post(
            f"{API_BASE_URL}/chat",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Resposta recebida!")
            print(f"   Sucesso: {data['success']}")
            print(f"   Usuário: {data['user_id']}")
            print(f"   Sessão: {data['session_id']}")
            print(f"   Resposta: {data['response'][:200]}...")
        else:
            print(f"❌ Erro no chat: {response.status_code}")
            print(f"   Detalhes: {response.text}")
    except Exception as e:
        print(f"❌ Erro ao conectar com a API: {e}")

def test_chat_stream():
    """Testa o endpoint de chat com streaming."""
    print("\n🔍 Testando chat com streaming...")
    
    # Exemplo de mensagem
    message = "Analise este produto: https://www.amazon.com.br/dp/B08N5WRWNW"
    
    payload = {
        "message": message,
        "user_id": "test_user_123",
        "session_id": "test_session_456",
        "stream": True
    }
    
    try:
        print(f"📤 Enviando mensagem com streaming: {message[:50]}...")
        response = requests.post(
            f"{API_BASE_URL}/chat/stream",
            json=payload,
            headers={"Content-Type": "application/json"},
            stream=True
        )
        
        if response.status_code == 200:
            print("✅ Streaming iniciado!")
            print("📥 Recebendo resposta em tempo real:")
            print("-" * 50)
            
            for line in response.iter_lines():
                if line:
                    line_str = line.decode('utf-8')
                    if line_str.startswith('data: '):
                        content = line_str[6:]  # Remove 'data: '
                        if content == '[DONE]':
                            print("\n" + "-" * 50)
                            print("✅ Streaming concluído!")
                            break
                        else:
                            print(content, end='', flush=True)
        else:
            print(f"❌ Erro no streaming: {response.status_code}")
            print(f"   Detalhes: {response.text}")
    except Exception as e:
        print(f"❌ Erro ao conectar com a API: {e}")

def main():
    """Função principal para executar todos os testes."""
    print("🚀 Iniciando testes da API do Agente de Pesquisa de Produtos")
    print("=" * 60)
    
    # Executar testes
    test_health()
    test_agent_info()
    test_chat()
    test_chat_stream()
    
    print("\n" + "=" * 60)
    print("✅ Testes concluídos!")
    print("\n📚 Para mais informações, acesse:")
    print(f"   - Documentação: {API_BASE_URL}/docs")
    print(f"   - ReDoc: {API_BASE_URL}/redoc")

if __name__ == "__main__":
    main()
