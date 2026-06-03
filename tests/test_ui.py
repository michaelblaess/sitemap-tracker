"""Tests fuer UI-Interaktionen: Header-Tooltip, Crawl-Blink, Sitemap-Speichern.

Die Tests fahren die echte Textual-App im Headless-Test-Modus
(``app.run_test()``) hoch und pruefen das Verhalten ueber die oeffentlichen
Aktionen/Callbacks - keine privaten Textual-Interna.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.coordinate import Coordinate

from sitemap_tracker.app import SitemapTrackerApp
from sitemap_tracker.i18n import load_locale, t
from sitemap_tracker.models.crawl_result import CrawlResult, PageStatus
from sitemap_tracker.models.history import HistoryEntry
from sitemap_tracker.widgets.url_table import HeaderTooltipDataTable


@pytest.fixture(autouse=True)
def _german_locale() -> None:
    """Stellt eine definierte Sprache fuer die Tooltip-/Label-Vergleiche."""
    load_locale("de")


def _html_200(url: str) -> CrawlResult:
    """Baut ein 200-HTML-Ergebnis, das die Sitemap aufnehmen wuerde."""
    return CrawlResult(
        url=url,
        status=PageStatus.OK,
        http_status_code=200,
        content_type="text/html",
    )


async def _wait_footer_key(app: SitemapTrackerApp, pilot, action: str):  # type: ignore[no-untyped-def]
    """Wartet, bis die FooterKey-Widgets gemountet sind, und gibt die Taste zurueck.

    Der Footer mountet seine FooterKey-Kinder erst nach einigen Refresh-Zyklen;
    ein einzelnes ``pilot.pause()`` reicht nicht zuverlaessig.
    """
    for _ in range(20):
        key = app._footer_key(action)
        if key is not None:
            return key
        await pilot.pause()
    return None


class TestHeaderTooltip:
    """Der Links-Spaltenkopf zeigt beim Hovern einen erklaerenden Tooltip."""

    async def test_links_header_shows_tooltip(self) -> None:
        app = SitemapTrackerApp(start_url="https://example.com")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.query_one("#url-data", HeaderTooltipDataTable)
            # Spalte 4 = Links-Spalte, Zeile -1 = Spaltenkopf.
            table.hover_coordinate = Coordinate(-1, 4)
            await pilot.pause()
            assert table.tooltip == t("table.tooltip.links")

    async def test_other_header_has_no_tooltip(self) -> None:
        app = SitemapTrackerApp(start_url="https://example.com")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.query_one("#url-data", HeaderTooltipDataTable)
            table.hover_coordinate = Coordinate(-1, 2)
            await pilot.pause()
            assert table.tooltip is None

    async def test_data_row_has_no_tooltip(self) -> None:
        app = SitemapTrackerApp(start_url="https://example.com")
        async with app.run_test() as pilot:
            await pilot.pause()
            table = app.query_one("#url-data", HeaderTooltipDataTable)
            table.hover_coordinate = Coordinate(3, 4)
            await pilot.pause()
            assert table.tooltip is None


class TestCrawlBlink:
    """Die Footer-Taste 'c' blinkt, sobald nach History-Auswahl startklar."""

    async def test_blink_toggles_when_ready(self) -> None:
        app = SitemapTrackerApp(start_url="https://example.com")
        async with app.run_test() as pilot:
            key = await _wait_footer_key(app, pilot, "start_crawl")
            assert key is not None  # FooterKey fuer den Crawl existiert

            app._crawl_ready = True
            app._crawl_running = False
            app._attention_on = False
            # Vier Ticks am Stueck (kein await -> der 0.6s-Timer kann nicht
            # dazwischenfunken) muessen die Klasse alternieren lassen.
            states = []
            for _ in range(4):
                app._tick_attention()
                states.append(key.has_class("-attention"))
            assert states == [True, False, True, False]

    async def test_blink_off_during_crawl(self) -> None:
        app = SitemapTrackerApp(start_url="https://example.com")
        async with app.run_test() as pilot:
            key = await _wait_footer_key(app, pilot, "start_crawl")
            assert key is not None

            app._crawl_ready = True
            app._crawl_running = True  # Crawl laeuft -> kein Blink
            app._attention_on = True
            app._tick_attention()
            assert key.has_class("-attention") is False

    async def test_blink_off_when_not_ready(self) -> None:
        app = SitemapTrackerApp(start_url="https://example.com")
        async with app.run_test() as pilot:
            key = await _wait_footer_key(app, pilot, "start_crawl")
            assert key is not None

            app._crawl_ready = False
            app._crawl_running = False
            app._attention_on = True
            app._tick_attention()
            assert key.has_class("-attention") is False


class TestHistorySelection:
    """History-Auswahl macht startklar; ein Abbruch aendert nichts."""

    async def test_history_pick_sets_ready(self) -> None:
        app = SitemapTrackerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app._crawl_ready = False
            app._on_history_selected(HistoryEntry(url="https://picked.example/"))
            assert app._crawl_ready is True
            assert app.start_url == "https://picked.example/"

    async def test_history_cancel_keeps_state(self) -> None:
        app = SitemapTrackerApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            app._crawl_ready = False
            app._on_history_selected(None)
            assert app._crawl_ready is False


class TestSitemapSaveDialog:
    """Die Aktion 'm' oeffnet den Speichern-unter-Dialog (FileSave)."""

    async def test_dialog_opens_with_results(self) -> None:
        app = SitemapTrackerApp(start_url="https://example.com")
        async with app.run_test() as pilot:
            await pilot.pause()
            app._results = [_html_200("https://example.com/")]
            depth_before = len(app.screen_stack)
            app.action_save_sitemap()
            await pilot.pause()
            assert len(app.screen_stack) == depth_before + 1
            assert type(app.screen_stack[-1]).__name__ == "FileSave"

    async def test_no_dialog_without_results(self) -> None:
        app = SitemapTrackerApp(start_url="https://example.com")
        async with app.run_test() as pilot:
            await pilot.pause()
            app._results = []
            depth_before = len(app.screen_stack)
            app.action_save_sitemap()
            await pilot.pause()
            # Kein neuer Screen - nur ein Warn-Toast.
            assert len(app.screen_stack) == depth_before

    async def test_target_chosen_writes_file(self, tmp_path: Path) -> None:
        app = SitemapTrackerApp(start_url="https://example.com")
        async with app.run_test() as pilot:
            await pilot.pause()
            app._results = [_html_200("https://example.com/")]
            target = tmp_path / "out.xml"
            app._on_sitemap_target_chosen(target)
            await pilot.pause()
            assert target.is_file()
            assert "<urlset" in target.read_text(encoding="utf-8")
            # Zielverzeichnis wird fuer den naechsten Dialog gemerkt.
            assert app._last_export_dir == str(tmp_path)

    async def test_target_none_writes_nothing(self, tmp_path: Path) -> None:
        app = SitemapTrackerApp(start_url="https://example.com")
        async with app.run_test() as pilot:
            await pilot.pause()
            app._results = [_html_200("https://example.com/")]
            before = app._last_export_dir
            app._on_sitemap_target_chosen(None)
            await pilot.pause()
            # Abbruch: keine Datei, kein Verzeichniswechsel.
            assert list(tmp_path.iterdir()) == []
            assert app._last_export_dir == before
