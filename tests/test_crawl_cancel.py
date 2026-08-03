"""Nach einem Abbruch darf kein Abschluss gemeldet werden.

Abbrechen konnte der Tracker schon ('x' waehrend des Laufs), aber der
Abbruch-Zweig griff nicht: erkannt wurde er an ``self._crawler is None``, und
das wird erst ganz am Ende des Laufs gesetzt. Ein abgebrochener Crawl lief
deshalb in den vollstaendigen Abschluss - mit "Crawl abgeschlossen", Statistik
im Verlauf und Zusammenfassung, als waere er durchgelaufen.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from sitemap_tracker import app as app_module
from sitemap_tracker.app import SitemapTrackerApp
from sitemap_tracker.i18n import load_locale, t
from sitemap_tracker.models.crawl_result import CrawlResult, CrawlStats, PageStatus


@pytest.fixture(autouse=True)
def _german_locale() -> Iterator[None]:
    """Laedt Deutsch - und raeumt danach wieder auf.

    ``load_locale`` setzt ein Modul-Global. Ohne Aufraeumen wirkt die geladene
    Sprache in allen nachfolgenden Testdateien weiter, und Tests, die gegen die
    unuebersetzten Schluessel pruefen, kippen je nach Reihenfolge.
    """
    from sitemap_tracker import i18n

    strings_before = dict(i18n._strings)
    lang_before = i18n._current_lang
    load_locale("de")
    yield
    i18n._strings = strings_before
    i18n._current_lang = lang_before


def _result(url: str) -> CrawlResult:
    return CrawlResult(
        url=url, status=PageStatus.OK, http_status_code=200, content_type="text/html"
    )


class FakeCrawler:
    """Crawler-Ersatz: liefert zwei Treffer und meldet sich als abgebrochen."""

    cancelled_value = True

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.stats = CrawlStats()
        self._cancelled = FakeCrawler.cancelled_value

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def add_seed_urls(self, urls: Any) -> int:
        return 0

    def cancel(self) -> None:
        self._cancelled = True

    async def crawl(self, *args: Any, **kwargs: Any) -> list[CrawlResult]:
        return [_result("https://example.invalid/a"), _result("https://example.invalid/b")]


async def _drive(monkeypatch: pytest.MonkeyPatch, cancelled: bool, tmp_path: Path) -> SitemapTrackerApp:
    """Faehrt einen Crawl mit dem Crawler-Ersatz und liefert die App zurueck."""
    FakeCrawler.cancelled_value = cancelled
    monkeypatch.setattr(app_module, "Crawler", FakeCrawler)
    monkeypatch.setattr(SitemapTrackerApp, "_ask_disclaimer", lambda self: None, raising=False)

    app = SitemapTrackerApp(start_url="https://example.invalid/")
    async with app.run_test(size=(200, 45)) as pilot:
        app._run_crawl()
        # Auf den Zustand warten, nicht auf eine feste Zahl Durchlaeufe: vor dem
        # Crawl sucht die App noch die offizielle Sitemap ab, und wie lange die
        # fehlschlagenden Abrufe brauchen, ist von Lauf zu Lauf verschieden.
        for _ in range(400):  # bis der Lauf begonnen hat
            await pilot.pause()
            if app._crawl_running:
                break
        for _ in range(400):  # und bis er wieder vorbei ist
            await pilot.pause()
            if not app._crawl_running:
                break
        for _ in range(5):  # Nachlauf: Auswertung nach dem finally-Block
            await pilot.pause()
    return app


@pytest.mark.asyncio
async def test_cancelled_crawl_reports_cancellation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app = await _drive(monkeypatch, cancelled=True, tmp_path=tmp_path)
    assert app.sub_title == t("subtitle.cancelled")
    # Die Treffer des Teillaufs bleiben - genau dafuer bricht man ja ab.
    assert len(app._results) == 2
    # Kein Site-Score: sonst zeigt die Zusammenfassung eine Bewertung des
    # halben Laufs, als waere sie die des ganzen.
    assert app._last_score is None


@pytest.mark.asyncio
async def test_completed_crawl_still_finishes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Gegenprobe: ohne Abbruch laeuft der Abschluss wie bisher."""
    app = await _drive(monkeypatch, cancelled=False, tmp_path=tmp_path)
    assert app.sub_title != t("subtitle.cancelled")
    assert app._last_score is not None
