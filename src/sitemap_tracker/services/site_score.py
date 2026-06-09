"""Site-Score: bewertet das Gesamtergebnis eines Crawls.

Der sitemap-tracker crawlt Seiten (per httpx oder Playwright) und prueft dabei
in erster Linie die Erreichbarkeit. Der Score (0-100) bildet darum die
Fehlerfreiheit ab: den Anteil der gecrawlten Seiten OHNE Fehler (4xx/5xx,
Verbindungsfehler, Timeout). Redirects (3xx) gelten NICHT als Fehler.

Bewusst KEIN Groessen-Score: die "Groesse"-Spalte ist die HTML-Dokumentgroesse
(httpx laedt keine Ressourcen wie Bilder/CSS/JS nach), aus der sich kein
sinnvoller Seitengewicht-Score ableiten laesst.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models.crawl_result import CrawlResult, CrawlStats, PageStatus

# Stati, die als tatsaechlich gecrawlt zaehlen (ein definitives Ergebnis haben).
# PENDING/CRAWLING laufen noch, SKIPPED (robots.txt) und MAX_DEPTH wurden nie
# geladen - alle vier fliessen nicht in die Bewertung ein.
_SCANNED_STATES = (
    PageStatus.OK,
    PageStatus.REDIRECT,
    PageStatus.REDIRECT_EXTERNAL,
    PageStatus.ERROR,
    PageStatus.TIMEOUT,
)


@dataclass
class SiteScore:
    """Aggregiertes Bewertungsergebnis eines kompletten Crawls."""

    score: int = 0  # Gesamt 0-100 (Anteil fehlerfreier Seiten)
    total_pages: int = 0  # tatsaechlich gecrawlte Seiten
    clean_pages: int = 0  # Seiten ohne Fehler
    pages_with_errors: int = 0  # Seiten mit 4xx/5xx/Verbindungsfehler/Timeout
    total_2xx: int = 0
    total_3xx: int = 0
    total_4xx: int = 0
    total_5xx: int = 0
    total_links: int = 0  # Summe gefundener interner Links ueber alle Seiten
    sitemap_urls: int = 0  # Anzahl URLs in der erzeugten Sitemap (200er + aufgeloeste Ziele)
    resolved_redirects: int = 0  # davon: als Alias aufgeloeste Redirect-Ziele

    @property
    def grade(self) -> str:
        """Schulnoten-aehnliches Kuerzel (A-F) zum Score."""
        s = self.score
        if s >= 90:
            return "A"
        if s >= 75:
            return "B"
        if s >= 60:
            return "C"
        if s >= 45:
            return "D"
        if s >= 30:
            return "E"
        return "F"


def compute_site_score(results: list[CrawlResult], stats: CrawlStats) -> SiteScore:
    """Berechnet den Site-Score aus allen Crawl-Ergebnissen.

    Args:
        results:
            Alle CrawlResults (auch ungecrawlte werden uebergeben, aber
            herausgefiltert).
        stats:
            Die Crawl-Statistiken (liefert die bereits gezaehlten
            HTTP-Status-Kategorien 2xx/3xx/4xx/5xx).

    Returns:
        Ein ``SiteScore`` mit Gesamtscore und Detailwerten.
    """
    scanned = [r for r in results if r.status in _SCANNED_STATES]
    if not scanned:
        return SiteScore()

    total = len(scanned)
    clean = sum(1 for r in scanned if not r.is_error)
    total_links = sum(r.links_found for r in scanned)

    # Score = Anteil fehlerfreier Seiten (0-100).
    score = int(round(100 * clean / total))

    return SiteScore(
        score=score,
        total_pages=total,
        clean_pages=clean,
        pages_with_errors=total - clean,
        total_2xx=stats.total_2xx,
        total_3xx=stats.total_3xx,
        total_4xx=stats.total_4xx,
        total_5xx=stats.total_5xx,
        total_links=total_links,
    )
