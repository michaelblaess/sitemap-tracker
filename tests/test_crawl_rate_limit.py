"""Integrationstest: greift das Rate-Limit im echten Crawl-Pfad?

Der Unit-Test in test_rate_limit.py prueft nur den Limiter selbst. Hier laeuft
ein vollstaendiger Crawl gegen einen lokalen HTTP-Server - einmal gedrosselt,
einmal nicht. Faellt die Verdrahtung im Crawler weg, sind beide Laeufe gleich
schnell und der Test schlaegt fehl.
"""

from __future__ import annotations

import asyncio
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from sitemap_tracker.services.crawler import Crawler

_PAGE_COUNT = 5


class _Handler(BaseHTTPRequestHandler):
    """Liefert eine Startseite, die auf fuenf Unterseiten verlinkt."""

    def do_GET(self) -> None:  # noqa: N802 - von BaseHTTPRequestHandler vorgegeben
        if self.path in ("/", "/index.html"):
            links = "".join(f'<a href="/seite-{i}">Seite {i}</a>' for i in range(_PAGE_COUNT))
            body = f"<html><body>{links}</body></html>".encode()
        elif self.path == "/robots.txt":
            self.send_error(404)
            return
        else:
            body = b"<html><body>Unterseite ohne Links</body></html>"

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        """Unterdrueckt die Server-Logzeilen im Testlauf."""


def _crawl_seconds(rate_per_minute: int) -> tuple[float, int]:
    """Startet den Server, misst einen kompletten Crawl und raeumt wieder auf."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}/"

    crawler = Crawler(
        start_url=base,
        max_depth=2,
        concurrency=8,
        timeout=10,
        respect_robots=False,
        rate_per_minute=rate_per_minute,
    )

    try:
        start = time.monotonic()
        results = asyncio.run(crawler.crawl())
        elapsed = time.monotonic() - start
    finally:
        server.shutdown()
        server.server_close()

    return elapsed, len(results)


class TestCrawlRateLimit:
    def test_unlimited_crawl_reaches_all_pages(self) -> None:
        """Referenzlauf ohne Limit: alle Unterseiten werden gefunden."""
        _, pages = _crawl_seconds(0)
        assert pages >= _PAGE_COUNT, "Der Crawl hat die Unterseiten nicht gefunden"

    def test_rate_limit_adds_waiting_time(self) -> None:
        """Vergleicht gedrosselt gegen ungedrosselt - unabhaengig von der Maschine.

        Eine absolute Obergrenze fuer den ungedrosselten Lauf waere flaky: auf
        einem ausgelasteten CI-Runner dauert derselbe Crawl ein Vielfaches
        (beobachtet: 2,3 s statt 0,08 s). Die Wartezeit des Limiters kommt
        dagegen additiv obendrauf, egal wie langsam die Maschine ist - der
        Abstand zwischen beiden Laeufen ist damit belastbar.
        """
        unlimited, _ = _crawl_seconds(0)
        limited, _ = _crawl_seconds(60)  # 1 s Abstand, sechs Seiten -> ~5 s Warten
        assert limited >= unlimited + 3.0

    def test_rate_limit_slows_the_crawl_down(self) -> None:
        """1200/Minute = 50 ms Abstand; sechs Seiten warten also mehrere Intervalle."""
        elapsed, pages = _crawl_seconds(1200)
        assert pages >= _PAGE_COUNT
        # Untere Schranke mit Abstand zum Sollwert - die Timeraufloesung unter
        # Windows liegt bei rund 15 ms, ein exakter Wert waere flaky.
        assert elapsed >= 0.15
