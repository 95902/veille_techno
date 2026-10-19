from datetime import UTC, datetime
from email.utils import format_datetime

import httpx
import psycopg
import pytest
from helpers import CATEGORIES, NOW, FakeRepo, fixture, http_client, source

from veille_worker import collect as collect_module
from veille_worker import extract
from veille_worker.collect import Report, run
from veille_worker.config import Settings
from veille_worker.db import URL_MAX_CHARS
from veille_worker.llm import Enrichment, LLMInvalidOutputError, LLMUnavailableError

SETTINGS = Settings(max_attempts=3)
LAB = "https://lab.example.com/feed.xml"
PRESS = "https://press.example.org/ai/feed"
ARXIV = "https://export.arxiv.org/rss/cs.CL"
MODEL_X = "https://lab.example.com/news/model-x"
AGENTS = "https://lab.example.com/news/agents-sdk"
SAFETY = "https://lab.example.com/news/safety-report"
AI_ACT = "https://press.example.org/2026/10/ai-act-2027"
PAPER = "https://arxiv.org/abs/2610.11111"

ROUTES = {
    LAB: fixture("lab_blog.rss.xml"),
    PRESS: fixture("press.atom.xml"),
    ARXIV: fixture("arxiv.rss.xml"),
    # Pages réelles : Model X a un article complet, les autres pages sont vides ou absentes
    # (le texte vient alors du flux).
    "https://lab.example.com/news/model-x?utm_source=rss&utm_medium=feed": fixture("article.html"),
    AGENTS: fixture("empty.html"),
    SAFETY: fixture("article.html"),
}


class FakeEnricher:
    """LLM simulé : valide par défaut, ou erreur programmée pour certains titres."""

    def __init__(self, errors: dict[str, Exception] | None = None) -> None:
        self.errors = errors or {}
        self.calls: list[tuple[str, str]] = []

    def __call__(self, text, title, categories):
        self.calls.append((title, text))
        assert [c.slug for c in categories] == [c.slug for c in CATEGORIES]
        if title in self.errors:
            raise self.errors[title]
        return Enrichment(
            title_fr=f"FR : {title}",
            summary=["Phrase une.", "Phrase deux.", "Phrase trois."],
            category="reglementation" if "AI Act" in title else "modeles",
        )


def sources():
    return [source(1, LAB), source(2, PRESS), source(3, ARXIV, type="arxiv", max_items=10)]


def collect(repo, enricher, routes=ROUTES, now=NOW) -> Report:
    return run(repo, http_client(routes), SETTINGS, enricher, now=now)


def test_first_run_creates_recent_articles_and_summarizes_them():
    repo = FakeRepo(sources())

    report = collect(repo, FakeEnricher())

    urls = {a.normalized_url for a in repo.articles}
    # Doublon utm_* dédoublonné, billet de 10 jours et billet non daté exclus.
    assert urls == {MODEL_X, AGENTS, SAFETY, AI_ACT, PAPER}
    assert report.sources_ok == ["Source 1", "Source 2", "Source 3"]
    assert (report.new_articles, report.summarized, report.failed) == (5, 5, 0)
    for article in repo.articles:
        assert article.status == "summarized"
        assert article.title_fr.startswith("FR : ")
        assert article.summary.split("\n") == ["Phrase une.", "Phrase deux.", "Phrase trois."]
        assert article.category_id in {c.id for c in CATEGORIES}
        assert article.attempts == 1 and article.last_error is None
    assert repo.by_url(AI_ACT).category_id == 3


def test_second_run_creates_no_duplicate():
    repo = FakeRepo(sources())
    collect(repo, FakeEnricher())
    first = {a.normalized_url: a.id for a in repo.articles}
    enricher = FakeEnricher()

    report = collect(repo, enricher)

    urls = [a.normalized_url for a in repo.articles]
    assert len(urls) == len(set(urls))
    assert all(repo.by_url(url).id == id_ for url, id_ in first.items())
    # Seule l'entrée non datée, exclue du premier passage, arrive ; rien n'est re-résumé.
    assert set(urls) - set(first) == {"https://lab.example.com/news/undated"}
    assert report.new_articles == 1
    assert report.summarized == 0
    assert enricher.calls == []


