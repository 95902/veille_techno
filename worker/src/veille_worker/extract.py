"""Texte d'un article : extraction trafilatura, repli sur le contenu du flux, troncature."""

import html
import re
from html.parser import HTMLParser

import httpx
import trafilatura

WHITESPACE = re.compile(r"[ \t\r\f\v]+")
BLANK_LINES = re.compile(r"\n\s*\n+")


class NoUsableTextError(RuntimeError):
    """Ni la page ni le flux ne fournissent de texte exploitable."""


class _TextCollector(HTMLParser):
    BLOCKS = {"p", "br", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "blockquote"}
    SKIPPED = {"script", "style"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skipping = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.SKIPPED:
            self.skipping += 1
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIPPED and self.skipping:
            self.skipping -= 1
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skipping:
            self.parts.append(data)


def html_to_text(fragment: str) -> str:
    """Texte brut d'un fragment HTML de flux (titre, résumé, contenu)."""
    if "<" not in fragment:
        return _clean(html.unescape(fragment))
    collector = _TextCollector()
    collector.feed(fragment)
    collector.close()
    return _clean("".join(collector.parts))


def _clean(text: str) -> str:
    lines = (WHITESPACE.sub(" ", line).strip() for line in text.split("\n"))
    return BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def extract_page_text(url: str, client: httpx.Client) -> str | None:
    """Texte principal de la page de l'article, ou None si la page est inaccessible."""
    try:
        response = client.get(url)
    except httpx.HTTPError:
        return None
    content_type = response.headers.get("content-type", "")
    if response.status_code >= 400 or ("html" not in content_type and content_type):
        return None
    text = trafilatura.extract(
        response.text, url=str(response.url), include_comments=False, include_tables=False
    )
    return _clean(text) if text else None


def article_text(
    *,
    url: str,
    source_type: str,
    feed_content: str | None,
    client: httpx.Client,
    min_extracted_chars: int,
    min_text_chars: int,
    max_chars: int,
) -> str:
    """Texte à résumer, tronqué à `max_chars`.

    arXiv : le résumé du flux suffit (la page est un PDF ou une notice). Ailleurs : la page
    extraite si elle est assez longue, sinon le plus long de la page et du contenu du flux.
    """
    feed_text = (feed_content or "").strip()
    if source_type == "arxiv":
        text = feed_text
    else:
        extracted = extract_page_text(url, client) or ""
        if len(extracted) >= min_extracted_chars:
            text = extracted
        else:
            text = max(extracted, feed_text, key=len)
    if len(text) < min_text_chars:
        raise NoUsableTextError(
            f"aucun texte exploitable ({len(text)} caractères, minimum {min_text_chars})"
        )
    return truncate(text, max_chars)


def truncate(text: str, max_chars: int) -> str:
    """Coupe au dernier espace avant `max_chars`, marque de coupure comprise."""
    if len(text) <= max_chars:
        return text
    marker = " […]"
    cut = text[: max_chars - len(marker)]
    space = cut.rfind(" ")
    return (cut[:space] if space > len(cut) // 2 else cut).rstrip() + marker
