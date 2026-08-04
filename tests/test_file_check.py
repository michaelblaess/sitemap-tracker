"""Pruefung verlinkter Dateien (PDF, Office, Archive) auf Erreichbarkeit.

Anlass: Am 04.08.2026 war ein verlinktes PDF zeitweise nicht abrufbar, ohne
dass ein Crawl das gemeldet haette - der Crawler laesst solche Ziele bewusst
aus, damit fiel der Ausfall schlicht niemandem auf.

Der HTTP-Teil laeuft gegen einen echten lokalen Server (``ThreadingHTTPServer``
auf ``127.0.0.1:0``), nicht gegen Attrappen: nur so ist belegt, dass HEAD, der
GET-Rueckfall und die Groessenermittlung wirklich funktionieren.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from sitemap_tracker.services.crawler import Crawler
from sitemap_tracker.services.file_checker import (
    FileChecker,
    filter_by_extensions,
    parse_extensions,
)

_PDF_INHALT = b"%PDF-1.4 nur-fuer-den-test" * 40


class _Handler(BaseHTTPRequestHandler):
    """Bedient drei Faelle: vorhanden, fehlend, und HEAD wird abgelehnt."""

    def log_message(self, *args: object) -> None:  # Testausgabe ruhig halten
        return

    def _kopf(self, status: int, laenge: int, typ: str = "application/pdf") -> None:
        self.send_response(status)
        self.send_header("Content-Type", typ)
        self.send_header("Content-Length", str(laenge))
        self.end_headers()

    def do_HEAD(self) -> None:  # noqa: N802 - von BaseHTTPRequestHandler vorgegeben
        if self.path == "/kein-head.pdf":
            self.send_response(405)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/fehlt.pdf":
            self._kopf(404, 0, "text/html")
            return
        self._kopf(200, len(_PDF_INHALT))

    def do_GET(self) -> None:  # noqa: N802 - von BaseHTTPRequestHandler vorgegeben
        if self.path == "/fehlt.pdf":
            self._kopf(404, 0, "text/html")
            self.wfile.write(b"")
            return
        self._kopf(200, len(_PDF_INHALT))
        self.wfile.write(_PDF_INHALT)


@pytest.fixture
def server() -> Iterator[str]:
    """Startet einen echten HTTP-Server und liefert seine Basis-URL."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()


class TestEndungenZerlegen:
    """Die Eingabe des Anwenders soll grosszuegig ausgelegt werden."""

    def test_komma_und_punkt(self) -> None:
        assert parse_extensions("pdf, .docx ,XLSX") == ["pdf", "docx", "xlsx"]

    def test_leerzeichen_und_semikolon(self) -> None:
        assert parse_extensions(".pdf; docx") == ["pdf", "docx"]

    def test_leere_eingabe(self) -> None:
        assert parse_extensions("   ") == []

    def test_dubletten_fallen_weg(self) -> None:
        assert parse_extensions("pdf, pdf, .PDF") == ["pdf"]


class TestFiltern:
    LINKS = {
        "https://example.com/a.pdf": "https://example.com/",
        "https://example.com/b.docx": "https://example.com/x",
        "https://example.com/c.zip": "https://example.com/y",
    }

    def test_eine_endung(self) -> None:
        assert list(filter_by_extensions(self.LINKS, ["pdf"])) == ["https://example.com/a.pdf"]

    def test_mehrere_endungen(self) -> None:
        treffer = filter_by_extensions(self.LINKS, ["pdf", "docx"])
        assert len(treffer) == 2

    def test_leere_auswahl_bedeutet_alle(self) -> None:
        assert len(filter_by_extensions(self.LINKS, [])) == 3

    def test_query_string_stoert_nicht(self) -> None:
        links = {"https://example.com/d.pdf?v=2": "https://example.com/"}
        assert len(filter_by_extensions(links, ["pdf"])) == 1


class TestPruefung:
    """Gegen einen echten Server - Attrappen wuerden hier nichts beweisen."""

    async def test_vorhandene_datei_gilt_als_erreichbar(self, server: str) -> None:
        checker = FileChecker(rate_per_minute=0, timeout=10)
        summary = await checker.check({f"{server}/da.pdf": "seite"})
        assert summary.total == 1
        ergebnis = summary.results[0]
        assert ergebnis.ok
        assert ergebnis.status_code == 200
        assert ergebnis.size_bytes == len(_PDF_INHALT)
        assert ergebnis.fundort == "seite"

    async def test_fehlende_datei_wird_gemeldet(self, server: str) -> None:
        checker = FileChecker(rate_per_minute=0, timeout=10)
        summary = await checker.check({f"{server}/fehlt.pdf": "seite"})
        assert summary.failed
        assert summary.failed[0].status_code == 404
        assert summary.ok_count == 0

    async def test_rueckfall_auf_get_wenn_head_abgelehnt(self, server: str) -> None:
        """405 auf HEAD darf nicht als toter Link durchgehen."""
        checker = FileChecker(rate_per_minute=0, timeout=10)
        summary = await checker.check({f"{server}/kein-head.pdf": "seite"})
        ergebnis = summary.results[0]
        assert ergebnis.ok, "Datei ist vorhanden, nur HEAD wird abgelehnt"
        assert ergebnis.per_get_geprueft

    async def test_fehler_stehen_oben(self, server: str) -> None:
        checker = FileChecker(rate_per_minute=0, timeout=10)
        summary = await checker.check(
            {f"{server}/da.pdf": "a", f"{server}/fehlt.pdf": "b", f"{server}/auch-da.pdf": "c"}
        )
        assert not summary.results[0].ok, "die kaputte Datei gehoert nach oben"
        assert summary.ok_count == 2

    async def test_fortschritt_wird_gemeldet(self, server: str) -> None:
        meldungen: list[tuple[int, int]] = []
        checker = FileChecker(rate_per_minute=0, timeout=10)
        await checker.check(
            {f"{server}/a.pdf": "", f"{server}/b.pdf": ""},
            on_progress=lambda fertig, gesamt: meldungen.append((fertig, gesamt)),
        )
        assert meldungen[-1] == (2, 2)


