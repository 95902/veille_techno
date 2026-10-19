from datetime import UTC, datetime

import httpx
import pytest
from helpers import NOW, fixture, http_client

from veille_worker.feeds import FeedError, fetch_feed, recent_entries

RSS = "https://lab.example.com/feed.xml"


def test_rss_entries_are_parsed_and_sorted_newest_first():
    entries = fetch_feed(RSS, http_client({RSS: fixture("lab_blog.rss.xml")}))

    assert [e.title for e in entries][:3] == [
        "Introducing Model X",
        "Model X, again (same article, other tracking)",
        "Agents SDK 2.0",
    ]
    assert entries[-1].title == "Undated post" and entries[-1].published_at is None
    assert entries[0].published_at == datetime(2026, 10, 18, 10, 0, tzinfo=UTC)
    assert entries[0].content == "Model X is our new open-weight model."


def test_first_run_keeps_only_the_last_seven_days():
    entries = fetch_feed(RSS, http_client({RSS: fixture("lab_blog.rss.xml")}))

    recent = recent_entries(entries, first_run=True, days=7, now=NOW)

    assert [e.url.split("/")[-1].split("?")[0] for e in recent] == [
        "model-x", "model-x", "agents-sdk", "safety-report",
    ]


def test_later_runs_keep_undated_entries_but_not_the_feed_archive():
    entries = fetch_feed(RSS, http_client({RSS: fixture("lab_blog.rss.xml")}))

    later = recent_entries(entries, first_run=False, days=7, now=NOW)

    titles = [e.title for e in later]
    assert "Undated post" in titles
    assert "An old post" not in titles
    assert len(later) == 5


def test_atom_full_content_is_preferred_and_html_stripped():
    url = "https://press.example.org/ai/feed"
    [entry] = fetch_feed(url, http_client({url: fixture("press.atom.xml")}))

    assert entry.title == "EU & the AI Act: what changes in 2027"
    assert entry.url == "https://press.example.org/2026/10/ai-act-2027"
    assert entry.content == (
        "The European Union confirmed the timeline of the AI Act.\n\n"
        "General-purpose models must publish a summary of their training data.\n\n"
        "Providers of high-risk systems get one more year to comply, and fines can reach "
        "7 percent of global turnover."
    )
    assert entry.published_at == datetime(2026, 10, 19, 6, 0, tzinfo=UTC)


def test_arxiv_abstract_loses_its_announce_prefix():
    url = "https://export.arxiv.org/rss/cs.CL"
    [entry] = fetch_feed(url, http_client({url: fixture("arxiv.rss.xml")}))

    assert entry.content.startswith("We propose a sparse attention mechanism")
    assert entry.url == "https://arxiv.org/abs/2610.11111"


def test_http_error_raises_feed_error():
    with pytest.raises(FeedError, match="HTTP 503"):
        fetch_feed(RSS, http_client({RSS: 503}))


def test_unreachable_feed_raises_feed_error():
    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(FeedError, match="injoignable"):
        fetch_feed(RSS, http_client({RSS: refuse}))


def test_html_page_is_not_a_feed():
    with pytest.raises(FeedError, match="invalide"):
        fetch_feed(RSS, http_client({RSS: fixture("article.html")}))
