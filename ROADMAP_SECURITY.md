# 🗺️ Roadmap de Melhorias de Segurança

**Projeto:** agno-scraper-agent
**Data:** 2026-02-02
**Status:** Implementações futuras recomendadas

---

## 📋 Visão Geral

Este documento outlines recomendações para melhorar a segurança, performance e monitoramento do agente de pesquisa de produtos. As implementações estão ordenadas por **prioridade** e **complexidade**.

---

## 🔴 Prioridade ALTA

### 1. Rate Limiting (Limitação de Taxa)

**Descrição:** Limitar o número de requisições que um usuário pode fazer em um período de tempo.

**Motivo:**
- Prevenir abuso do serviço
- Proteger contra ataques de DDoS
- Controlar custos de API do LLM
- Evitar scraping excessivo

**Implementação sugerida:**

\`\`\`python
# requirements.txt adicionar:
# slowapi==0.1.9
# fastapi-limiter==0.1.5

# api.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/chat")
@limiter.limit("10/minute")  # 10 requisições por minuto
async def chat_with_agent(request: ChatRequest, http_request: Request):
    # ... código existente
\`\`\`

**Configurações recomendadas:**
- Usuários gratuitos: 10 requisições/minuto
- Usuários autenticados: 60 requisições/minuto
- Enterprise: customizado

**Esforço:** ⭐⭐ (Médio)
**Impacto:** 🔒🔒🔒 (Alto)

---

### 2. Autenticação e Autorização

**Descrição:** Adicionar camada de autenticação para controlar acesso à API.

**Motivo:**
- Rastrear quem está usando o sistema
- Implementar rate limiting por usuário
- Permitir diferentes níveis de acesso
- Auditar ações

**Implementação sugerida:**

\`\`\`python
# requirements.txt adicionar:
# python-jose[cryptography]==3.3.0
# passlib[bcrypt]==1.7.4
# python-multipart==0.0.6

# auth.py (novo arquivo)
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

# api.py - adicionar aos endpoints
@app.post("/chat")
async def chat_with_agent(
    request: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    # user_id vem do token, não da request
    request.user_id = user_id
    # ... resto do código
\`\`\`

**Planos de acesso sugeridos:**
- **Free:** 50 requisições/dia
- **Pro:** 500 requisições/dia
- **Enterprise:** Ilimitado + SLA

**Esforço:** ⭐⭐⭐ (Alto)
**Impacto:** 🔒🔒🔒 (Alto)

---

### 3. Allowlist de Domínios

**Descrição:** Configurar domínios permitidos por cliente/usuário.

**Motivo:**
- Prevenir acesso a sites não autorizados
- Proteger contra scraping de sites maliciosos
- Atender requisitos de compliance

**Implementação sugerida:**

\`\`\`python
# domain_whitelist.py (novo arquivo)
from typing import Set, Optional
import json

class DomainWhitelist:
    def __init__(self, config_file: str = "config/allowed_domains.json"):
        with open(config_file, 'r') as f:
            self.domains = json.load(f)

    def is_allowed(self, url: str, user_id: Optional[str] = None) -> tuple[bool, str]:
        """Verifica se URL está na allowlist do usuário ou global."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc

        # Verificar allowlist global
        if domain in self.domains.get("global", []):
            return True, ""

        # Verificar allowlist do usuário
        if user_id and user_id in self.domains.get("users", {}):
            if domain in self.domains["users"][user_id]:
                return True, ""

        return False, f"Domínio {domain} não está autorizado"

# config/allowed_domains.json
{
  "global": ["example.com", "trusted-site.com"],
  "users": {
    "user_123": ["client1.com", "client2.com"],
    "user_456": ["another-client.com"]
  }
}

# api.py - integrar na validação
from domain_whitelist import DomainWhitelist

whitelist = DomainWhitelist()

@app.post("/chat")
def chat_with_agent(request: ChatRequest):
    # ... validações existentes

    # Nova validação
    is_allowed, msg = whitelist.is_allowed(request.url, request.user_id)
    if not is_allowed:
        logger.warning(f"Tentativa de acessar domínio não autorizado: {request.url}")
        raise HTTPException(status_code=403, detail=msg)

    # ... resto do código
\`\`\`

**Esforço:** ⭐⭐ (Médio)
**Impacto:** 🔒🔒 (Médio)

---

## 🟡 Prioridade MÉDIA

### 4. Cache de Scraping

**Descrição:** Implementar cache para evitar scraping repetido da mesma URL.

**Motivo:**
- Melhorar performance (respostas mais rápidas)
- Reduzir carga em servidores externos
- Economizar recursos
- Evitar bloqueios por scraping excessivo

**Implementação sugerida:**

\`\`\`python
# requirements.txt adicionar:
# redis==5.0.1
# or use: cachetools==5.3.2

# cache.py (novo arquivo)
from cachetools import TTLCache
import hashlib
import json

class ScrapingCache:
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """Cache com TTL de 1 hora por padrão."""
        self.cache = TTLCache(maxsize=max_size, ttl=ttl)

    def _generate_key(self, url: str) -> str:
        """Gera chave única baseada na URL."""
        return hashlib.md5(url.encode()).hexdigest()

    def get(self, url: str) -> Optional[str]:
        """Retorna conteúdo em cache ou None."""
        key = self._generate_key(url)
        return self.cache.get(key)

    def set(self, url: str, content: str) -> None:
        """Salva conteúdo no cache."""
        key = self._generate_key(url)
        self.cache[key] = content

# api.py - integrar
from cache import ScrapingCache

cache = ScrapingCache(max_size=1000, ttl=3600)

@app.post("/chat")
def chat_with_agent(request: ChatRequest):
    # ... validações

    # Tentar obter do cache primeiro
    site_content = cache.get(request.url)

    if not site_content:
        logger.info(f"Cache miss - fazendo scraping de: {request.url}")
        site_content = buscar_conteudo_completo_site(request.url)
        cache.set(request.url, site_content)
    else:
        logger.info(f"Cache hit - usando conteúdo em cache: {request.url}")

    # ... resto do código
\`\`\`

**Configurações recomendadas:**
- TTL: 1 hora (configurável)
- Tamanho máximo: 1000 URLs
- Para produção: Usar Redis ao invés de TTLCache

**Esforço:** ⭐⭐ (Médio)
**Impacto:** ⚡⚡⚡ (Alto - Performance)

---

### 5. Monitoramento e Logging Avançado

**Descrição:** Implementar sistema completo de monitoramento e alertas.

**Motivo:**
- Detectar ataques em tempo real
- Analisar padrões de uso
- Debugar problemas
- Métricas de business

**Implementação sugerida:**

\`\`\`python
# requirements.txt adicionar:
# prometheus-fastapi-instrumentator==7.0.0
# python-json-logger==2.0.7

# monitoring.py (novo arquivo)
from prometheus_fastapi_instrumentator import Instrumentator
import logging
from pythonjsonlogger import jsonlogger

# Configurar logging estruturado
def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Métricas personalizadas
from prometheus_client import Counter

security_alerts = Counter(
    'security_alerts_total',
    'Total de alertas de segurança',
    ['alert_type']
)

scraping_requests = Counter(
    'scraping_requests_total',
    'Total de requisições de scraping',
    ['status']
)
\`\`\`

**Esforço:** ⭐⭐⭐ (Alto)
**Impacto:** 📊📊 (Médio - Observabilidade)

---

### 6. Validação de Conteúdo

**Descrição:** Validar e filtrar conteúdo malicioso extraído de sites.

**Motivo:**
- Prevenir XSS (Cross-Site Scripting)
- Filtrar conteúdo adulto/ilegal
- Remover scripts maliciosos
- Sanitizar HTML/Markdown

**Implementação sugerida:**

\`\`\`python
# requirements.txt adicionar:
# bleach==6.1.0
# beautifulsoup4==4.12.3

# content_validator.py (novo arquivo)
import bleach
from bs4 import BeautifulSoup

class ContentValidator:
    # Tags permitidas (seguro por padrão)
    ALLOWED_TAGS = [
        'p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
    ]

    # Atributos permitidos
    ALLOWED_ATTRIBUTES = {
        'a': ['href', 'title'],
        '*': ['class']
    }

    def sanitize(self, content: str) -> tuple[str, bool]:
        """Sanitiza conteúdo HTML/Markdown."""
        # Remover scripts e estilos perigosos
        soup = BeautifulSoup(content, 'html.parser')
        
        for tag in soup(['script', 'style', 'iframe', 'object', 'embed']):
            tag.decompose()

        clean_content = bleach.clean(
            str(soup),
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            strip=True
        )

        was_modified = clean_content != content
        return clean_content, was_modified
\`\`\`

**Esforço:** ⭐⭐ (Médio)
**Impacto:** 🔒🔒 (Médio)

---

## 🟢 Prioridade BAIXA

### 7. Suporte a Proxy

**Descrição:** Permitir configuração de proxy para requests de saída.

**Motivo:**
- Acessar sites que bloqueiam IPs de cloud
- Rotacionar IPs para evitar bloqueios
- Requisito de compliance em algumas empresas

**Implementação:**

\`\`\`python
# env.example
PROXY_URL=http://proxy.example.com:8080
PROXY_USERNAME=
PROXY_PASSWORD=

# tools/web_scraper.py
import os
from httpx import Proxy

def get_proxy_config():
    proxy_url = os.getenv("PROXY_URL")
    if not proxy_url:
        return None
    
    username = os.getenv("PROXY_USERNAME")
    password = os.getenv("PROXY_PASSWORD")
    
    if username and password:
        proxy_url = proxy_url.replace("://", f"://{username}:{password}@")
    
    return Proxy(url=proxy_url)
\`\`\`

**Esforço:** ⭐ (Baixo)
**Impacto:** 🔧 (Baixo)

---

### 8. Retry com Exponential Backoff

**Descrição:** Implementar tentativas automáticas com backoff exponencial.

**Motivo:**
- Lidar com falhas temporárias de rede
- Melhorar taxa de sucesso
- Ser gentil com servidores externos

**Implementação:**

\`\`\`python
# requirements.txt adicionar:
# tenacity==8.2.3

# tools/web_scraper.py
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def buscar_conteudo_completo_site(url: str) -> str:
    """Busca conteúdo com retry automático."""
    # ... código existente
\`\`\`

**Esforço:** ⭐ (Baixo)
**Impacto:** ⚡⚡ (Médio)

---

## 📊 Matriz de Priorização

| Recurso | Prioridade | Esforço | Impacto | ROI |
|---------|-----------|---------|---------|-----|
| Rate Limiting | 🔴 ALTA | ⭐⭐ | 🔒🔒🔒 | **ALTO** |
| Autenticação | 🔴 ALTA | ⭐⭐⭐ | 🔒🔒🔒 | **ALTO** |
| Allowlist Domínios | 🔴 ALTA | ⭐⭐ | 🔒🔒 | **MÉDIO** |
| Cache Scraping | 🟡 MÉDIA | ⭐⭐ | ⚡⚡⚡ | **ALTO** |
| Monitoramento | 🟡 MÉDIA | ⭐⭐⭐ | 📊📊 | **MÉDIO** |
| Validação Conteúdo | 🟡 MÉDIA | ⭐⭐ | 🔒🔒 | **MÉDIO** |
| Suporte Proxy | 🟢 BAIXA | ⭐ | 🔧 | **BAIXO** |
| Retry Backoff | 🟢 BAIXA | ⭐ | ⚡⚡ | **MÉDIO** |

---

## 🎯 Recomendação de Implementação

### Fase 1 - Fundamentos de Segurança (1-2 semanas)
1. Rate Limiting
2. Autenticação básica
3. Cache de scraping

### Fase 2 - Monitoramento e Compliance (1 semana)
4. Monitoramento básico
5. Allowlist de domínios

### Fase 3 - Melhorias de Performance (1 semana)
6. Retry com backoff
7. Validação de conteúdo

---

## 📝 Checklist de Implementação

### 🔴 Prioridade ALTA
- [ ] Rate Limiting implementado
- [ ] Autenticação JWT configurada
- [ ] Allowlist de domínios ativa

### 🟡 Prioridade MÉDIA
- [ ] Cache de scraping funcional
- [ ] Dashboard de monitoramento
- [ ] Validação de conteúdo ativada

### 🟢 Prioridade BAIXA
- [ ] Suporte a proxy configurado
- [ ] Retry com exponential backoff
- [ ] Documentação OpenAPI detalhada

---

## 🔗 Recursos Adicionais

### Bibliotecas Recomendadas
- **Security:** \`slowapi\`, \`python-jose\`, \`passlib\`
- **Cache:** \`redis-py\`, \`cachetools\`
- **Monitoring:** \`prometheus-fastapi-instrumentator\`
- **Sanitização:** \`bleach\`, \`beautifulsoup4\`
- **Resiliência:** \`tenacity\`

### Leituras Recomendadas
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
- [Prompt Injection Guide](https://prompt-injection-guide.com/)

---

**Última atualização:** 2026-02-02  
**Versão:** 1.0.0  
**Status:** ✅ Segurança base implementada | 🚀 Melhorias futuras planejadas