def test_unchanged_feeds_add_nothing_on_the_third_run():
    repo = FakeRepo(sources())
    collect(repo, FakeEnricher())
    collect(repo, FakeEnricher())
    count = len(repo.articles)

    report = collect(repo, FakeEnricher())

    assert report.new_articles == 0 and len(repo.articles) == count


def test_later_runs_do_not_import_the_feed_archive():
    repo = FakeRepo([source(1, LAB)])
    collect(repo, FakeEnricher())

    collect(repo, FakeEnricher())

    assert "https://lab.example.com/news/old-post" not in {a.normalized_url for a in repo.articles}


def test_extracted_page_text_or_feed_fallback_is_sent_to_the_llm():
    repo = FakeRepo(sources())
    enricher = FakeEnricher()

    collect(repo, enricher)

    texts = dict(enricher.calls)
    assert "Model X was trained on 15 trillion tokens" in texts["Introducing Model X"]
    assert texts["Agents SDK 2.0"].startswith("The Agents SDK reaches version 2.0")
    assert texts["Sparse Attention for Long-Context Summarization"].startswith("We propose")
    assert "Model X was trained" in repo.by_url(MODEL_X).content


def test_invalid_llm_output_marks_the_article_failed_and_retries_up_to_three_times():
    repo = FakeRepo([source(2, PRESS)])
    title = "EU & the AI Act: what changes in 2027"
    enricher = FakeEnricher({title: LLMInvalidOutputError("catégorie inconnue : 'sport'")})

    report = collect(repo, enricher)

    article = repo.by_url(AI_ACT)
    assert (article.status, article.attempts) == ("failed", 1)
    assert article.last_error == "catégorie inconnue : 'sport'"
    assert (report.summarized, report.failed) == (0, 1)

    collect(repo, enricher)
    collect(repo, enricher)
    assert article.attempts == 3

    enricher.calls.clear()
    report = collect(repo, enricher)
    assert enricher.calls == []
    assert article.attempts == 3 and report.failed == 0


def test_failed_article_succeeds_on_retry():
    repo = FakeRepo([source(2, PRESS)])
    title = "EU & the AI Act: what changes in 2027"
    collect(repo, FakeEnricher({title: LLMInvalidOutputError("JSON invalide")}))

    report = collect(repo, FakeEnricher())

    article = repo.by_url(AI_ACT)
    assert (article.status, article.attempts, article.last_error) == ("summarized", 2, None)
    assert report.summarized == 1


def test_article_without_usable_text_fails_without_calling_the_llm():
    repo = FakeRepo([source(1, LAB)])
    enricher = FakeEnricher()
    routes = {url: body for url, body in ROUTES.items() if url != SAFETY}

    report = collect(repo, enricher, routes=routes)

    # Safety report : page absente, flux trop court.
    safety = repo.by_url(SAFETY)
    assert safety.status == "failed"
    assert "aucun texte exploitable" in safety.last_error
    assert "Safety report" not in dict(enricher.calls)
    assert report.failed == 1


@pytest.mark.parametrize("failure", [503, "unreachable", b"<html><body>Not a feed</body></html>"])
def test_broken_source_is_reported_without_blocking_the_others(failure):
    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)

    routes = {**ROUTES, LAB: refuse if failure == "unreachable" else failure}
    repo = FakeRepo(sources())

    report = collect(repo, FakeEnricher(), routes=routes)

    assert [name for name, _ in report.sources_ko] == ["Source 1"]
    assert report.sources_ok == ["Source 2", "Source 3"]
    assert {a.normalized_url for a in repo.articles} == {AI_ACT, PAPER}
    assert report.summarized == 2
    assert any("Source 1" in line for line in report.lines(1.0))


