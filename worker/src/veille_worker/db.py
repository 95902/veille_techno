"""Accès base du worker (rôle veille_worker) : SQL brut paramétré, ni DDL ni DELETE.

Laravel possède le schéma (tables sources, categories, articles) ; ce module ne fait que
lire les sources et catégories, insérer et mettre à jour des articles.
"""

from dataclasses import dataclass
from datetime import datetime

import psycopg
from psycopg.rows import dict_row

from veille_worker.config import Settings

# Clé fixe du verrou consultatif de session qui sérialise les collectes (cron et manuelles).
COLLECT_LOCK_KEY = 7_265_100_001


def clean_text(value: str | None) -> str | None:
    """Texte sans caractère NUL : Postgres le refuse dans un champ text (psycopg.DataError).

    Toute valeur texte écrite par Repository passe par ici (flux, page extraite, sortie LLM).
    """
    return value.replace("\x00", "") if value is not None else None


class DatabaseUnavailableError(RuntimeError):
    """La base est injoignable ou refuse la connexion."""


@dataclass(frozen=True)
class Source:
    id: int
    name: str
    feed_url: str
    type: str
    max_items_per_run: int


@dataclass(frozen=True)
class Category:
    id: int
    name: str
    slug: str
    description: str | None


@dataclass(frozen=True)
class NewArticle:
    source_id: int
    url: str
    normalized_url: str
    title: str
    content: str | None
    published_at: datetime | None


@dataclass(frozen=True)
class ArticleToProcess:
    id: int
    url: str
    title: str
    content: str | None
    source_type: str
    attempts: int


class Repository:
    def __init__(self, conn: psycopg.Connection) -> None:
        self.conn = conn

    @classmethod
    def connect(cls, settings: Settings) -> "Repository":
        try:
            conn = psycopg.connect(
                host=settings.db_host,
                port=settings.db_port,
                dbname=settings.db_name,
                user=settings.db_user,
                password=settings.db_password,
                connect_timeout=10,
                autocommit=True,
                row_factory=dict_row,
            )
        except psycopg.Error as exc:
            raise DatabaseUnavailableError(
                f"base injoignable ({settings.db_user}@{settings.db_host}:{settings.db_port}"
                f"/{settings.db_name}) : {exc}"
            ) from exc
        return cls(conn)

    def close(self) -> None:
        self.conn.close()

    def try_lock(self) -> bool:
        """Prend le verrou de collecte pour la session ; False si une autre collecte le tient.

        Verrou de session : libéré à la fermeture de la connexion (fin du processus compris).
        """
        row = self.conn.execute(
            "SELECT pg_try_advisory_lock(%s) AS locked", (COLLECT_LOCK_KEY,)
        ).fetchone()
        return bool(row and row["locked"])

    def active_sources(self) -> list[Source]:
        rows = self.conn.execute(
            "SELECT id, name, feed_url, type, max_items_per_run FROM sources"
            " WHERE active ORDER BY id"
        ).fetchall()
        return [Source(**row) for row in rows]

    def categories(self) -> list[Category]:
        rows = self.conn.execute(
            "SELECT id, name, slug, description FROM categories ORDER BY id"
        ).fetchall()
        return [Category(**row) for row in rows]

    def has_articles(self, source_id: int) -> bool:
        row = self.conn.execute(
            "SELECT EXISTS (SELECT 1 FROM articles WHERE source_id = %s) AS found", (source_id,)
        ).fetchone()
        return bool(row and row["found"])

    def known_urls(self, normalized_urls: list[str]) -> set[str]:
        if not normalized_urls:
            return set()
        rows = self.conn.execute(
            "SELECT normalized_url FROM articles WHERE normalized_url = ANY(%s)",
            (normalized_urls,),
        ).fetchall()
        return {row["normalized_url"] for row in rows}

    def insert_article(self, article: NewArticle) -> bool:
        """Insère un article pending ; renvoie False si l'URL normalisée existe déjà."""
        cur = self.conn.execute(
            "INSERT INTO articles (source_id, url, normalized_url, title, content, published_at,"
            " status, attempts, created_at, updated_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, 'pending', 0, now(), now())"
            " ON CONFLICT (normalized_url) DO NOTHING",
            (
                article.source_id,
                clean_text(article.url),
                clean_text(article.normalized_url),
                clean_text(article.title),
                clean_text(article.content),
                article.published_at,
            ),
        )
        return cur.rowcount == 1

    def articles_to_process(self, max_attempts: int) -> list[ArticleToProcess]:
        rows = self.conn.execute(
            "SELECT a.id, a.url, a.title, a.content, s.type AS source_type, a.attempts"
            " FROM articles a JOIN sources s ON s.id = a.source_id"
            " WHERE a.status = 'pending' OR (a.status = 'failed' AND a.attempts < %s)"
            " ORDER BY a.published_at DESC NULLS LAST, a.id",
            (max_attempts,),
        ).fetchall()
        return [ArticleToProcess(**row) for row in rows]

    def mark_summarized(
        self,
        article_id: int,
        *,
        title_fr: str,
        summary: str,
        category_id: int,
        content: str,
    ) -> None:
        self.conn.execute(
            "UPDATE articles SET status = 'summarized', title_fr = %s, summary = %s,"
            " category_id = %s, content = %s, attempts = attempts + 1, last_error = NULL,"
            " updated_at = now() WHERE id = %s",
            (
                clean_text(title_fr),
                clean_text(summary),
                category_id,
                clean_text(content),
                article_id,
            ),
        )

    def mark_failed(self, article_id: int, error: str, content: str | None = None) -> None:
        self.conn.execute(
            "UPDATE articles SET status = 'failed', attempts = attempts + 1, last_error = %s,"
            " content = COALESCE(%s, content), updated_at = now() WHERE id = %s",
            ((clean_text(error) or "")[:2000], clean_text(content), article_id),
        )
