"""Le worker n'émet que des SELECT, INSERT et UPDATE (rôle veille_worker sans DDL ni DELETE)."""

import ast
import re
from pathlib import Path

import veille_worker

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
