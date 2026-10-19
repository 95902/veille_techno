"""Lecture des flux RSS/Atom : entrées récentes, triées, au format du worker."""

import calendar
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import feedparser
import httpx

from veille_worker.extract import html_to_text

ARXIV_PREFIX = re.compile(r"^arXiv:\S+\s+Announce Type:\s*\S+\s*(Abstract:\s*)?", re.IGNORECASE)


class FeedError(RuntimeError):
    """Flux injoignable, en erreur HTTP ou illisible."""


@dataclass(frozen=True)
class FeedEntry:
    url: str
    title: str
    content: str | None
    published_at: datetime | None


def fetch_feed(url: str, client: httpx.Client) -> list[FeedEntry]:
    """Télécharge et analyse un flux ; entrées triées de la plus récente à la plus ancienne."""
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        raise FeedError(f"flux injoignable : {exc.__class__.__name__} {exc}") from exc
    if response.status_code >= 400:
        raise FeedError(f"flux en erreur HTTP {response.status_code}")

    parsed = feedparser.parse(response.content)
    if parsed.bozo and not parsed.entries:
        raise FeedError(f"flux invalide : {parsed.get('bozo_exception')}")
    if not parsed.get("version") and not parsed.entries:
        raise FeedError("flux invalide : ni RSS ni Atom")

    entries = [entry for raw in parsed.entries if (entry := _to_entry(raw)) is not None]
    undated = datetime.min.replace(tzinfo=UTC)
    return sorted(entries, key=lambda e: e.published_at or undated, reverse=True)


# Passages suivants : entrées non datées admises au plus par ce nombre par source et par
# passage (les premières du flux), sinon un flux sans dates à longue archive serait importé
# par tranches de `max_items_per_run` chaque jour.
MAX_UNDATED_PER_RUN = 3


def recent_entries(
    entries: list[FeedEntry],
    *,
    first_run: bool,
    days: int,
    now: datetime,
    max_undated: int = MAX_UNDATED_PER_RUN,
) -> list[FeedEntry]:
    """Entrées des `days` derniers jours.

    Premier passage d'une source : seulement des entrées datées de la fenêtre. Passages
    suivants : s'y ajoutent les `max_undated` premières entrées non datées du flux (ordre du
    flux, avant dédoublonnage : déjà connues, elles ne laissent pas passer l'archive). Les
    entrées datées d'avant la fenêtre restent ignorées, sinon chaque passage importerait
    l'archive du flux (OpenAI en publie plus de 1 000) par tranches de `max_items_per_run`.
    """
    cutoff = now - timedelta(days=days)
    kept: list[FeedEntry] = []
    undated = 0
    for e in entries:
        if e.published_at is not None:
            if e.published_at >= cutoff:
                kept.append(e)
        elif not first_run and undated < max_undated:
            undated += 1
            kept.append(e)
    return kept


def _to_entry(raw: Any) -> FeedEntry | None:
    url = (raw.get("link") or "").strip()
    if not url.startswith(("http://", "https://")):
        return None
    title = html_to_text(raw.get("title") or "") or url
    return FeedEntry(
        url=url,
        title=title,
        content=_content(raw),
        published_at=_date(raw),
    )


def _content(raw: Any) -> str | None:
    """Contenu complet (Atom content) s'il existe, sinon le résumé ; texte brut."""
    candidates = [part.get("value", "") for part in raw.get("content") or []]
    candidates.append(raw.get("summary") or "")
    text = max((html_to_text(c) for c in candidates), key=len, default="")
    text = ARXIV_PREFIX.sub("", text).strip()
    return text or None


def _date(raw: Any) -> datetime | None:
    # feedparser normalise les dates en struct_time UTC.
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        value = raw.get(key)
        if value:
            return datetime.fromtimestamp(calendar.timegm(value), tz=UTC)
    return None
