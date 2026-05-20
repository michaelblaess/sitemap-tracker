"""Holt die HTML-Quelle einer verweisenden Seite und findet die Stelle,
an der ein bestimmter (defekter) Link verwendet wird.

Wird vom 4xx/5xx-Quellcode-Viewer benutzt. Cachet nichts — bei jedem Aufruf
wird die Seite frisch geholt. Bei grossen Crawls wuerde Caching schnell zu
Speicher-Druck fuehren, und der User klickt typischerweise nur fuer wenige
problematische Links nach.
"""

from __future__ import annotations

from typing import NamedTuple
from urllib.parse import unquote, urlparse

import httpx

_DEFAULT_TIMEOUT = 10.0


class SourceLocation(NamedTuple):
    """Ergebnis einer ``fetch_and_locate``-Suche."""

    html: str
    """Der vollstaendige HTML-Quellcode der Seite."""

    line: int
    """1-basierte Zeile mit dem Treffer. ``0`` wenn nicht gefunden."""

    column: int
    """1-basierte Spalte mit dem Treffer. ``0`` wenn nicht gefunden."""

    length: int
    """Laenge des gematchten Substrings im HTML. ``0`` wenn nicht gefunden."""


async def fetch_and_locate(
    source_url: str,
    target_url: str,
    *,
    cookies: list[dict[str, str]] | None = None,
    user_agent: str = "",
    timeout: float = _DEFAULT_TIMEOUT,
) -> SourceLocation:
    """Laedt ``source_url`` per httpx und sucht im HTML nach ``target_url``.

    Args:
        source_url:
            Die verweisende Seite (200, enthaelt den defekten Link).
        target_url:
            Die defekte URL, die im HTML stehen soll.
        cookies:
            Optionale Cookie-Liste fuer authentisierte Seiten.
        user_agent:
            Optionaler User-Agent.
        timeout:
            HTTP-Timeout in Sekunden.

    Returns:
        ``SourceLocation`` mit HTML, Zeile, Spalte — Zeile=0 wenn der
        Link nicht direkt im HTML steht (z.B. via JS nachgeladen).
    """
    jar = httpx.Cookies()
    if cookies:
        parsed = urlparse(source_url)
        domain = parsed.hostname or ""
        for c in cookies:
            jar.set(c.get("name", ""), c.get("value", ""), domain=domain, path="/")
    headers = {"User-Agent": user_agent} if user_agent else {}

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=timeout,
        verify=False,
        cookies=jar,
        headers=headers,
    ) as client:
        response = await client.get(source_url)
        html = response.text

    line, col, length = _locate(html, target_url)
    return SourceLocation(html=html, line=line, column=col, length=length)


def _locate(html: str, target_url: str) -> tuple[int, int, int]:
    """Sucht den ersten Treffer einer Reihe von URL-Varianten im HTML.

    Varianten in dieser Reihenfolge: Original, ohne Fragment, ohne Query,
    nur Pfad, URL-dekodiert.

    Args:
        html:
            HTML-Inhalt der Seite.
        target_url:
            Die zu suchende URL.

    Returns:
        ``(line, column, length)`` — 1-basiert fuer Zeile/Spalte,
        ``length`` = Laenge des gematchten Substrings. ``(0, 0, 0)`` wenn
        nichts passt.
    """
    if not target_url:
        return (0, 0, 0)

    candidates = [target_url]
    if "#" in target_url:
        candidates.append(target_url.split("#", 1)[0])
    if "?" in target_url:
        candidates.append(target_url.split("?", 1)[0])
    parsed = urlparse(target_url)
    if parsed.path and parsed.path != "/":
        candidates.append(parsed.path)
        # Letzte Pfad-Komponente — fangt relative Links wie
        # ``<a href="seitenname">`` ab, die im HTML nicht als
        # absolute URL stehen.
        last = parsed.path.rstrip("/").rsplit("/", 1)[-1]
        if last and len(last) >= 3:
            candidates.append(f'"{last}"')
            candidates.append(f"'{last}'")
    decoded = unquote(target_url)
    if decoded != target_url:
        candidates.append(decoded)

    # Duplikate raus, Reihenfolge erhalten
    seen: set[str] = set()
    ordered = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            ordered.append(c)

    for cand in ordered:
        idx = html.find(cand)
        if idx < 0:
            continue
        line = html.count("\n", 0, idx) + 1
        last_nl = html.rfind("\n", 0, idx)
        column = idx - last_nl if last_nl >= 0 else idx + 1
        return (line, column, len(cand))
    return (0, 0, 0)
