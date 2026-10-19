"""Texte d'un article : extraction trafilatura, repli sur le contenu du flux, troncature."""

import html
import ipaddress
import re
import socket
import time
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


# Téléchargement des pages d'articles. Les URL viennent de flux tiers (Hacker News pointe vers
# n'importe quel site) : protocole http/https seulement, redirections suivies à la main
# (5 au plus), hôte résolu et refusé s'il n'a pas que des adresses publiques (ce qui écarte
# aussi les services Compose : vllm, postgres, app résolvent en IP privées), content-type
# vérifié avant de lire le corps, corps plafonné, durée totale bornée.
MAX_REDIRECTS = 5
MAX_PAGE_BYTES = 3 * 1024 * 1024
PAGE_DEADLINE = 30.0
HTML_TYPES = {"text/html", "application/xhtml+xml"}
REDIRECT_CODES = {301, 302, 303, 307, 308}


class UnsafeFetchError(RuntimeError):
    """Page refusée : adresse non publique, protocole, redirections, taille, type ou délai."""


def resolve_host(host: str, port: int) -> list[str]:
    """Adresses IP de `host` (résolution système). Remplacée dans les tests."""
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(info[4][0]) for info in infos]


def is_public_ip(address: str) -> bool:
    """Vrai si l'adresse est routable sur Internet (IPv4, IPv6, IPv4 encapsulée comprises)."""
    ip = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(ip, ipaddress.IPv6Address):
        embedded = ip.ipv4_mapped or ip.sixtofour or (ip.teredo[1] if ip.teredo else None)
        if embedded is not None and not is_public_ip(str(embedded)):
            return False
    return ip.is_global and not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _public_address(url: httpx.URL) -> str:
    """Première adresse de l'hôte, après avoir vérifié que toutes sont publiques."""
    if url.scheme not in {"http", "https"}:
        raise UnsafeFetchError(f"protocole refusé : {url.scheme!r}")
    host = url.host
    if not host:
        raise UnsafeFetchError("URL sans hôte")
    try:
        addresses = [str(ipaddress.ip_address(host))]
    except ValueError:
        try:
            addresses = resolve_host(url.raw_host.decode("ascii"), url.port or 0)
        except OSError as exc:
            raise UnsafeFetchError(f"hôte introuvable : {host}") from exc
    if not addresses:
        raise UnsafeFetchError(f"hôte sans adresse : {host}")
    for address in addresses:
        if not is_public_ip(address):
            raise UnsafeFetchError(f"adresse non publique refusée : {host} → {address}")
    return addresses[0]


def _remaining(deadline: float) -> float:
    left = deadline - time.monotonic()
    if left <= 0:
        raise UnsafeFetchError(f"délai total de {PAGE_DEADLINE:.0f} s dépassé")
    return left


def fetch_html(
    url: str,
    client: httpx.Client,
    *,
    max_bytes: int = MAX_PAGE_BYTES,
    total_timeout: float = PAGE_DEADLINE,
    max_redirects: int = MAX_REDIRECTS,
) -> tuple[str, str]:
    """(HTML, URL finale) d'une page tierce, ou UnsafeFetchError / httpx.HTTPError.

    Anti-rebinding : la requête part vers l'IP validée (Host et SNI gardent le nom d'hôte,
    le certificat TLS est vérifié pour ce nom), si bien que le DNS n'est consulté qu'une fois
    par saut. Risque résiduel : un proxy HTTP(S) configuré par l'environnement résout
    lui-même les noms ; la résolution DNS système (getaddrinfo) n'est pas bornée par le délai.
    """
    deadline = time.monotonic() + total_timeout
    current = httpx.URL(url)
    for _hop in range(max_redirects + 1):
        address = _public_address(current)
        pinned = current.copy_with(host=address)
        per_op = min(client.timeout.read or total_timeout, _remaining(deadline))
        with client.stream(
            "GET",
            pinned,
            headers={"Host": current.netloc.decode("ascii"), "Connection": "close"},
            extensions={"sni_hostname": current.raw_host.decode("ascii")},
            follow_redirects=False,
            timeout=httpx.Timeout(per_op),
        ) as response:
            if response.status_code in REDIRECT_CODES:
                location = response.headers.get("location")
                if not location:
                    raise UnsafeFetchError("redirection sans Location")
                current = current.join(location)
                continue
            if response.status_code >= 400:
                raise UnsafeFetchError(f"HTTP {response.status_code}")
            media_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
            if media_type not in HTML_TYPES:
                raise UnsafeFetchError(f"content-type refusé : {media_type or 'absent'}")
            declared = response.headers.get("content-length", "")
            if declared.isdigit() and int(declared) > max_bytes:
                raise UnsafeFetchError(f"page trop lourde ({declared} octets annoncés)")
            body = bytearray()
            for chunk in response.iter_bytes():
                body += chunk
                if len(body) > max_bytes:
                    raise UnsafeFetchError(f"page trop lourde (plus de {max_bytes} octets)")
                _remaining(deadline)
            encoding = response.charset_encoding or "utf-8"
            try:
                text = bytes(body).decode(encoding, errors="replace")
            except LookupError:
                text = bytes(body).decode("utf-8", errors="replace")
            return text, str(current)
    raise UnsafeFetchError(f"plus de {max_redirects} redirections")


def extract_page_text(url: str, client: httpx.Client) -> str | None:
    """Texte principal de la page de l'article, ou None si la page est refusée ou inaccessible."""
    try:
        page, final_url = fetch_html(url, client)
    except (UnsafeFetchError, httpx.HTTPError, httpx.InvalidURL, UnicodeError, ValueError):
        # UnicodeError : nom d'hôte IDNA invalide ; ValueError : port ou adresse invalides.
        return None
    text = trafilatura.extract(
        page, url=final_url, include_comments=False, include_tables=False
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
