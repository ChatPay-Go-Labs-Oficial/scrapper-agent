"""
Interface de chat com Streamlit para interagir com o Agente de Pesquisa de Produtos.
"""

import streamlit as st
import requests
import json
import time
import re
from typing import Dict, Any, Optional
import uuid
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurações da API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
CHAT_ENDPOINT = f"{API_BASE_URL}/chat"
STREAM_ENDPOINT = f"{API_BASE_URL}/chat/stream"
HEALTH_ENDPOINT = f"{API_BASE_URL}/health"

def clean_agent_response(response_text: str) -> str:
    """
    Limpa a resposta do agente removendo informações sobre ferramentas e tempo de execução.
    
    Args:
        response_text: Resposta bruta do agente
        
    Returns:
        str: Resposta limpa apenas com o conteúdo relevante
    """
    if not response_text:
        return ""
    
    print(f"DEBUG - Input para limpeza: {repr(response_text)}")
    
    # Aplicar apenas limpezas essenciais, preservando markdown
    cleaned = response_text
    
    # Remove informações sobre ferramentas e tempo de execução
    # Padrões como: "Nonebuscar_conteudo_completo_site(url=...) completed in 0.5908s."
    cleaned = re.sub(r'^None.*?completed in \d+\.\d+s\.\s*', '', cleaned)
    cleaned = re.sub(r'^.*?completed in \d+\.\d+s\.\s*', '', cleaned)
    cleaned = re.sub(r'^None', '', cleaned)
    cleaned = re.sub(r'buscar_conteudo_completo_site\(url=.*?\) completed in \d+\.\d+s\.\s*', '', cleaned)
    cleaned = re.sub(r'\w+\(.*?\) completed in \d+\.\d+s\.\s*', '', cleaned)
    
    # Substituir apenas caracteres Unicode problemáticos
    # cleaned = cleaned.replace('∗', '*')  # Substituir asterisco Unicode por asterisco ASCII
    
    # Debug: verificar se há caracteres invisíveis ou problemas de encoding
    special_chars = [c for c in cleaned if ord(c) > 127]
    if special_chars:
        print(f"DEBUG - Caracteres especiais encontrados: {special_chars}")
    
    # Remove espaços em branco extras no início e fim
    cleaned = cleaned.strip()
    
    print(f"DEBUG - Output após limpeza: {repr(cleaned)}")
    
    return cleaned

