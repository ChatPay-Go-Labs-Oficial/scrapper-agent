"""Unit tests for the output guard (F2-SEC-002)."""

from llm.output_guard import check_output


def test_blocks_literal_window():
    chunk = "Este produto tem garantia de 30 dias e suporte vitalicio para todos os compradores"
    response = "Este produto tem garantia de 30 dias e suporte vitalicio para todos os compradores"
    assert check_output(response, [chunk], threshold_words=12) is False


def test_allows_paraphrase():
    chunk = "Este produto tem garantia de 30 dias e suporte vitalicio para todos os compradores"
    response = "O produto oferece 30 dias de garantia e suporte sem prazo de validade"
    assert check_output(response, [chunk], threshold_words=15) is True


def test_allows_short_chunk():
    chunk = "Garantia de 30 dias"
    response = "Garantia de 30 dias"
    assert check_output(response, [chunk], threshold_words=15) is True
