"""Crawl-Header: konsolidierte Statistik-Anzeige als InfoHeader."""

from __future__ import annotations

from textual_widgets import InfoHeader, InfoItem

from ..i18n import t
from ..models.crawl_result import CrawlStats


class CrawlHeader(InfoHeader):  # type: ignore[misc]
    """Kopf-Panel mit allen Crawl-Statistiken in einem Spalten-Raster.

    Ersetzt das fruehere SummaryPanel und buendelt die Werte, die zuvor
    redundant auch im StatsPanel standen.
    """

    def __init__(self, id: str | None = None) -> None:
        """Erstellt den Crawl-Header mit allen Statistik-Items.

        Args:
            id:
                Optionale Widget-ID.
        """
        items = [
            InfoItem("mode", t("header.mode"), "", value_align="right"),
            InfoItem("discovered", t("stats.discovered"), "0", value_align="right"),
            InfoItem("crawled", t("stats.crawled"), "0", value_align="right"),
            InfoItem("queue", t("stats.queue"), "0", value_align="right"),
            InfoItem("ok", "2xx", "0", value_style="dim", value_align="right"),
            InfoItem("redirect", "3xx", "0", value_style="dim", value_align="right"),
            InfoItem("notfound", "4xx", "0", value_style="dim", value_align="right"),
            InfoItem("server", "5xx", "0", value_style="dim", value_align="right"),
            InfoItem("skipped", t("stats.skipped"), "0", value_align="right"),
            InfoItem("max_depth", t("stats.max_depth"), "0", value_align="right"),
            InfoItem("duration", t("stats.duration"), "-", value_align="right"),
            InfoItem("urls_per_sec", t("stats.urls_per_sec"), "0.0", value_align="right"),
        ]
        super().__init__(
            items,
            columns=4,
            title=t("header.title"),
            collapsible=True,
            id=id,
        )

    def set_info(self, url: str, mode: str) -> None:
        """Setzt die Basis-Info (aktuell nur den Crawl-Modus).

        Args:
            url:
                Start-URL. Wird bereits im Terminal-Subtitle gezeigt und
                hier nicht erneut benoetigt.
            mode:
                Crawl-Modus (httpx / Playwright).
        """
        self.set_value("mode", mode)

    def update_stats(self, stats: CrawlStats) -> None:
        """Aktualisiert alle Statistik-Werte.

        Args:
            stats:
                Aktuelle CrawlStats.
        """
        self.set_value("discovered", str(stats.total_discovered))
        self.set_value("crawled", str(stats.total_crawled))
        self.set_value("queue", str(stats.queue_size))
        self.set_value("ok", str(stats.total_2xx), value_style="bold green" if stats.total_2xx else "dim")
        self.set_value("redirect", str(stats.total_3xx), value_style="bold yellow" if stats.total_3xx else "dim")
        self.set_value("notfound", str(stats.total_4xx), value_style="bold red" if stats.total_4xx else "dim")
        self.set_value("server", str(stats.total_5xx), value_style="bold red" if stats.total_5xx else "dim")
        self.set_value("skipped", str(stats.total_skipped))
        self.set_value("max_depth", str(stats.max_depth_reached))
        self.set_value("duration", stats.duration_display)
        self.set_value("urls_per_sec", f"{stats.urls_per_second:.1f}")
