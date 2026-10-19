"""SQL de Repository contre le Postgres de Compose, en tant que veille_worker (marqueur `db`).

Opt-in : ignorés sans WORKER_DB_PASSWORD dans l'environnement ou si la base est injoignable.
Chaque test tourne dans une transaction annulée à la fin : aucune ligne ne reste en base
(veille_worker n'a pas le droit de DELETE). Seule la séquence articles_id_seq avance.
"""

import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import psycopg
import pytest
from helpers import http_client
from psycopg.rows import dict_row

from veille_worker.collect import Report, collect_source
from veille_worker.config import Settings
from veille_worker.db import (
    URL_MAX_BYTES,
    ArticleToProcess,
    Category,
    NewArticle,
    Repository,
    Source,
    url_fits,
)

pytestmark = pytest.mark.db


def connect() -> psycopg.Connection:
    if "WORKER_DB_PASSWORD" not in os.environ:
        pytest.skip("WORKER_DB_PASSWORD absent : tests db désactivés")
    settings = Settings.from_env()
    try:
        return psycopg.connect(
            host=settings.db_host,
            port=settings.db_port,
            dbname=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            connect_timeout=3,
            row_factory=dict_row,
        )
    except psycopg.OperationalError as exc:
        pytest.skip(f"base injoignable : {exc}")


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture
def repo(conn) -> Repository:
    # Connexion sans autocommit : tout le test tient dans une transaction annulée.
    return Repository(conn)


@pytest.fixture
def a_source(repo) -> Source:
    sources = repo.active_sources()
    if not sources:
        pytest.skip("aucune source active (lancer les seeders Laravel)")
    return sources[0]


def new_article(source: Source, **overrides) -> NewArticle:
    url = f"https://pytest.invalid/{uuid.uuid4()}"
    fields = dict(
        source_id=source.id, url=url, normalized_url=url, title="Test db",
        content="Contenu de test.", published_at=datetime(2999, 1, 1, tzinfo=UTC),
    )
    return NewArticle(**{**fields, **overrides})


def row(conn, normalized_url: str) -> dict:
    return conn.execute(
        "SELECT * FROM articles WHERE normalized_url = %s", (normalized_url,)
    ).fetchone()


def test_sources_and_categories_map_to_dataclasses(repo):
    assert all(isinstance(s, Source) for s in repo.active_sources())
    assert all(isinstance(c, Category) for c in repo.categories())


def test_insert_is_idempotent_and_urls_are_found_with_any(repo, a_source):
    article = new_article(a_source)

    assert repo.insert_article(article) is True
    assert repo.insert_article(article) is False
    assert repo.known_urls([article.normalized_url, "https://pytest.invalid/absent"]) == {
        article.normalized_url
    }
    assert repo.known_urls([]) == set()
    assert repo.has_articles(a_source.id) is True


def test_pending_then_failed_articles_follow_the_attempt_cap(conn, repo, a_source):
    article = new_article(a_source)
    repo.insert_article(article)
    article_id = row(conn, article.normalized_url)["id"]

    pending = {a.id: a for a in repo.articles_to_process(max_attempts=3)}
    assert isinstance(pending[article_id], ArticleToProcess)
    assert pending[article_id].source_type == a_source.type
    # Daté de l'an 2999 : en tête du tri par date décroissante.
    assert repo.articles_to_process(max_attempts=3)[0].id == article_id

    repo.mark_failed(article_id, "erreur " * 500)
    stored = row(conn, article.normalized_url)
    assert (stored["status"], stored["attempts"]) == ("failed", 1)
    assert len(stored["last_error"]) == 2000 and stored["content"] == "Contenu de test."
    assert article_id in {a.id for a in repo.articles_to_process(max_attempts=2)}
    assert article_id not in {a.id for a in repo.articles_to_process(max_attempts=1)}


def test_mark_summarized_stores_the_enrichment(conn, repo, a_source):
    article = new_article(a_source)
    repo.insert_article(article)
    article_id = row(conn, article.normalized_url)["id"]
    category = repo.categories()[0]
    repo.mark_failed(article_id, "premier essai")

    repo.mark_summarized(
        article_id, title_fr="Titre", summary="Une.\nDeux.\nTrois.",
        category_id=category.id, content="Texte extrait.",
    )

    stored = row(conn, article.normalized_url)
    assert stored["status"] == "summarized" and stored["attempts"] == 2
    assert stored["last_error"] is None and stored["category_id"] == category.id
    assert (stored["title_fr"], stored["content"]) == ("Titre", "Texte extrait.")
    assert article_id not in {a.id for a in repo.articles_to_process(max_attempts=3)}


