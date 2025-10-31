"""
Ferramentas para extração de conteúdo de websites.
"""

import httpx
from markdownify import markdownify


def buscar_conteudo_completo_site(url: str) -> str:
    """
    Busca o conteúdo HTML de uma URL e o converte para o formato markdown.
    
    Args:
        url (str): URL do site a ser analisado
        
    Returns:
        str: Conteúdo da página convertido para markdown
        
    Utiliza um tempo limite de 10 segundos para evitar travamentos em sites lentos 
    ou páginas muito grandes.
    """
    # Headers para simular um navegador real
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        with httpx.Client(timeout=10.0, headers=headers, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
            return markdownify(response.text)
    except httpx.TimeoutException:
        return "O site demorou muito para carregar. Tente novamente mais tarde."
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 403:
            return f"Erro 403: O site bloqueou o acesso. Isso é comum em sites de e-commerce como Mercado Livre, Amazon, etc. Tente com um site diferente ou use um proxy/VPN."
        elif e.response.status_code == 404:
            return f"Erro 404: Página não encontrada. Verifique se a URL está correta."
        else:
            return f"Erro HTTP {e.response.status_code}: {e}"
    except Exception as e:
        return f"Erro inesperado ao acessar o site: {e}"