class TestDrosselung:
    """Ohne Bremse laeuft die Pruefung in dieselbe Bot-Abwehr wie der Crawl."""

    async def test_drosselung_kostet_zusaetzliche_zeit(self, server: str) -> None:
        """Relativer Vergleich - absolute Schranken sind auf fremder Hardware wertlos."""
        import time

        links = {f"{server}/{i}.pdf": "" for i in range(4)}

        start = time.monotonic()
        await FileChecker(rate_per_minute=0, timeout=10, concurrency=1).check(dict(links))
        ohne = time.monotonic() - start

        start = time.monotonic()
        await FileChecker(rate_per_minute=60, timeout=10, concurrency=1).check(dict(links))
        mit = time.monotonic() - start

        # 60/min = 1 s Abstand, vier Dateien -> rund 3 s obendrauf.
        assert mit >= ohne + 2.0


class TestDialogDurchlauf:
    """Der komplette Weg durch die echte App - Taste, Dialog, Ergebnis.

    Die Bausteine einzeln zu pruefen genuegt hier nicht: beim Bauen war der
    Dialog zweimal kaputt, obwohl Service und Filter laengst gruen waren -
    einmal weil ``compose`` ein Widget abfragte, das es gerade erst erzeugte,
    einmal wegen zu frueher Initialisierung in ``on_mount``.
    """

    @staticmethod
    async def _oeffne(server: str, links: dict[str, str]):
        from sitemap_tracker.app import SitemapTrackerApp
        from sitemap_tracker.models.crawl_result import CrawlResult

        app = SitemapTrackerApp(start_url="https://example.com")
        app._ask_disclaimer = lambda: None  # type: ignore[method-assign]
        return app, CrawlResult(
            url="https://example.com/", http_status_code=200, content_type="text/html"
        )

    async def test_taste_oeffnet_dialog_und_prueft(self, server: str) -> None:
        from textual.widgets import Button, DataTable, Input

        from sitemap_tracker.screens.file_check import FileCheckScreen

        app, ergebnis = await self._oeffne(server, {})
        async with app.run_test(size=(140, 45)) as pilot:
            app._results = [ergebnis]
            app._document_links = {
                f"{server}/handbuch.pdf": "https://example.com/",
                f"{server}/fehlt.pdf": "https://example.com/service",
                f"{server}/liste.xlsx": "https://example.com/",
            }
            app._settings.rate_limit_enabled = False
            app._settings.proxy_url = ""  # lokaler Testserver, kein Proxy

            await pilot.press("p")
            for _ in range(25):
                await pilot.pause()

            screen = app.screen
            assert isinstance(screen, FileCheckScreen)
            assert screen.query_one("#fc-ext", Input).value == "pdf"

            screen.query_one("#fc-run", Button).press()
            for _ in range(120):
                await pilot.pause()

            tabelle = screen.query_one("#fc-table", DataTable)
            # Nur die beiden PDFs, das xlsx faellt durch den Endungsfilter.
            assert tabelle.row_count == 2, "Endungsfilter hat nicht gegriffen"
            erste = [str(z) for z in tabelle.get_row_at(0)]
            assert erste[0] == "404", f"die kaputte Datei gehoert nach oben: {erste}"

    async def test_ohne_dateien_kein_dialog(self, server: str) -> None:
        """Ohne eingesammelte Links soll die Taste gar nicht erst greifen."""
        app, ergebnis = await self._oeffne(server, {})
        async with app.run_test(size=(140, 45)) as pilot:
            app._results = [ergebnis]
            app._document_links = {}
            assert app.check_action("check_files", ()) is None
            await pilot.press("p")
            for _ in range(10):
                await pilot.pause()
            assert app.screen.id == "_default", "es haette kein Dialog aufgehen duerfen"


class TestCrawlerSammeltDateien:
    """Der Crawler muss die Links ueberhaupt erst aufheben."""

    def test_datei_link_wird_gemerkt_statt_verworfen(self) -> None:
        crawler = Crawler(start_url="https://example.com")
        eingereiht = crawler._enqueue("https://example.com/handbuch.pdf", 1, "https://example.com/")
        assert eingereiht is False, "PDFs werden weiterhin nicht gecrawlt"
        assert crawler.document_links == {
            "https://example.com/handbuch.pdf": "https://example.com/"
        }

    def test_html_landet_nicht_in_der_dateiliste(self) -> None:
        crawler = Crawler(start_url="https://example.com")
        crawler._enqueue("https://example.com/seite", 1, "https://example.com/")
        assert crawler.document_links == {}

    def test_erster_fundort_bleibt_erhalten(self) -> None:
        """Dieselbe Datei auf mehreren Seiten - der erste Fundort genuegt."""
        crawler = Crawler(start_url="https://example.com")
        crawler._enqueue("https://example.com/a.pdf", 1, "https://example.com/eins")
        crawler._enqueue("https://example.com/a.pdf", 2, "https://example.com/zwei")
        assert crawler.document_links["https://example.com/a.pdf"] == "https://example.com/eins"
