"""Output guard to prevent literal exfiltration of protected content."""

from __future__ import annotations

OUTPUT_BLOCKED_RESPONSE = (
    "Nao consigo apresentar essa informacao dessa forma. "
    "Posso te ajudar de outra maneira com duvidas sobre o produto?"
)


def check_output(response: str, chunks_used: list[str], threshold_words: int = 15) -> bool:
    """
    Return True when the response is safe.

    It blocks when a window of N consecutive words from any chunk appears
    literally in the response.
    """
    if not response or not chunks_used:
        return True

    response_lower = response.lower()

    for chunk in chunks_used:
        words = chunk.lower().split()
        if len(words) < threshold_words:
            continue

        for i in range(0, len(words) - threshold_words + 1):
            window = " ".join(words[i : i + threshold_words])
            if window in response_lower:
                return False

    return True
