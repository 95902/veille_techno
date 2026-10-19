"""Fixtures communes : résolution DNS simulée (aucun test n'interroge le DNS réel)."""

import pytest

from veille_worker import extract

PUBLIC_IP = "93.184.215.14"


@pytest.fixture(autouse=True)
def dns(monkeypatch) -> dict[str, list[str]]:
    """Nom d'hôte → adresses ; tout hôte absent résout vers une IP publique."""
    table: dict[str, list[str]] = {}
    monkeypatch.setattr(
        extract, "resolve_host", lambda host, port: table.get(host, [PUBLIC_IP])
    )
    return table
