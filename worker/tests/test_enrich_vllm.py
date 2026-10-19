import pytest
from helpers import CATEGORIES, fixture

from veille_worker.extract import html_to_text
from veille_worker.llm import enrich_fr


@pytest.mark.slow
def test_real_vllm_returns_french_title_three_sentences_and_known_category():
    text = html_to_text(fixture("article.html").decode())

    result = enrich_fr(text, "Introducing Model X", CATEGORIES)

    assert result.title_fr and result.title_fr != "Introducing Model X"
    assert len(result.summary) == 3
    assert all(s.strip() for s in result.summary)
    assert result.category in {c.slug for c in CATEGORIES}
    assert result.category == "modeles"
