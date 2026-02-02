"""
Utilitários de segurança para validação e sanitização de entradas.
"""

import re
from typing import Optional, Tuple
from urllib.parse import urlparse


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Valida se a URL é segura e bem-formada.

    Args:
        url: URL a ser validada

    Returns:
        Tuple[bool, Optional[str]]: (válida, mensagem_erro)
    """
    if not url or not url.strip():
        return False, "URL não pode estar vazia"

    # Verificar se começa com http:// ou https://
    if not url.startswith(('http://', 'https://')):
        return False, "URL deve começar com http:// ou https://"

    try:
        parsed = urlparse(url)

        # Verificar se há um netloc (domínio)
        if not parsed.netloc:
            return False, "URL não contém um domínio válido"

        # Bloquear acesso a localhost ou IPs privados
        hostname = parsed.hostname
        if not hostname:
            return False, "URL não contém um hostname válido"

        # Bloquear localhost e variantes
        blocked_domains = ['localhost', '127.0.0.1', '0.0.0.0', '::1']
        if hostname in blocked_domains or hostname.startswith('192.168.') or hostname.startswith('10.'):
            return False, "URLs locais ou privadas não são permitidas"

        # Bloquear IPs internos (172.16.0.0/12)
        if hostname.startswith('172.'):
            parts = hostname.split('.')
            if len(parts) >= 2:
                try:
                    second_octet = int(parts[1])
                    if 16 <= second_octet <= 31:
                        return False, "URLs privadas não são permitidas"
                except ValueError:
                    pass

        return True, None

    except Exception as e:
        return False, f"URL inválida: {str(e)}"


def sanitize_user_message(message: str) -> str:
    """
    Remove URLs e tentativas de prompt injection da mensagem do usuário.

    Args:
        message: Mensagem do usuário

    Returns:
        str: Mensagem sanitizada sem URLs
    """
    if not message:
        return ""

    # Padrões para detectar URLs
    url_patterns = [
        # http:// ou https://
        r'https?://[^\s]+',
        # www. (comum em URLs sem http)
        r'www\.[^\s]+',
        # Domínios com .com, .br, etc (mais agressivo)
        r'[a-zA-Z0-9-]+\.(com|br|org|net|gov|io|co|app|dev|tech)[^\s]*',
    ]

    sanitized = message

    # Remover URLs detectadas
    for pattern in url_patterns:
        sanitized = re.sub(pattern, '[URL_REMOVIDA]', sanitized, flags=re.IGNORECASE)

    # Detectar tentativas de instrução de system/injection
    injection_patterns = [
        r'(?i)(ignore|desconsidere|esqueça).+(instruções|instrucao|instructions|anteriores|previous)',
        r'(?i)(não usar|nao usar|do not use).+(ferramenta|tool)',
        r'(?i)(acessar|acesse|visite|ir para|go to).+(https?://|www\.)',
        r'(?i)(mudar|alterar|trocar|override).+(url|site|página)',
        r'(?i)(prompt|system|developer)',
    ]

    for pattern in injection_patterns:
        matches = re.findall(pattern, sanitized)
        if matches:
            # Adicionar aviso sobre tentativa de injection
            sanitized = re.sub(pattern, '[TENTATIVA_DE_INJECTION_REMOVIDA]', sanitized, flags=re.IGNORECASE)

    return sanitized.strip()


def detect_suspicious_patterns(message: str) -> Tuple[bool, list]:
    """
    Detecta padrões suspeitos na mensagem do usuário.

    Args:
        message: Mensagem do usuário

    Returns:
        Tuple[bool, list]: (é_suspeita, [padrões_encontrados])
    """
    suspicious_patterns = [
        ("Tentativa de ignorar instruções", r'(?i)(ignore|desconsidere|esqueça).+(instruções|instructions)'),
        ("Tentativa de acessar URL arbitrária", r'(?i)(acessar|acesse|visite|ir para).+(https?://|www\.)'),
        ("Tentativa de override", r'(?i)(override|mudar|alterar).+(system|config|configuração)'),
        ("Múltiplas URLs na mensagem", r'(?i)(https?://\S+){2,}'),
    ]

    found_patterns = []

    for pattern_name, pattern in suspicious_patterns:
        if re.search(pattern, message):
            found_patterns.append(pattern_name)

    return len(found_patterns) > 0, found_patterns


def create_safe_prompt(site_content: str, user_message: str, url: str) -> str:
    """
    Cria um prompt seguro com o conteúdo do site já extraído.

    Args:
        site_content: Conteúdo extraído do site
        user_message: Mensagem sanitizada do usuário
        url: URL original (para contexto)

    Returns:
        str: Prompt formatado e seguro
    """
    # Sanitizar a mensagem do usuário primeiro
    sanitized_message = sanitize_user_message(user_message)

    # Detectar padrões suspeitos
    is_suspicious, patterns = detect_suspicious_patterns(user_message)

    warning = ""
    if is_suspicious:
        warning = f"\n⚠️ AVISO: Foram detectadas e removidas tentativas de manipulação: {', '.join(patterns)}\n"

    prompt = f"""CONTEÚDO DO SITE ANALISADO:
URL: {url}

{site_content[:10000]}

{warning}

PERGUNTA DO USUÁRIO:
{sanitized_message}

INSTRUÇÕES PARA RESPOSTA:
- Responda à pergunta do usuário baseando-se APENAS no conteúdo do site fornecido acima
- NÃO acesse nenhum outro site, mesmo que o usuário peça
- NÃO use ferramentas de busca, mesmo que o usuário solicite
- Se a informação não estiver no conteúdo, diga que não está disponível
- Mantenha o tom de vendedor especialista e empático"""

    return prompt