def test_nul_characters_in_texts_never_reach_postgres(conn, repo, a_source):
    article = new_article(a_source, title="Ti\x00tre", content="Con\x00tenu")

    assert repo.insert_article(article) is True
    stored = row(conn, article.normalized_url)
    assert (stored["title"], stored["content"]) == ("Titre", "Contenu")

    repo.mark_failed(stored["id"], "er\x00reur", content="Pa\x00ge")
    repo.mark_summarized(
        stored["id"], title_fr="T\x00", summary="U\x00ne.", category_id=repo.categories()[0].id,
        content="Te\x00xte",
    )
    stored = row(conn, article.normalized_url)
    assert (stored["title_fr"], stored["summary"], stored["content"]) == ("T", "Une.", "Texte")


def padded_url(length: int) -> str:
    prefix = f"https://pytest.invalid/{uuid.uuid4()}/"
    return prefix + "a" * (length - len(prefix))


def test_url_limit_matches_the_articles_columns(conn, repo, a_source):
    at_limit = padded_url(URL_MAX_BYTES)
    assert repo.insert_article(new_article(a_source, url=at_limit, normalized_url=at_limit))

    for column in ("url", "normalized_url"):
        too_long = padded_url(URL_MAX_BYTES + 1)
        article = new_article(a_source, **{column: too_long})
        with pytest.raises(psycopg.errors.StringDataRightTruncation), conn.transaction():
            repo.insert_article(article)


def test_url_limit_is_measured_in_bytes_for_non_ascii_urls(conn, repo, a_source):
    # 1955 caractères CJK distincts = 5888 octets : sous 2048 caractères, mais au-delà de l'index
    # (2704 o). Des caractères variés évitent que Postgres compresse la clé d'index.
    cjk = "https://pytest.invalid/" + "".join(chr(0x4E00 + i) for i in range(1955))
    assert len(cjk) < URL_MAX_BYTES
    assert not url_fits(cjk)
    with pytest.raises(psycopg.errors.ProgramLimitExceeded), conn.transaction():
        repo.insert_article(new_article(a_source, url=cjk, normalized_url=cjk))

    fits = "https://pytest.invalid/" + "".join(chr(0x4E00 + i) for i in range(600))  # ~1823 o
    assert url_fits(fits)
    assert repo.insert_article(new_article(a_source, url=fits, normalized_url=fits))


def test_collect_skips_over_long_urls_and_keeps_long_titles(conn, repo, a_source):
    feed_url = f"https://pytest.invalid/{uuid.uuid4()}/feed.xml"
    kept, too_long = padded_url(200), padded_url(URL_MAX_BYTES + 1)
    long_title = "Titre très long " * 5000  # colonne text : aucune troncature nécessaire
    date = "Mon, 19 Oct 2026 11:00:00 GMT"
    items = "".join(
        f"<item><title>{title}</title><link>{link}</link><pubDate>{date}</pubDate>"
        f"<description>Texte du flux.</description></item>"
        for title, link in ((long_title, kept), ("Trop long", too_long))
    )
    feed = f'<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>{items}' \
        "</channel></rss>"
    source = Source(a_source.id, "pytest", feed_url, "rss", max_items_per_run=20)
    report = Report()

    collect_source(
        repo, http_client({feed_url: feed.encode()}), Settings(),
        datetime(2026, 10, 19, 12, 0, tzinfo=UTC), report, source,
    )

    assert report.sources_ok == ["pytest"] and report.skipped_entries == 1
    assert report.new_articles == 1
    assert row(conn, kept)["title"] == long_title.strip()
    assert repo.known_urls([too_long]) == set()


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM articles WHERE false",
        "CREATE TABLE pytest_forbidden (id int)",
        "SELECT count(*) FROM users",
        "UPDATE sources SET active = active WHERE false",
    ],
)
def test_worker_role_cannot_delete_create_or_touch_other_tables(conn, sql):
    with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
        conn.execute(sql)


def test_collect_lock_is_exclusive_across_sessions():
    first, second = Repository(connect()), Repository(connect())
    try:
        assert first.try_lock() is True
        assert second.try_lock() is False
        first.close()  # fin de session : verrou libéré
        assert second.try_lock() is True
    finally:
        for repo in (first, second):
            if not repo.conn.closed:
                repo.conn.rollback()
                repo.conn.close()
