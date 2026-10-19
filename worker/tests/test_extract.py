import time

import httpx
import pytest
from conftest import PUBLIC_IP
from helpers import fixture, http_client

from veille_worker.extract import (
    NoUsableTextError,
    UnsafeFetchError,
    article_text,
    extract_page_text,
    fetch_html,
    html_to_text,
    is_public_ip,
    truncate,
)

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


# --- Téléchargement borné et anti-SSRF des pages tierces ---------------------------------

HTML = {"content-type": "text/html; charset=utf-8"}


def page(body: bytes = b"<html><body><p>ok</p></body></html>", **headers):
    return lambda request: httpx.Response(200, content=body, headers={**HTML, **headers})


def redirect(location: str):
    return lambda request: httpx.Response(302, headers={"location": location})


def refused(url, client):
    with pytest.raises(UnsafeFetchError) as info:
        fetch_html(url, client)
    return str(info.value)


def test_request_goes_to_the_validated_ip_with_host_and_sni_kept():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, content=b"<html></html>", headers=HTML)

    client = httpx.Client(transport=httpx.MockTransport(handler))

    fetch_html("https://news.example.com/a?b=1", client)

    request = seen[0]
    assert str(request.url) == f"https://{PUBLIC_IP}/a?b=1"
    assert request.headers["host"] == "news.example.com"
    assert request.extensions["sni_hostname"] == "news.example.com"


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.1.2.3", "172.18.0.4", "192.168.1.1", "169.254.169.254", "0.0.0.0",
     "224.0.0.1", "240.0.0.1", "100.64.0.1", "::1", "fe80::1", "fc00::1", "::ffff:10.0.0.1",
     "2002:0a00:0001::1"],
)
def test_non_public_addresses_are_refused(address):
    assert not is_public_ip(address)


def test_public_addresses_are_allowed():
    assert is_public_ip("93.184.215.14") and is_public_ip("2606:4700::1111")


def test_private_ip_literal_is_refused():
    assert "non publique" in refused("http://127.0.0.1:8000/v1/models", http_client({}))


def test_host_resolving_to_a_private_ip_is_refused(dns):
    # Un service Compose (vllm, postgres, app) résout en IP privée : refusé de la même façon.
    dns["vllm"] = ["172.18.0.5"]
    dns["mixed.example.com"] = ["93.184.215.14", "10.0.0.7"]
    client = http_client({"http://vllm:8000/v1/models": page()})

    assert "non publique" in refused("http://vllm:8000/v1/models", client)
    assert "non publique" in refused("http://mixed.example.com/", client)


def test_redirect_to_a_private_ip_is_refused(dns):
    dns["internal.example.com"] = ["192.168.0.10"]
    client = http_client({
        "https://news.example.com/a": redirect("http://internal.example.com/admin"),
        "http://internal.example.com/admin": page(),
    })

    assert "non publique" in refused("https://news.example.com/a", client)


def test_relative_redirects_are_followed():
    client = http_client({
        "https://news.example.com/a": redirect("/b"),
        "https://news.example.com/b": page(b"<html><body>final</body></html>"),
    })

    html_page, final = fetch_html("https://news.example.com/a", client)

    assert "final" in html_page and final == "https://news.example.com/b"


def test_more_than_five_redirects_are_refused():
    routes = {f"https://news.example.com/{i}": redirect(f"/{i + 1}") for i in range(6)}
    routes["https://news.example.com/6"] = page()

    assert "redirections" in refused("https://news.example.com/0", http_client(routes))

    routes = {f"https://news.example.com/{i}": redirect(f"/{i + 1}") for i in range(5)}
    routes["https://news.example.com/5"] = page()
    assert fetch_html("https://news.example.com/0", http_client(routes))[1].endswith("/5")


@pytest.mark.parametrize(
    "url", ["ftp://news.example.com/a", "file:///etc/passwd", "gopher://news.example.com/"]
)
def test_non_http_schemes_are_refused(url):
    assert "protocole" in refused(url, http_client({}))


def test_redirect_to_a_non_http_scheme_is_refused():
    client = http_client({"https://news.example.com/a": redirect("file:///etc/passwd")})

    assert "protocole" in refused("https://news.example.com/a", client)


def test_oversized_body_is_refused_while_streaming():
    big = b"<html><body>" + b"x" * 4_000_000 + b"</body></html>"
    client = http_client({"https://news.example.com/big": page(big)})

    assert "trop lourde" in refused("https://news.example.com/big", client)


def test_declared_oversized_body_is_refused_before_reading():
    def handler(request):
        def body():
            raise AssertionError("le corps ne doit pas être lu")
            yield b""

        return httpx.Response(
            200, content=body(), headers={**HTML, "content-length": "999999999"}
        )

    client = http_client({"https://news.example.com/big": handler})

    assert "trop lourde" in refused("https://news.example.com/big", client)


def test_wrong_content_type_is_skipped_before_reading_the_body():
    def pdf(request):
        def body():
            raise AssertionError("le corps ne doit pas être lu")
            yield b""

        return httpx.Response(200, content=body(), headers={"content-type": "application/pdf"})

    client = http_client({"https://news.example.com/paper": pdf})

    assert "content-type" in refused("https://news.example.com/paper", client)


def test_total_deadline_bounds_a_slow_body():
    def slow(request):
        def body():
            yield b"<html>"
            time.sleep(0.2)
            yield b"<body>late</body></html>"

        return httpx.Response(200, content=body(), headers=HTML)

    client = http_client({"https://news.example.com/slow": slow})

    with pytest.raises(UnsafeFetchError, match="délai"):
        fetch_html("https://news.example.com/slow", client, total_timeout=0.1)


@pytest.mark.parametrize(
    "url",
    [
        "http://xn--a.example.com/", "http://host:abc/", "http://exa mple.com/",
        "http://[::1/", "http://ex\u00e4\u200dmple..com/",
    ],
)
def test_invalid_urls_give_no_page_instead_of_crashing(url):
    assert extract_page_text(url, http_client({})) is None


def test_refused_page_falls_back_to_feed_content(dns):
    dns["lab.example.com"] = ["10.0.0.3"]

    text = article_text(
        url=PAGE, source_type="rss", feed_content=FEED_TEXT,
        client=http_client({PAGE: fixture("article.html")}), **LIMITS,
    )

    assert text == FEED_TEXT
