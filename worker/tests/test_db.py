"""Le worker n'émet que des SELECT, INSERT et UPDATE (rôle veille_worker sans DDL ni DELETE)."""

import ast
import re
from pathlib import Path
from types import SimpleNamespace

import veille_worker
from veille_worker.db import NewArticle, Repository, clean_text

PACKAGE = Path(veille_worker.__file__).parent
FORBIDDEN = re.compile(
    r"\b(CREATE|ALTER|DROP|TRUNCATE|DELETE|GRANT|REVOKE|COMMENT)\b", re.IGNORECASE
)


def execute_calls(path: Path) -> list[ast.Call]:
    tree = ast.parse(path.read_text())
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"execute", "executemany"}
    ]


def test_only_db_module_runs_sql():
    others = [p.name for p in PACKAGE.glob("*.py") if p.name != "db.py" and execute_calls(p)]

    assert others == []


def test_every_statement_is_a_literal_select_insert_or_update():
    statements = []
    for call in execute_calls(PACKAGE / "db.py"):
        sql = call.args[0]
        # Requêtes littérales uniquement : aucune concaténation de valeurs dans le SQL.
        assert isinstance(sql, ast.Constant) and isinstance(sql.value, str)
        statements.append(sql.value)

    assert len(statements) >= 7
    for sql in statements:
        assert sql.lstrip().split()[0].upper() in {"SELECT", "INSERT", "UPDATE"}, sql
        assert not FORBIDDEN.search(sql), sql


def test_article_insert_ignores_duplicates():
    assert "ON CONFLICT (normalized_url) DO NOTHING" in (PACKAGE / "db.py").read_text()


class RecordingConn:
    """Connexion factice : garde les paramètres envoyés à execute."""

    def __init__(self) -> None:
        self.params: list[tuple] = []

    def execute(self, sql, params=()):
        self.params.append(params)
        return SimpleNamespace(rowcount=1)


def test_nul_characters_are_stripped_from_every_written_text():
    conn = RecordingConn()
    repo = Repository(conn)

    repo.insert_article(NewArticle(
        source_id=1, url="https://a.example/\x00x", normalized_url="https://a.example/\x00x",
        title="Ti\x00tle", content="Con\x00tent", published_at=None,
    ))
    repo.mark_summarized(7, title_fr="Ti\x00tre", summary="Un\x00e.", category_id=2,
                         content="Te\x00xte")
    repo.mark_failed(7, "er\x00reur", content="Pa\x00ge")
    repo.mark_failed(7, "x" * 1999 + "\x00" + "yz")

    texts = [value for params in conn.params for value in params if isinstance(value, str)]
    assert texts and not any("\x00" in value for value in texts)
    assert conn.params[0][1:5] == (
        "https://a.example/x", "https://a.example/x", "Title", "Content"
    )
    assert conn.params[1][:4] == ("Titre", "Une.", 2, "Texte")
    assert conn.params[2][:2] == ("erreur", "Page")
    assert conn.params[3][0] == "x" * 1999 + "y" and conn.params[3][1] is None


def test_clean_text_keeps_none():
    assert clean_text(None) is None and clean_text("a\x00b") == "ab"
