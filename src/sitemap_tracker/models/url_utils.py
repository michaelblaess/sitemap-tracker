"""Gemeinsame URL-Helfer (Normalisierung, Domain-Vergleich).

Liegt in ``models/``, damit sowohl der Writer (models) als auch der Crawler
(services) ohne Schichtverletzung darauf zugreifen koennen.
"""

from __future__ import annotations

from urllib.parse import quote, unquote, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalisiert eine URL fuer Deduplizierung.

    Normalisierungsschritte:
    - Scheme und Domain lowercase
    - Percent-Encoding vereinheitlichen (dekodieren und einheitlich
      re-enkodieren, damit z.B. ``gesch%C3%A4ftskunden`` und
      ``bereich-b`` als gleich erkannt werden)
    - Leerer Pfad wird zu ``/``
    - Fragment entfernen

    Der Pfad wird NICHT lowercased - Server-Pfade sind case-sensitiv
    (``/Produkte`` und ``/produkte`` koennen verschiedene Seiten sein).

    Args:
        url:
            Die zu normalisierende URL.

    Returns:
        Normalisierte URL.
    """
    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    path = unquote(parsed.path)
    path = quote(path, safe="/:@!$&'*+,;=-._~")
    if not path:
        path = "/"

    query = unquote(parsed.query)
    query = quote(query, safe="/:@!$&'*+,;=-._~?=")

    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def same_host(host_a: str, host_b: str) -> bool:
    """Prueft ob zwei Hosts identisch sind (case-insensitiv, ohne Port).

    Bewusst KEIN registrierbarer-Domain-Vergleich (eTLD+1): eine ``sitemap.xml``
    darf laut Standard nur URLs DESSELBEN Hosts enthalten. Schwester-Subdomains
    wie ``www.kunde.example`` oder ``www.shop.kunde.example`` gehoeren NICHT in die
    Sitemap von ``www.blog.kunde.example`` - Suchmaschinen verwerfen cross-host
    Eintraege.

    Args:
        host_a:
            Erster Hostname (ggf. mit Port).
        host_b:
            Zweiter Hostname (ggf. mit Port).

    Returns:
        True wenn beide denselben Host bezeichnen, sonst False.
    """
    norm_a = host_a.lower().split(":")[0]
    return bool(norm_a) and norm_a == host_b.lower().split(":")[0]
