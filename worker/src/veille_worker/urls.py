"""Normalisation d'URL : clé de dédoublonnage des articles."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_url(url: str) -> str:
    """Schéma et hôte en minuscules, port par défaut retiré, sans fragment ni paramètre utm_*.

    Les autres paramètres sont gardés dans leur ordre : ils identifient souvent l'article.
    """
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    netloc = host
    if parts.port is not None and DEFAULT_PORTS.get(scheme) != parts.port:
        netloc = f"{host}:{parts.port}"
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
        ]
    )
    return urlunsplit((scheme, netloc, parts.path or "/", query, ""))
