"""Outils de test partagés : fixtures figées, transport HTTP simulé, dépôt en mémoire."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg

from veille_worker.db import URL_MAX_CHARS, ArticleToProcess, Category, NewArticle, Source

FIXTURES = Path(__file__).parent / "fixtures"

# Date figée des tests : les fixtures datent du 9 au 19 octobre 2026.
NOW = datetime(2026, 10, 19, 12, 0, tzinfo=UTC)

CATEGORIES = [
    Category(1, "Modèles", "modeles", "Sorties de modèles"),
    Category(2, "Outils dev", "outils-dev", "Outils pour développeurs"),
    Category(3, "Réglementation", "reglementation", "Lois et régulation"),
    Category(4, "Autre", "autre", None),
]


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


Route = bytes | int | Callable[[httpx.Request], httpx.Response]


def http_client(routes: dict[str, Route]) -> httpx.Client:
    """Client httpx servi par `routes` (URL → contenu, code HTTP ou fonction) ; sinon 404."""

    def handler(request: httpx.Request) -> httpx.Response:
        # Le fragment n'est jamais envoyé au serveur. Les pages d'articles partent vers l'IP
        # validée : l'URL demandée se reconstruit avec l'en-tête Host.
        url = request.url.copy_with(fragment=None)
        host = request.headers.get("host", "")
        if host:
            url = httpx.URL(f"{url.scheme}://{host}{url.raw_path.decode('ascii')}")
        route = routes.get(str(url))
        if route is None:
            return httpx.Response(404, text="not found")
        if callable(route):
            return route(request)
        if isinstance(route, int):
            return httpx.Response(route, text="error")
        content_type = "text/html; charset=utf-8" if route.lstrip().startswith(
            (b"<!DOCTYPE html", b"<html")
        ) else "application/xml"
        return httpx.Response(200, content=route, headers={"content-type": content_type})

    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)


@dataclass
class StoredArticle:
    id: int
    source_id: int
    url: str
    normalized_url: str
    title: str
    content: str | None
    published_at: datetime | None
    status: str = "pending"
    attempts: int = 0
    title_fr: str | None = None
    summary: str | None = None
    category_id: int | None = None
    last_error: str | None = None


class FakeRepo:
    """Dépôt en mémoire reproduisant la sémantique des requêtes de veille_worker.db."""

    def __init__(self, sources: list[Source], categories: list[Category] = CATEGORIES) -> None:
        self.sources = sources
        self._categories = categories
        self.articles: list[StoredArticle] = []
        self.locked_elsewhere = False

    def try_lock(self) -> bool:
        return not self.locked_elsewhere

    def active_sources(self) -> list[Source]:
        return list(self.sources)

    def categories(self) -> list[Category]:
        return list(self._categories)

    def has_articles(self, source_id: int) -> bool:
        return any(a.source_id == source_id for a in self.articles)

    def known_urls(self, normalized_urls: list[str]) -> set[str]:
        return {a.normalized_url for a in self.articles} & set(normalized_urls)

    def insert_article(self, article: NewArticle) -> bool:
        if max(len(article.url), len(article.normalized_url)) > URL_MAX_CHARS:
            # Comme Postgres sur un varchar(2048) : l'erreur interromprait la collecte.
            raise psycopg.errors.StringDataRightTruncation("value too long for varchar(2048)")
        if article.normalized_url in {a.normalized_url for a in self.articles}:
            return False
        self.articles.append(StoredArticle(id=len(self.articles) + 1, **vars(article)))
        return True

    def articles_to_process(self, max_attempts: int) -> list[ArticleToProcess]:
        types = {s.id: s.type for s in self.sources}
        return [
            ArticleToProcess(a.id, a.url, a.title, a.content, types[a.source_id], a.attempts)
            for a in self.articles
            if a.status == "pending" or (a.status == "failed" and a.attempts < max_attempts)
        ]

    def _get(self, article_id: int) -> StoredArticle:
        return next(a for a in self.articles if a.id == article_id)

    def mark_summarized(self, article_id, *, title_fr, summary, category_id, content) -> None:
        a = self._get(article_id)
        a.status, a.title_fr, a.summary = "summarized", title_fr, summary
        a.category_id, a.content = category_id, content
        a.attempts, a.last_error = a.attempts + 1, None

    def mark_failed(self, article_id, error, content=None) -> None:
        a = self._get(article_id)
        a.status, a.attempts, a.last_error = "failed", a.attempts + 1, error
        a.content = content if content is not None else a.content

    def by_url(self, normalized_url: str) -> StoredArticle:
        return next(a for a in self.articles if a.normalized_url == normalized_url)


def source(id: int, url: str, type: str = "rss", max_items: int = 20) -> Source:
    return Source(id=id, name=f"Source {id}", feed_url=url, type=type, max_items_per_run=max_items)


