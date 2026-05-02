"""
Módulo responsável por fazer o cache do conteúdo de scraping no Redis.
"""

import os
import logging
import redis
from typing import Optional
from tools.web_scraper import buscar_conteudo_completo_site

logger = logging.getLogger(__name__)

# Configurar cliente Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
# Usamos decode_responses=True para retornar string em vez de bytes
try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3)
except Exception as e:
    logger.error(f"Erro ao inicializar cliente Redis: {e}")
    redis_client = None

CACHE_TTL_SECONDS = 86400  # 24 horas

def get_or_fetch(product_id: Optional[str], url: str) -> str:
    """
    Busca o conteúdo no cache ou faz scraping se não existir/se o Redis estiver fora.
    
    Args:
        product_id: ID opcional do produto (usado preferencialmente como chave)
        url: URL do produto (usada como chave de fallback se product_id não for fornecido)
        
    Returns:
        str: Conteúdo extraído do site
    """
    cache_key = None
    
    if product_id:
        cache_key = f"scraping:product:{product_id}"
    elif url:
        cache_key = f"scraping:url:{url}"
        
    # Tentar buscar do cache
    if cache_key and redis_client is not None:
        try:
            cached_content = redis_client.get(cache_key)
            if cached_content:
                logger.debug(f"Cache HIT - usando conteúdo em cache para chave: {cache_key}")
                return cached_content
            logger.debug(f"Cache MISS - fazendo scraping para chave: {cache_key}")
        except Exception as e:
            logger.error(f"Erro ao acessar Redis (Cache ignorado): {e}")
            # Em caso de erro no Redis, fallback para scraping normal (resiliência)
    
    # Faz o scraping usando a ferramenta original
    logger.info(f"Fazendo scraping real da URL: {url}")
    site_content = buscar_conteudo_completo_site(url)
    
    # Se o scraping for bem-sucedido e não for um erro
    if not (site_content.startswith("Erro") or site_content.startswith("O site demorou")):
        # Salvar no cache
        if cache_key and redis_client is not None:
            try:
                redis_client.setex(name=cache_key, time=CACHE_TTL_SECONDS, value=site_content)
                logger.debug(f"Conteúdo salvo no cache com TTL 24h: {cache_key}")
            except Exception as e:
                logger.error(f"Erro ao salvar no Redis (Cache ignorado): {e}")
                
    return site_content
