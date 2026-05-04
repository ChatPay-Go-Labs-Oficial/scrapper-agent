"""
Guard de entrada para detectar prompt injection e exfiltracao.
"""

from dataclasses import dataclass
import re

INJECTION_PATTERNS = [
    r"(?i)(ignore|desconsidere|esque[cç]a).{0,50}(instru[cç][aã]o|instru[cç][oõ]es|instructions)",
    r"(?i)(override|sobrescrever).{0,30}(system|config|prompt)",
    r"(?i)(act as|atue como|you are now).{0,30}(different|outro|novo)",
    r"(?i)(developer mode|jailbreak|dan mode)",
    r"(?i)(mude|alterar|trocar).{0,30}(regras|guardrails|politica|policy)",
    r"(?i)(siga|ignore).{0,30}(instru[cç][oõ]es|prompt)",
]

EXFILTRATION_PATTERNS = [
    r"(?i)(liste?|escreva?|copie?|transcreva?|reproduza?).{0,40}(cap[ií]tulo|conte[uú]do|material|livro|texto completo|tudo)",
    r"(?i)(me d[êe]|quero ver|preciso de).{0,30}(conte[uú]do (completo|inteiro|todo))",
    r"(?i)(resumo (completo|de tudo|inteiro))",
    r"(?i)(qual [eé] o texto|repita exatamente|palavra por palavra)",
    r"(?i)(quantas? (p[aá]ginas?|cap[ií]tulos?|se[cç][oõ]es?))",
    r"(?i)([ií]ndice|sum[aá]rio|table of contents)",
    r"(?i)(dump|export|print all|liste todos)",
    r"(?i)(transcreva|copie).{0,20}(ebook|pdf)",
]


@dataclass
class GuardResult:
    passed: bool
    blocked_reason: str | None = None
    is_injection: bool = False
    is_exfiltration: bool = False


EXFILTRATION_RESPONSE = (
    "Esse conteudo faz parte do material exclusivo para quem adquire o produto. "
    "Posso te ajudar com duvidas especificas?"
)

INJECTION_RESPONSE = (
    "So posso ajudar com informacoes sobre esse produto. "
    "Tem alguma duvida sobre ele?"
)


def check_input(message: str) -> GuardResult:
    if not message:
        return GuardResult(passed=True)

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, message):
            return GuardResult(
                passed=False,
                blocked_reason="injection_attempt",
                is_injection=True,
            )

    for pattern in EXFILTRATION_PATTERNS:
        if re.search(pattern, message):
            return GuardResult(
                passed=False,
                blocked_reason="exfiltration_attempt",
                is_exfiltration=True,
            )

    return GuardResult(passed=True)
