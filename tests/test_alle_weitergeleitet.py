"""Warnung, wenn ein Crawl ausschliesslich Weiterleitungen liefert.

Am 04.08.2026 kamen bei einem Lauf gegen dieselbe Site 0 von 257 Seiten mit
Status 200 zurueck, alle anderen als Weiterleitung - Ursache war eine
Bot-Abwehr bei 16 parallelen, ungedrosselten Anfragen. Die Sitemap nimmt nur
200er auf und blieb deshalb leer. Das Werkzeug meldete beim Speichern lediglich
"keine Seiten fuer Sitemap", sodass der Fehler beim Speichern vermutet wurde.
Derselbe Lauf mit 8 Anfragen und Drosselung ergab 276 von 341 mit Status 200.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from sitemap_tracker import i18n
from sitemap_tracker.app import SitemapTrackerApp
from sitemap_tracker.i18n import load_locale
from sitemap_tracker.models.crawl_result import CrawlResult, CrawlStats, PageStatus
from sitemap_tracker.screens.scan_summary import ScanSummaryScreen
from sitemap_tracker.services.site_score import SiteScore


@pytest.fixture(autouse=True)
def _sprache() -> Iterator[None]:
    """Laedt Deutsch und stellt den vorherigen Zustand danach wieder her.

    ``load_locale`` setzt Modul-Globals. Ohne Wiederherstellung liefe die
    halbe Suite danach mit geladenen Texten weiter, und Tests, die auf die
    unuebersetzten Schluessel pruefen, kippen je nach Reihenfolge - genau das
    ist hier beim ersten Anlauf passiert (5 Fehler in test_page_analysis).
    """
    vorher_strings = dict(i18n._strings)
    vorher_lang = i18n._current_lang
    load_locale("de")
    yield
    i18n._strings = vorher_strings
    i18n._current_lang = vorher_lang


class TestErkennung:
    """Die reine Bedingung - eng gefasst, damit sie nicht falsch anschlaegt."""

    def test_nur_weiterleitungen_wird_erkannt(self) -> None:
        stats = CrawlStats()
        stats.total_2xx = 0
        stats.total_3xx = 257
        assert SitemapTrackerApp.all_pages_redirected(stats) is True

    def test_normaler_lauf_schlaegt_nicht_an(self) -> None:
        """Der reale Lauf mit 276 von 341 darf keine Warnung ausloesen."""
        stats = CrawlStats()
        stats.total_2xx = 276
        stats.total_3xx = 59
        assert SitemapTrackerApp.all_pages_redirected(stats) is False

    def test_viele_weiterleitungen_mit_treffern_schlaegt_nicht_an(self) -> None:
        """Hoher, aber legitimer Weiterleitungsanteil ist kein Fehlerfall."""
        stats = CrawlStats()
        stats.total_2xx = 1
        stats.total_3xx = 500
        assert SitemapTrackerApp.all_pages_redirected(stats) is False

    def test_leerer_lauf_schlaegt_nicht_an(self) -> None:
        """Ohne jede Weiterleitung ist es ein anderer Fehler."""
        stats = CrawlStats()
        stats.total_2xx = 0
        stats.total_3xx = 0
        assert SitemapTrackerApp.all_pages_redirected(stats) is False


class TestZusammenfassung:
    """Die Warnung muss dort stehen, wo der Anwender nach dem Crawl hinsieht."""

    @staticmethod
    def _text(score: SiteScore) -> str:
        from rich.console import Console

        console = Console(width=100, record=True)
        console.print(ScanSummaryScreen(score)._build_content())
        return console.export_text()

    def test_warnung_erscheint(self) -> None:
        score = SiteScore()
        score.total_2xx = 0
        score.total_3xx = 257
        ausgabe = self._text(score)
        assert "weitergeleitet" in ausgabe
        assert "257" in ausgabe

    def test_ohne_anlass_keine_warnung(self) -> None:
        score = SiteScore()
        score.total_2xx = 276
        score.total_3xx = 59
        assert "weitergeleitet" not in self._text(score)


class TestSpeichernMeldung:
    """Beim Speichern muss die Ursache genannt werden, nicht nur das Symptom."""

    async def test_meldung_nennt_die_ursache(self, tmp_path: Path) -> None:
        """Weiterleitung auf einen FREMDEN Host - so sah der reale Fall aus.

        Zeigt die Weiterleitung dagegen auf eine Seite desselben Hosts, loest
        der Writer sie als Alias auf und schreibt sehr wohl eine Sitemap. Leer
        bleibt sie nur bei fremdem Ziel, also genau bei einer externen
        Sperrseite.
        """
        app = SitemapTrackerApp(start_url="https://example.com")
        app._ask_disclaimer = lambda: None  # type: ignore[method-assign]
        meldungen: list[str] = []

        async with app.run_test(size=(120, 40)):
            app._results = [
                CrawlResult(
                    url=f"https://example.com/{i}",
                    http_status_code=301,
                    content_type="text/html",
                    status=PageStatus.REDIRECT_EXTERNAL,
                    redirect_url="https://sperrseite.example.net/blocked",
                )
                for i in range(5)
            ]
            app.notify = lambda text, **kw: meldungen.append(str(text))  # type: ignore[method-assign]
            app._do_save_sitemap(str(tmp_path / "sitemap.xml"))

        assert meldungen, "es kam ueberhaupt keine Meldung"
        assert "weitergeleitet" in meldungen[0], meldungen
        assert not list(tmp_path.glob("*.xml")), "es haette keine Datei entstehen duerfen"
