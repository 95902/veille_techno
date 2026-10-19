import pytest
from helpers import fixture, http_client

from veille_worker.extract import NoUsableTextError, article_text, html_to_text, truncate

PAGE = "https://lab.example.com/news/model-x"
LIMITS = {"min_extracted_chars": 500, "min_text_chars": 150, "max_chars": 12_000}
FEED_TEXT = (
    "The Agents SDK reaches version 2.0 with tracing, handoffs and guardrails. Developers can "
    "now build multi-agent workflows with a few lines of code, and deploy them on any cloud."
)


def test_page_text_is_extracted_without_boilerplate():
    text = article_text(
        url=PAGE, source_type="rss", feed_content="teaser",
        client=http_client({PAGE: fixture("article.html")}), **LIMITS,
    )

    assert "Model X was trained on 15 trillion tokens" in text
    assert "Careers" not in text and "All rights reserved" not in text


def test_empty_page_falls_back_to_feed_content():
    text = article_text(
        url=PAGE, source_type="rss", feed_content=FEED_TEXT,
        client=http_client({PAGE: fixture("empty.html")}), **LIMITS,
    )

    assert text == FEED_TEXT


def test_unreachable_page_falls_back_to_feed_content():
    text = article_text(
        url=PAGE, source_type="rss", feed_content=FEED_TEXT,
        client=http_client({PAGE: 403}), **LIMITS,
    )

    assert text == FEED_TEXT


def test_arxiv_uses_the_feed_abstract_without_fetching_the_page():
    def must_not_fetch(request):
        raise AssertionError("arXiv : la page ne doit pas être téléchargée")

    text = article_text(
        url="https://arxiv.org/abs/2610.11111", source_type="arxiv", feed_content=FEED_TEXT,
        client=http_client({"https://arxiv.org/abs/2610.11111": must_not_fetch}), **LIMITS,
    )

    assert text == FEED_TEXT


def test_no_usable_text_raises():
    with pytest.raises(NoUsableTextError, match="aucun texte exploitable"):
        article_text(
            url=PAGE, source_type="rss", feed_content="Short teaser.",
            client=http_client({PAGE: fixture("empty.html")}), **LIMITS,
        )


def test_long_text_is_truncated_within_the_budget():
    long_text = "word " * 10_000

    text = article_text(
        url="https://arxiv.org/abs/1", source_type="arxiv", feed_content=long_text,
        client=http_client({}), **{**LIMITS, "max_chars": 1_000},
    )

    assert len(text) <= 1_000
    assert text.endswith("[…]")


@pytest.mark.parametrize("budget", [50, 51, 999, 1000])
def test_truncate_never_exceeds_budget(budget):
    assert len(truncate("abcdefghij " * 500, budget)) <= budget
    assert len(truncate("x" * 5000, budget)) <= budget


def test_html_to_text_strips_tags_scripts_and_entities():
    assert html_to_text("<p>A &amp; B</p><script>evil()</script><p>C</p>") == "A & B\n\nC"
