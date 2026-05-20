"""Crawl-Header: konsolidierte Statistik-Anzeige als InfoHeader."""

from __future__ import annotations

from textual_widgets import InfoHeader, InfoItem

from ..i18n import t
from ..models.crawl_result import CrawlStats


class CrawlHeader(InfoHeader):  # type: ignore[misc]
    """Kopf-Panel mit allen Crawl-Informationen in einem 4-Spalten-Raster.

    Die Spalten sind thematisch gruppiert (Fuellrichtung spaltenweise):
        1. Ziel:          URL, Modus, robots.txt, Queue
        2. Konfiguration: Concurrency, Timeout, Max Tiefe, Dauer
        3. Statuscodes:   2xx, 3xx, 4xx, 5xx
        4. Fortschritt:   Gecrawlt, Entdeckt, Uebersprungen, URLs/Sek
    """

    def __init__(
        self,
        id: str | None = None,
        render: bool = False,
        respect_robots: bool = True,
        concurrency: int = 8,
        timeout: int = 30,
        max_depth: int = 3,
    ) -> None:
        """Erstellt den Crawl-Header.

        Args:
            id:
                Optionale Widget-ID.
            render:
                True fuer Playwright-Modus, False fuer httpx.
            respect_robots:
                Ob robots.txt beachtet wird.
            concurrency:
                Anzahl paralleler Requests.
            timeout:
                Request-Timeout in Sekunden.
            max_depth:
                Konfigurierte maximale Crawl-Tiefe.
        """
        items = [
            # Spalte 1: Ziel
            InfoItem("url", t("header.url"), ""),
            InfoItem("mode", t("header.mode"), self._mode_text(render)),
            InfoItem(
                "robots",
                t("header.robots"),
                self._robots_text(respect_robots),
                value_style="green" if respect_robots else "dim",
            ),
            InfoItem("queue", t("stats.queue"), "0"),
            # Spalte 2: Konfiguration
            InfoItem("concurrency", t("header.concurrency"), t("header.concurrency_value", count=concurrency)),
            InfoItem("timeout", t("header.timeout"), f"{timeout}s"),
            InfoItem("max_depth", t("stats.max_depth"), str(max_depth)),
            InfoItem("duration", t("stats.duration"), "-"),
            # Spalte 3: Statuscodes
            InfoItem("ok", "2xx", "0", value_style="dim"),
            InfoItem("redirect", "3xx", "0", value_style="dim"),
            InfoItem("notfound", "4xx", "0", value_style="dim"),
            InfoItem("server", "5xx", "0", value_style="dim"),
            # Spalte 4: Fortschritt
            InfoItem("crawled", t("stats.crawled"), "0"),
            InfoItem("discovered", t("stats.discovered"), "0"),
            InfoItem("skipped", t("stats.skipped"), "0"),
            InfoItem("urls_per_sec", t("stats.urls_per_sec"), "0.0"),
        ]
        super().__init__(
            items,
            columns=4,
            fill="column",
            title=t("header.title"),
            collapsible=True,
            id=id,
        )

    @staticmethod
    def _mode_text(render: bool) -> str:
        """Gibt den Anzeigetext fuer den Crawl-Modus zurueck."""
        return t("mode.playwright") if render else t("mode.httpx")

    @staticmethod
    def _robots_text(respect_robots: bool) -> str:
        """Gibt den Anzeigetext fuer die robots.txt-Beachtung zurueck."""
        return t("log.robots_on") if respect_robots else t("log.robots_off")

    def set_url(self, url: str) -> None:
        """Setzt die aktuell gecrawlte URL.

        Args:
            url: Die Start-URL des Crawls.
        """
        self.set_value("url", url)

    def update_config(
        self,
        render: bool,
        respect_robots: bool,
        concurrency: int,
        timeout: int,
        max_depth: int,
    ) -> None:
        """Aktualisiert die Konfigurationswerte (z.B. nach History-Restore).

        Args:
            render:
                True fuer Playwright-Modus.
            respect_robots:
                Ob robots.txt beachtet wird.
            concurrency:
                Anzahl paralleler Requests.
            timeout:
                Request-Timeout in Sekunden.
            max_depth:
                Konfigurierte maximale Crawl-Tiefe.
        """
        self.set_value("mode", self._mode_text(render))
        self.set_value(
            "robots",
            self._robots_text(respect_robots),
            value_style="green" if respect_robots else "dim",
        )
        self.set_value("concurrency", t("header.concurrency_value", count=concurrency))
        self.set_value("timeout", f"{timeout}s")
        self.set_value("max_depth", str(max_depth))

    def update_stats(self, stats: CrawlStats) -> None:
        """Aktualisiert die dynamischen Statistik-Werte.

        Args:
            stats:
                Aktuelle CrawlStats.
        """
        self.set_value("queue", str(stats.queue_size))
        self.set_value("duration", stats.duration_display)
        self.set_value("ok", str(stats.total_2xx), value_style="bold green" if stats.total_2xx else "dim")
        self.set_value("redirect", str(stats.total_3xx), value_style="bold yellow" if stats.total_3xx else "dim")
        self.set_value("notfound", str(stats.total_4xx), value_style="bold red" if stats.total_4xx else "dim")
        self.set_value("server", str(stats.total_5xx), value_style="bold red" if stats.total_5xx else "dim")
        self.set_value("crawled", str(stats.total_crawled))
        self.set_value("discovered", str(stats.total_discovered))
        self.set_value("skipped", str(stats.total_skipped))
        self.set_value("urls_per_sec", f"{stats.urls_per_second:.1f}")
