"""
Testes de integração para F0-SEC-001 — Bearer Token Guard.

Testa os critérios de aceitação do backlog diretamente:
- Sem token → 401
- Token inválido → 401
- Token correto → request chega à rota (não é bloqueado pelo guard)

Usa TestClient do FastAPI com app mínimo para isolar o guard.
"""

import os
import sys
import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

# Garantir que o módulo guards está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from guards.auth import verify_internal_token

# App mínimo de teste — não depende do agente/scraper
test_app = FastAPI()

@test_app.get("/protected", dependencies=[Depends(verify_internal_token)])
def protected_route():
    return {"message": "acesso permitido"}

@test_app.get("/public")
def public_route():
    return {"message": "rota pública"}

client = TestClient(test_app, raise_server_exceptions=False)

VALID_TOKEN = "test-token-super-secreto-32chars!!"


class TestBearerTokenGuard:
    """Critérios de aceitação F0-SEC-001."""

    def setup_method(self):
        """Configura o token válido antes de cada teste."""
        os.environ["AI_SERVICE_INTERNAL_TOKEN"] = VALID_TOKEN

    def teardown_method(self):
        """Limpa o ambiente após cada teste."""
        os.environ.pop("AI_SERVICE_INTERNAL_TOKEN", None)

    # ─── Critério 1: Sem token → 401 ──────────────────────────────────────
    def test_sem_token_retorna_401(self):
        """Requisição sem header Authorization deve retornar 401."""
        response = client.get("/protected")
        assert response.status_code == 401, (
            f"Esperado 401, recebido {response.status_code}"
        )
        print("✅ CA-1: Sem token → 401")

    # ─── Critério 2: Token inválido → 401 ─────────────────────────────────
    def test_token_invalido_retorna_401(self):
        """Requisição com token errado deve retornar 401."""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer token_completamente_errado"}
        )
        assert response.status_code == 401, (
            f"Esperado 401, recebido {response.status_code}"
        )
        # Garantir que o detalhe não vaza o token real
        body = response.json()
        assert VALID_TOKEN not in str(body), "Token real vazou na resposta!"
        print("✅ CA-2: Token inválido → 401 (sem leak do token real)")

    # ─── Critério 3: Token correto → acesso permitido ─────────────────────
    def test_token_correto_retorna_200(self):
        """Requisição com token correto deve prosseguir normalmente."""
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {VALID_TOKEN}"}
        )
        assert response.status_code == 200, (
            f"Esperado 200, recebido {response.status_code}"
        )
        assert response.json()["message"] == "acesso permitido"
        print("✅ CA-3: Token correto → 200 (acesso permitido)")

    # ─── Critério 4: Token não aparece nos logs ────────────────────────────
    def test_token_nao_vaza_na_resposta_de_erro(self):
        """O corpo das respostas de erro não deve conter o token."""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer token_errado"}
        )
        body = str(response.json())
        assert "token_errado" not in body
        assert VALID_TOKEN not in body
        print("✅ CA-4: Token não vaza na resposta de erro")

    # ─── Critério extra: Rota pública não exige token ─────────────────────
    def test_rota_publica_nao_requer_token(self):
        """/health e / são públicas — não devem exigir token."""
        response = client.get("/public")
        assert response.status_code == 200
        print("✅ CA-5: Rota pública não requer token")

    # ─── Critério extra: Variável não configurada → 503 ───────────────────
    def test_sem_env_retorna_503(self):
        """Se AI_SERVICE_INTERNAL_TOKEN não está configurado, retorna 503."""
        os.environ.pop("AI_SERVICE_INTERNAL_TOKEN", None)
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer qualquer_coisa"}
        )
        assert response.status_code == 503, (
            f"Esperado 503 (configuração ausente), recebido {response.status_code}"
        )
        print("✅ CA-6: Sem variável de ambiente → 503 (configuração ausente)")


if __name__ == "__main__":
    # Execução direta sem pytest
    suite = TestBearerTokenGuard()
    tests = [
        suite.test_sem_token_retorna_401,
        suite.test_token_invalido_retorna_401,
        suite.test_token_correto_retorna_200,
        suite.test_token_nao_vaza_na_resposta_de_erro,
        suite.test_rota_publica_nao_requer_token,
        suite.test_sem_env_retorna_503,
    ]
    passed = 0
    failed = 0
    for test in tests:
        suite.setup_method()
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FALHOU: {test.__name__} — {e}")
            failed += 1
        finally:
            suite.teardown_method()

    print(f"\n{'='*50}")
    print(f"Resultado: {passed} passaram, {failed} falharam")
    if failed > 0:
        sys.exit(1)