def big_feed(count: int) -> bytes:
    items = "".join(
        f"<item><title>Paper {i}</title><link>https://big.example/p/{i}</link>"
        f"<pubDate>{format_datetime(datetime(2026, 10, 19, 11, 0, tzinfo=UTC))}</pubDate>"
        f"<description>{'Abstract text. ' * 20}</description></item>"
        for i in range(count)
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>Big</title>{items}' \
        f"</channel></rss>".encode()


def test_max_items_per_run_caps_new_articles():
    url = "https://big.example/feed.xml"
    repo = FakeRepo([source(1, url, type="arxiv", max_items=20)])

    report = collect(repo, FakeEnricher(), routes={url: big_feed(200)})

    assert report.new_articles == 20
    assert len(repo.articles) == 20

    report = collect(repo, FakeEnricher(), routes={url: big_feed(200)})
    assert report.new_articles == 20 and len(repo.articles) == 40


def test_llm_outage_aborts_without_losing_or_penalizing_articles():
    repo = FakeRepo(sources())
    outage = LLMUnavailableError("vLLM injoignable à http://vllm:8000/v1")
    enricher = FakeEnricher({"Introducing Model X": outage})

    report = collect(repo, enricher)

    assert report.aborted == "vLLM injoignable à http://vllm:8000/v1"
    assert len(repo.articles) == 5
    model_x = repo.by_url(MODEL_X)
    assert (model_x.status, model_x.attempts) == ("pending", 0)
    assert any(line.startswith("Interrompue") for line in report.lines(1.0))


def test_no_category_aborts_before_collecting():
    repo = FakeRepo(sources(), categories=[])

    report = collect(repo, FakeEnricher())

    assert report.aborted and "catégorie" in report.aborted
    assert repo.articles == []


def feed_with(links: list[str]) -> bytes:
    date = format_datetime(datetime(2026, 10, 19, 11, 0, tzinfo=UTC))
    items = "".join(
        f"<item><title>Post {i}</title><link>{link}</link><pubDate>{date}</pubDate>"
        f"<description>{'Feed text long enough to summarize. ' * 10}</description></item>"
        for i, link in enumerate(links)
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>{items}' \
        f"</channel></rss>".encode()


def test_malformed_entry_is_skipped_and_counted_without_stopping_the_run():
    url = "https://mixed.example/feed.xml"
    links = ["https://mixed.example/a", "http://host:abc/broken", "https://mixed.example/b"]
    repo = FakeRepo([source(1, url), source(2, PRESS)])

    report = collect(repo, FakeEnricher(), routes={**ROUTES, url: feed_with(links)})

    urls = {a.normalized_url for a in repo.articles}
    assert urls == {"https://mixed.example/a", "https://mixed.example/b", AI_ACT}
    assert report.sources_ok == ["Source 1", "Source 2"]
    assert report.skipped_entries == 1
    assert "Entrées ignorées (malformées) : 1" in report.lines(1.0)
    assert report.summarized == 3 and report.aborted is None


def test_entry_with_a_url_longer_than_the_column_is_skipped_and_counted():
    url = "https://long.example/feed.xml"
    too_long = "https://long.example/" + "a" * (URL_MAX_CHARS - len("https://long.example/") + 1)
    assert len(too_long) == URL_MAX_CHARS + 1
    # Raccourcie par la normalisation (utm_*), mais l'URL brute reste trop longue.
    raw_too_long = "https://long.example/b?utm_source=" + "x" * URL_MAX_CHARS
    links = ["https://long.example/a", too_long, raw_too_long, "https://long.example/c"]
    repo = FakeRepo([source(1, url), source(2, PRESS)])

    report = collect(repo, FakeEnricher(), routes={**ROUTES, url: feed_with(links)})

    urls = {a.normalized_url for a in repo.articles}
    assert urls == {"https://long.example/a", "https://long.example/c", AI_ACT}
    assert report.sources_ok == ["Source 1", "Source 2"] and report.sources_ko == []
    assert report.skipped_entries == 2
    assert (report.new_articles, report.summarized, report.aborted) == (3, 3, None)


def test_url_at_the_column_limit_is_kept():
    url = "https://long.example/feed.xml"
    at_limit = "https://long.example/" + "a" * (URL_MAX_CHARS - len("https://long.example/"))
    repo = FakeRepo([source(1, url)])

    report = collect(repo, FakeEnricher(), routes={url: feed_with([at_limit])})

    assert [a.url for a in repo.articles] == [at_limit]
    assert report.skipped_entries == 0


def test_articles_inserted_before_an_unexpected_source_error_are_counted():
    class FlakyRepo(FakeRepo):
        def insert_article(self, article):
            if article.normalized_url.endswith("/boom"):
                raise RuntimeError("insert crashed")
            return super().insert_article(article)

    url = "https://flaky.example/feed.xml"
    links = ["https://flaky.example/a", "https://flaky.example/b", "https://flaky.example/boom"]
    repo = FlakyRepo([source(1, url), source(2, PRESS)])

    report = collect(repo, FakeEnricher(), routes={**ROUTES, url: feed_with(links)})

    assert report.sources_ko == [("Source 1", "erreur inattendue : RuntimeError insert crashed")]
    assert len(repo.articles) == 3
    assert report.new_articles == 3


def test_unexpected_source_error_marks_only_that_source_ko():
    def explode(request):
        raise RuntimeError("parser crashed")

    repo = FakeRepo(sources())

    report = collect(repo, FakeEnricher(), routes={**ROUTES, LAB: explode})

    assert report.sources_ko == [("Source 1", "erreur inattendue : RuntimeError parser crashed")]
    assert report.sources_ok == ["Source 2", "Source 3"]
    assert report.summarized == 2 and report.aborted is None


def test_poisoned_article_is_marked_failed_and_later_articles_are_processed(monkeypatch):
    real_extract = extract.trafilatura.extract

    def poisoned(page, url, **kwargs):
        if "model-x" in url:
            raise TypeError("trafilatura exploded")
        return real_extract(page, url=url, **kwargs)

    monkeypatch.setattr(extract.trafilatura, "extract", poisoned)
    repo = FakeRepo(sources())
    title = "EU & the AI Act: what changes in 2027"
    enricher = FakeEnricher({title: KeyError("unexpected")})

    report = collect(repo, enricher)

    model_x, ai_act = repo.by_url(MODEL_X), repo.by_url(AI_ACT)
    assert (model_x.status, model_x.attempts) == ("failed", 1)
    assert model_x.last_error == "erreur inattendue : TypeError trafilatura exploded"
    assert (ai_act.status, ai_act.attempts) == ("failed", 1)
    assert ai_act.last_error.startswith("erreur inattendue : KeyError")
    assert (report.summarized, report.failed) == (3, 2)
    assert repo.by_url(PAPER).status == "summarized"


def test_database_error_during_processing_aborts_without_penalty():
    repo = FakeRepo(sources())
    enricher = FakeEnricher({"Introducing Model X": psycopg.OperationalError("db gone")})

    with pytest.raises(psycopg.OperationalError):
        collect(repo, enricher)

    assert (repo.by_url(MODEL_X).status, repo.by_url(MODEL_X).attempts) == ("pending", 0)


def test_concurrent_run_exits_without_doing_anything():
    repo = FakeRepo(sources())
    repo.locked_elsewhere = True
    enricher = FakeEnricher()

    report = collect(repo, enricher)

    assert report.already_running and report.aborted is None
    assert repo.articles == [] and enricher.calls == []


def test_main_reports_already_running_and_exits_zero(monkeypatch, capsys):
    repo = FakeRepo(sources())
    repo.locked_elsewhere = True
    repo.close = lambda: None
    monkeypatch.setattr(collect_module.Repository, "connect", classmethod(lambda cls, s: repo))

    assert collect_module.main() == 0
    assert "collecte déjà en cours" in capsys.readouterr().out
