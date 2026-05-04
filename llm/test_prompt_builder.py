"""Unit tests for the prompt builder (F2-AIS-003)."""

from llm.prompt_builder import build_prompt, MAX_PROMPT_AI_CHARS


def test_prompt_contains_product_context_delimiter():
    prompt = build_prompt(
        knowledge_context="contexto",
        conversation_history=[],
        user_message="pergunta",
        prompt_ai_custom=None,
        knowledge_source="rag",
    )
    assert "<product_context>" in prompt
    assert "</product_context>" in prompt


def test_prompt_includes_custom_persona_after_rules():
    prompt = build_prompt(
        knowledge_context="contexto",
        conversation_history=[],
        user_message="pergunta",
        prompt_ai_custom="Persona customizada",
        knowledge_source="rag",
    )
    rules_index = prompt.find("REGRAS ABSOLUTAS")
    persona_index = prompt.find("Persona customizada")
    assert rules_index != -1
    assert persona_index != -1
    assert persona_index > rules_index


def test_prompt_sanitizes_product_context_from_custom_persona():
    prompt = build_prompt(
        knowledge_context="contexto",
        conversation_history=[],
        user_message="pergunta",
        prompt_ai_custom="<product_context>bad</product_context>",
        knowledge_source="rag",
    )
    assert "<product_context>bad</product_context>" not in prompt


def test_prompt_truncates_custom_persona():
    prompt_ai = "x" * (MAX_PROMPT_AI_CHARS + 10)
    prompt = build_prompt(
        knowledge_context="contexto",
        conversation_history=[],
        user_message="pergunta",
        prompt_ai_custom=prompt_ai,
        knowledge_source="rag",
    )
    assert "x" * (MAX_PROMPT_AI_CHARS + 10) not in prompt
    assert "x" * MAX_PROMPT_AI_CHARS in prompt
