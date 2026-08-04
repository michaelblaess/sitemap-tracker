"""Prueft, ob verlinkte Dateien (PDF, Office, Archive) erreichbar sind.

Der Crawler laesst solche Ziele bewusst links liegen - ein PDF hat keine
Folgelinks und wuerde nur Bandbreite kosten. Damit faellt aber auch nicht auf,
wenn eines davon tot ist. Genau dieser Fall trat am 04.08.2026 auf: ein
verlinktes PDF war zeitweise nicht abrufbar, ohne dass ein Crawl das gemeldet
haette.

Geprueft wird mit ``HEAD``, das liefert Status, Groesse und Typ ohne den Inhalt
zu laden - bei einem 200-KB-PDF ist das der Unterschied zwischen einer
Statuszeile und einem vollen Download. Server, die ``HEAD`` nicht moegen
(405/501), bekommen als Rueckfall ein ``GET`` mit ``Range: bytes=0-0``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx

from ..models.crawl_result import friendly_error_message
from .rate_limit import RateLimiter

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

# Statuscodes, bei denen ein Server HEAD ablehnt, die Datei aber da sein kann.
_HEAD_NICHT_UNTERSTUETZT = frozenset({405, 501})


@dataclass
class FileCheckResult:
    """Ergebnis der Erreichbarkeitspruefung einer einzelnen Datei."""

    url: str
    fundort: str = ""
    status_code: int = 0
    content_type: str = ""
    size_bytes: int = 0
    error_message: str = ""
    per_get_geprueft: bool = False

    @property
    def ok(self) -> bool:
        """True, wenn die Datei abrufbar ist (2xx)."""
        return 200 <= self.status_code < 300

    @property
    def endung(self) -> str:
        """Datei-Endung ohne Punkt, klein geschrieben (leer wenn keine)."""
        pfad = urlparse(self.url).path
        _, _, rest = pfad.rpartition(".")
        return rest.lower() if "." in pfad and "/" not in rest else ""

    @property
    def size_display(self) -> str:
        """Groesse in KB/MB, deutsch formatiert - leer wenn unbekannt."""
        if self.size_bytes <= 0:
            return ""
        if self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB".replace(".", ",")
        return f"{self.size_bytes / (1024 * 1024):.1f} MB".replace(".", ",")


@dataclass
class FileCheckSummary:
    """Gesamtergebnis eines Pruefdurchlaufs."""

    results: list[FileCheckResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def failed(self) -> list[FileCheckResult]:
        """Alle nicht erreichbaren Dateien - Fehler zuerst sortiert."""
        return [r for r in self.results if not r.ok]

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.ok)


def filter_by_extensions(links: dict[str, str], extensions: Iterable[str]) -> dict[str, str]:
    """Filtert die gefundenen Datei-Links nach Endungen.

    Args:
        links:
            Alle gefundenen Datei-Links als ``URL -> Fundort``.
        extensions:
            Gewuenschte Endungen, mit oder ohne fuehrenden Punkt. Eine leere
            Auswahl bedeutet "alle" - so muss der Anwender nichts eintippen,
            wenn er ohnehin alles sehen will.

    Returns:
        Die passenden Eintraege, Reihenfolge bleibt erhalten.
    """
    gewuenscht = {e.strip().lstrip(".").lower() for e in extensions if e.strip()}
    if not gewuenscht:
        return dict(links)
    treffer: dict[str, str] = {}
    for url, fundort in links.items():
        pfad = urlparse(url).path.lower()
        if any(pfad.endswith(f".{e}") for e in gewuenscht):
            treffer[url] = fundort
    return treffer


def parse_extensions(raw: str) -> list[str]:
    """Zerlegt die Eingabe des Anwenders in einzelne Endungen.

    Akzeptiert Komma, Semikolon und Leerzeichen als Trenner, mit und ohne
    Punkt - also sowohl ``pdf, docx`` als auch ``.pdf .docx``.

    Args:
        raw:
            Der eingegebene Text.

    Returns:
        Liste der Endungen ohne Punkt, klein geschrieben, ohne Dubletten.
    """
    roh = raw.replace(";", ",").replace(" ", ",")
    gesehen: list[str] = []
    for teil in roh.split(","):
        endung = teil.strip().lstrip(".").lower()
        if endung and endung not in gesehen:
            gesehen.append(endung)
    return gesehen


class FileChecker:
    """Prueft eine Menge von Datei-URLs auf Erreichbarkeit.

    Die Pruefung laeuft gedrosselt und mit begrenzter Parallelitaet. Das ist
    hier kein Beiwerk: ein Schwung ungebremster Anfragen laeuft in dieselbe
    Bot-Abwehr, die am 04.08.2026 einen ganzen Crawl unbrauchbar gemacht hat.
    """

    def __init__(
        self,
        *,
        timeout: int = 30,
        concurrency: int = 8,
        rate_per_minute: int = 60,
        user_agent: str = "",
        proxy: str = "",
        cookies: list[dict[str, str]] | None = None,
    ) -> None:
        self._timeout = timeout
        self._concurrency = max(1, concurrency)
        self._limiter = RateLimiter(rate_per_minute)
        self._user_agent = user_agent
        self._proxy = proxy.strip()
        self._cookies = cookies or []
        self._cancelled = False

    def cancel(self) -> None:
        """Bricht einen laufenden Durchlauf ab."""
        self._cancelled = True

    async def check(
        self,
        links: dict[str, str],
        on_progress: Callable[[int, int], None] | None = None,
    ) -> FileCheckSummary:
        """Prueft alle uebergebenen Dateien.

        Args:
            links:
                Die zu pruefenden Dateien als ``URL -> Fundort``.
            on_progress:
                Optionaler Rueckruf ``(fertig, gesamt)`` nach jeder Datei.

        Returns:
            Das Gesamtergebnis.
        """
        self._cancelled = False
        gesamt = len(links)
        fertig = 0
        ergebnisse: list[FileCheckResult] = []
        sperre = asyncio.Semaphore(self._concurrency)

        jar = httpx.Cookies()
        for c in self._cookies:
            jar.set(c["name"], c["value"])

        async with httpx.AsyncClient(
            timeout=float(self._timeout),
            follow_redirects=True,
            verify=False,
            cookies=jar,
            headers={"User-Agent": self._user_agent} if self._user_agent else None,
            proxy=self._proxy or None,
        ) as client:

            async def eine(url: str, fundort: str) -> None:
                nonlocal fertig
                async with sperre:
                    if self._cancelled:
                        return
                    await self._limiter.acquire()
                    ergebnis = await self._pruefe_eine(client, url, fundort)
                ergebnisse.append(ergebnis)
                fertig += 1
                if on_progress is not None:
                    on_progress(fertig, gesamt)

            await asyncio.gather(
                *(eine(url, fundort) for url, fundort in links.items()),
                return_exceptions=True,
            )

        # Fehler nach oben, dann stabil nach URL - so steht das Wichtige zuerst.
        ergebnisse.sort(key=lambda r: (r.ok, r.url))
        return FileCheckSummary(results=ergebnisse)

    async def _pruefe_eine(self, client: httpx.AsyncClient, url: str, fundort: str) -> FileCheckResult:
        """Prueft eine einzelne Datei, HEAD mit GET-Rueckfall."""
        ergebnis = FileCheckResult(url=url, fundort=fundort)
        try:
            antwort = await client.head(url)
            if antwort.status_code in _HEAD_NICHT_UNTERSTUETZT:
                # Server mag kein HEAD - minimalen GET nachschieben, der laedt
                # dank Range nur das erste Byte statt der ganzen Datei.
                antwort = await client.get(url, headers={"Range": "bytes=0-0"})
                ergebnis.per_get_geprueft = True
            ergebnis.status_code = antwort.status_code
            ergebnis.content_type = antwort.headers.get("content-type", "")
            laenge = antwort.headers.get("content-range", "").rpartition("/")[2]
            if not laenge.isdigit():
                laenge = antwort.headers.get("content-length", "")
            ergebnis.size_bytes = int(laenge) if laenge.isdigit() else 0
        except Exception as fehler:
            ergebnis.error_message = friendly_error_message(fehler)
        return ergebnis
