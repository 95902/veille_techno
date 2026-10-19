"""Collecte quotidienne : flux → nouveaux articles → extraction → vLLM → base.

Usage : python -m veille_worker.collect

Code de sortie : 0 si la collecte a tourné (même avec des sources ou articles en échec),
1 si la base ou vLLM sont indisponibles (les articles restent en base pour la prochaine passe).
"""

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

import httpx
import psycopg

from veille_worker.config import USER_AGENT, Settings
from veille_worker.db import (
    ArticleToProcess,
    Category,
    DatabaseUnavailableError,
    NewArticle,
    Repository,
    Source,
)
from veille_worker.extract import NoUsableTextError, article_text
from veille_worker.feeds import FeedError, fetch_feed, recent_entries
from veille_worker.llm import (
    Enrichment,
    LLMInvalidOutputError,
    LLMUnavailableError,
    enrich_fr,
    make_client,
)
from veille_worker.urls import normalize_url

Enricher = Callable[[str, str, list[Category]], Enrichment]


class Repo(Protocol):
    def active_sources(self) -> list[Source]: ...
    def categories(self) -> list[Category]: ...
    def has_articles(self, source_id: int) -> bool: ...
    def known_urls(self, normalized_urls: list[str]) -> set[str]: ...
    def insert_article(self, article: NewArticle) -> bool: ...
    def articles_to_process(self, max_attempts: int) -> list[ArticleToProcess]: ...
    def mark_summarized(
        self, article_id: int, *, title_fr: str, summary: str, category_id: int, content: str
    ) -> None: ...
    def mark_failed(self, article_id: int, error: str, content: str | None = None) -> None: ...


@dataclass
class Report:
    sources_ok: list[str] = field(default_factory=list)
    sources_ko: list[tuple[str, str]] = field(default_factory=list)
    new_articles: int = 0
    summarized: int = 0
    failed: int = 0
    aborted: str | None = None

    def lines(self, duration: float) -> list[str]:
        out = [
            "=== Bilan de la collecte ===",
            f"Sources : {len(self.sources_ok)} OK, {len(self.sources_ko)} en erreur",
        ]
        out += [f"  ✗ {name} : {error}" for name, error in self.sources_ko]
        out += [
            f"Nouveaux articles : {self.new_articles}",
            f"Résumés : {self.summarized}",
            f"Échecs : {self.failed}",
            f"Durée : {duration:.0f} s",
        ]
        if self.aborted:
            out.append(f"Interrompue : {self.aborted}")
        return out


def log(message: str) -> None:
    print(message, flush=True)


def collect_sources(
    repo: Repo, client: httpx.Client, settings: Settings, now: datetime, report: Report
) -> None:
    """Insère les nouvelles entrées de chaque source active ; une source en erreur est notée."""
    for source in repo.active_sources():
        try:
            entries = fetch_feed(source.feed_url, client)
        except FeedError as exc:
            report.sources_ko.append((source.name, str(exc)))
            log(f"[source] {source.name} : ERREUR {exc}")
            continue

        first_run = not repo.has_articles(source.id)
        entries = recent_entries(
            entries, first_run=first_run, days=settings.first_run_days, now=now
        )
        by_url = {}
        for entry in entries:
            by_url.setdefault(normalize_url(entry.url), entry)
        known = repo.known_urls(list(by_url))

        inserted = 0
        for normalized, entry in by_url.items():
            if inserted >= source.max_items_per_run:
                break
            if normalized in known:
                continue
            if repo.insert_article(
                NewArticle(
                    source_id=source.id,
                    url=entry.url,
                    normalized_url=normalized,
                    title=entry.title,
                    content=entry.content,
                    published_at=entry.published_at,
                )
            ):
                inserted += 1

        report.sources_ok.append(source.name)
        report.new_articles += inserted
        scope = "premier passage" if first_run else "suivi"
        scope += f", {settings.first_run_days} derniers jours"
        log(f"[source] {source.name} : {len(entries)} entrées ({scope}), {inserted} nouvelles")


def process_articles(
    repo: Repo,
    client: httpx.Client,
    settings: Settings,
    categories: list[Category],
    enrich: Enricher,
    report: Report,
) -> None:
    """Résume les articles pending et les failed sous le plafond d'essais.

    LLMUnavailableError remonte : l'article courant n'est pas compté comme un essai.
    """
    category_ids = {c.slug: c.id for c in categories}
    articles = repo.articles_to_process(settings.max_attempts)
    log(f"[llm] {len(articles)} article(s) à résumer")
    for index, article in enumerate(articles, start=1):
        text: str | None = None
        try:
            text = article_text(
                url=article.url,
                source_type=article.source_type,
                feed_content=article.content,
                client=client,
                min_extracted_chars=settings.min_extracted_chars,
                min_text_chars=settings.min_text_chars,
                max_chars=settings.max_input_chars,
            )
            result = enrich(text, article.title, categories)
        except (NoUsableTextError, LLMInvalidOutputError) as exc:
            repo.mark_failed(article.id, str(exc), content=text)
            report.failed += 1
            log(f"[llm] {index}/{len(articles)} #{article.id} ÉCHEC : {exc}")
            continue

        repo.mark_summarized(
            article.id,
            title_fr=result.title_fr,
            summary="\n".join(result.summary),
            category_id=category_ids[result.category],
            content=text,
        )
        report.summarized += 1
        log(f"[llm] {index}/{len(articles)} #{article.id} [{result.category}] {result.title_fr}")


def run(
    repo: Repo,
    client: httpx.Client,
    settings: Settings,
    enrich: Enricher,
    now: datetime | None = None,
) -> Report:
    report = Report()
    categories = repo.categories()
    if not categories:
        report.aborted = "aucune catégorie en base (lancer les seeders Laravel)"
        return report
    collect_sources(repo, client, settings, now or datetime.now(UTC), report)
    try:
        process_articles(repo, client, settings, categories, enrich, report)
    except LLMUnavailableError as exc:
        report.aborted = str(exc)
    return report


def make_http_client(settings: Settings) -> httpx.Client:
    return httpx.Client(
        timeout=settings.http_timeout,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
    )


def main() -> int:
    started = time.monotonic()
    settings = Settings.from_env()
    try:
        repo = Repository.connect(settings)
    except DatabaseUnavailableError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    llm_client = make_client(settings)

    def enrich(text: str, title: str, categories: list[Category]) -> Enrichment:
        return enrich_fr(text, title, categories, settings=settings, client=llm_client)

    try:
        with make_http_client(settings) as client:
            report = run(repo, client, settings, enrich)
    except psycopg.Error as exc:
        print(f"Erreur : base indisponible en cours de collecte : {exc}", file=sys.stderr)
        return 1
    finally:
        repo.close()

    for line in report.lines(time.monotonic() - started):
        log(line)
    if report.aborted:
        print(f"Erreur : {report.aborted}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