def send_message_to_agent(url: str, message: str, user_id: str, session_id: str, stream: bool = False) -> Dict[str, Any]:
    """Envia mensagem para o agente via API."""
    payload = {
        "url": url,
        "message": message,
        "user_id": user_id,
        "session_id": session_id,
        "stream": stream
    }
    
    try:
        if stream:
            response = requests.post(STREAM_ENDPOINT, json=payload, stream=True, timeout=30)
            return {"stream_response": response}
        else:
            response = requests.post(CHAT_ENDPOINT, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
    except requests.RequestException as e:
        return {"error": f"Erro ao comunicar com a API: {str(e)}"}

def display_streaming_response(stream_response):
    """Exibe resposta em streaming."""
    message_placeholder = st.empty()
    full_response = ""
    
    try:
        for line in stream_response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    content = line_str[6:]  # Remove 'data: '
                    if content == '[DONE]':
                        break
                    full_response += content
                    # Debug: ver o conteúdo bruto que está sendo recebido
                    print(f"DEBUG - Conteúdo bruto recebido: {repr(content)}")
                    print(f"DEBUG - Resposta acumulada: {repr(full_response)}")
                    
                    # Usar apenas limpeza básica, sem formatação markdown
                    cleaned_response = clean_agent_response(full_response)
                    print(f"DEBUG - Resposta após limpeza: {repr(cleaned_response)}")
                    
                    # Teste: usar st.write em vez de st.markdown para ver se há diferença
                    try:
                        message_placeholder.markdown(cleaned_response)
                    except Exception as e:
                        print(f"DEBUG - Erro no markdown: {e}")
                        message_placeholder.write(cleaned_response)
    except Exception as e:
        st.error(f"Erro no streaming: {str(e)}")
    
    # Retornar a resposta limpa sem formatação adicional
    cleaned_response = clean_agent_response(full_response)
    print(f"DEBUG - Resposta final retornada: {repr(cleaned_response)}")
    return cleaned_response

def main():
    """Função principal da aplicação Streamlit."""
    
    # Configuração da página
    st.set_page_config(
        page_title="Agente especializado em Checkout",
        page_icon="🤖",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # CSS customizado para melhorar o visual
    st.markdown("""
    <style>
    /* Estilo geral da página */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 800px;
        margin: 0 auto;
    }
    
    /* Centralizar o conteúdo */
    .main {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    
    /* Estilo do título */
    .main h1 {
        color: #1f2937;
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        margin-bottom: 1rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    /* Estilo das mensagens do usuário */
    .stChatMessage[data-testid="user"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 18px 18px 4px 18px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
        display: flex;
        align-items: center;
    }
    
    .stChatMessage[data-testid="user"] .stMarkdown {
        color: white;
        margin: 0;
    }
    
    /* Estilo das mensagens do assistente */
    .stChatMessage[data-testid="assistant"] {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border-radius: 18px 18px 18px 4px;
        padding: 1rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        border-left: 4px solid #667eea;
        display: flex;
        align-items: center;
    }
    
    .stChatMessage[data-testid="assistant"] .stMarkdown {
        color: #1f2937;
        margin: 0;
    }
    
    /* Estilo do campo de entrada */
    .stChatInput {
        background: white;
        border-radius: 25px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        border: 2px solid #e2e8f0;
    }
    
    .stChatInput:focus-within {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
    }
    
    /* Estilo do campo de URL */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e2e8f0;
        padding: 0.75rem;
        font-size: 1rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    
    /* Estilo dos botões */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* Estilo dos spinners */
    .stSpinner {
        color: #667eea;
    }
    
    /* Estilo das mensagens de erro */
    .stAlert {
        border-radius: 12px;
        border-left: 4px solid #ef4444;
    }
    
    /* Estilo das mensagens de sucesso */
    .stSuccess {
        border-radius: 12px;
        border-left: 4px solid #10b981;
    }
    
    /* Espaçamento melhorado */
    .stChatMessage {
        margin: 1rem 0;
    }
    
    
    /* Estilo para markdown nas mensagens do assistente */
    .stChatMessage[data-testid="assistant"] h3 {
        color: #1f2937;
        font-size: 1.2rem;
        font-weight: 700;
        margin: 1rem 0 0.5rem 0;
        padding-bottom: 0.25rem;
        border-bottom: 2px solid #667eea;
    }
    
    .stChatMessage[data-testid="assistant"] ul {
        margin: 0.5rem 0;
        padding-left: 1.5rem;
    }
    
    .stChatMessage[data-testid="assistant"] li {
        margin: 0.25rem 0;
        line-height: 1.5;
        color: #374151;
    }
    
    .stChatMessage[data-testid="assistant"] li::marker {
        color: #667eea;
    }
    
    .stChatMessage[data-testid="assistant"] p {
        margin: 0.5rem 0;
        line-height: 1.6;
        color: #374151;
    }
    
    .stChatMessage[data-testid="assistant"] strong {
        color: #1f2937;
        font-weight: 700;
    }
    
    .stChatMessage[data-testid="assistant"] em {
        color: #6b7280;
        font-style: italic;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Título principal com estilo melhorado
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="margin: 0; padding: 0;">🤖 Agente especializado em Checkout</h1>
        <p style="color: #6b7280; font-size: 1.1rem; margin-top: 0.5rem;">
            Analise produtos e sites com inteligência artificial
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Teste de markdown para debug
    with st.expander("🔧 Teste de Markdown (Debug)", expanded=False):
        st.markdown("**Teste de negrito** e *teste de itálico*")
        st.markdown("**R$ 38,00 à vista** ou *8 vezes de R$ 5,41*")
    
    # Verificar status da API
    # if check_api_health():
    #     st.markdown("""
    #     <div style="background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); 
    #                 padding: 1rem; border-radius: 12px; border-left: 4px solid #10b981; 
    #                 margin-bottom: 1rem; text-align: center;">
    #         <h4 style="color: #065f46; margin: 0;">✅ API Conectada</h4>
    #         <p style="color: #047857; margin: 0.5rem 0 0 0; font-size: 0.9rem;">
    #             Sistema funcionando perfeitamente
    #         </p>
    #     </div>
    #     """, unsafe_allow_html=True)
    # else:
    #     st.markdown("""
    #     <div style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); 
    #                 padding: 1rem; border-radius: 12px; border-left: 4px solid #ef4444; 
    #                 margin-bottom: 1rem; text-align: center;">
    #         <h4 style="color: #991b1b; margin: 0;">❌ API Desconectada</h4>
    #         <p style="color: #dc2626; margin: 0.5rem 0 0 0; font-size: 0.9rem;">
    #             Verifique se a API está rodando em http://localhost:8000
    #         </p>
    #     </div>
    #     """, unsafe_allow_html=True)
    #     st.stop()
    
    # Configurações no topo
    col1, col2, col3 = st.columns([1, 2, 1])
    # with col2:
    #     use_streaming = st.checkbox("Usar Streaming", value=True, help="Mostra a resposta em tempo real")
    
    # Inicializar estado da sessão
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "user_id" not in st.session_state:
        st.session_state.user_id = str(uuid.uuid4())
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    # Botão para limpar histórico (discreto no topo)
    if st.session_state.messages:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col3:
            if st.button("🗑️ Limpar Histórico", help="Reiniciar a conversa"):
                st.session_state.messages = []
                st.session_state.session_id = str(uuid.uuid4())
                st.rerun()
    
    # Campo de URL
    url = st.text_input(
        "🌐 URL do Site",
        placeholder="https://exemplo.com/produto",
        help="Cole aqui a URL do site que deseja analisar"
    )
    
    # Exibir histórico de mensagens na conversa
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg['content'])
        else:
            with st.chat_message("assistant"):
                st.markdown(msg['content'])
    
    # Campo de mensagem com chat_input (permite enviar com Enter)
    message = st.chat_input(
        "💬 Digite sua pergunta sobre o produto...",
        key="chat_input"
    )
    
    # Processar nova mensagem se houver
    if message and url:
        # Validar URL
        if not url.startswith(('http://', 'https://')):
            st.error("❌ Por favor, insira uma URL válida (começando com http:// ou https://)")
        else:
            # Adicionar mensagem do usuário ao histórico
            st.session_state.messages.append({
                "role": "user",
                "url": url,
                "content": message,
                "timestamp": time.time()
            })
            
            # Mostrar mensagem do usuário imediatamente
            with st.chat_message("user"):
                st.markdown(message)
            
            # Processar resposta do agente
            with st.chat_message("assistant"):
                with st.spinner("🤖 Analisando..."):
                    response = send_message_to_agent(
                        url=url,
                        message=message,
                        user_id=st.session_state.user_id,
                        session_id=st.session_state.session_id,
                        stream=True
                    )
                
                if "error" in response:
                    st.error(response["error"])
                else:
                    full_response = display_streaming_response(response["stream_response"])
                    
                    # Salvar resposta completa no histórico
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_response,
                        "timestamp": time.time()
                    })

if __name__ == "__main__":
    main()
