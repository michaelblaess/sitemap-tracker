"""Settings-Dialog fuer den Sitemap Tracker.

Erbt vom standardisierten `BaseSettingsScreen` (textual-widgets): die Basis
liefert Look, Sprach-Tab und Save/Cancel; diese Klasse ergaenzt nur den
Crawl-Tab mit den App-spezifischen Optionen.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Checkbox, Input, Label, Static, TabPane
from textual_widgets import BaseSettingsScreen

from ..i18n import t
from ..models.history import History
from ..models.settings import SETTINGS_FILE
from ..services.preview_service import CACHE_DIR as PREVIEW_CACHE_DIR


class SitemapSettingsScreen(BaseSettingsScreen):
    """App-Settings: Sprache (von der Basis) + Crawl-Optionen."""

    def app_tabs(self) -> ComposeResult:
        """Ergaenzt den Crawl-Tab mit robots.txt, Playwright und Crawl-Parametern."""
        with TabPane(t("settings.tab_crawl"), id="settings-tab-crawl"), VerticalScroll():
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.robots_label"))
                yield Checkbox(
                    t("settings.robots_checkbox"),
                    value=bool(self._settings.get("respect_robots", True)),
                    id="set-robots",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.playwright_label"))
                yield Checkbox(
                    t("settings.playwright_checkbox"),
                    value=bool(self._settings.get("render", False)),
                    id="set-playwright",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.preview_label"))
                yield Checkbox(
                    t("settings.preview_checkbox"),
                    value=bool(self._settings.get("show_preview", False)),
                    id="set-preview",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.concurrency_label"))
                yield Input(
                    value=str(self._settings.get("concurrency", 8)),
                    type="integer",
                    id="set-concurrency",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.timeout_label"))
                yield Input(
                    value=str(self._settings.get("timeout", 30)),
                    type="integer",
                    id="set-timeout",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.max_depth_label"))
                yield Input(
                    value=str(self._settings.get("max_depth", 10)),
                    type="integer",
                    id="set-max-depth",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.max_retries_label"))
                yield Input(
                    value=str(self._settings.get("max_retries", 2)),
                    type="integer",
                    id="set-max-retries",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.no_headless_label"))
                yield Checkbox(
                    t("settings.no_headless_checkbox"),
                    value=bool(self._settings.get("no_headless", False)),
                    id="set-no-headless",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.user_agent_label"))
                yield Input(
                    value=str(self._settings.get("user_agent", "")),
                    placeholder=t("settings.user_agent_placeholder"),
                    id="set-user-agent",
                )
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.cookies_label"))
                yield Input(
                    value=str(self._settings.get("cookies", "")),
                    placeholder=t("settings.cookies_placeholder"),
                    id="set-cookies",
                )
            yield Static(t("settings.crawl_hint"), classes="settings-hint")

    def collect_app_settings(self, settings: dict[str, object]) -> None:
        """Schreibt die Crawl-Optionen aus den Widgets ins Ergebnis-Dict."""
        settings["respect_robots"] = self.query_one("#set-robots", Checkbox).value
        settings["render"] = self.query_one("#set-playwright", Checkbox).value
        settings["show_preview"] = self.query_one("#set-preview", Checkbox).value
        settings["concurrency"] = self._int("#set-concurrency", 8)
        settings["timeout"] = self._int("#set-timeout", 30)
        settings["max_depth"] = self._int("#set-max-depth", 10)
        settings["max_retries"] = self._int("#set-max-retries", 2, minimum=0)
        settings["no_headless"] = self.query_one("#set-no-headless", Checkbox).value
        settings["user_agent"] = self.query_one("#set-user-agent", Input).value.strip()
        settings["cookies"] = self.query_one("#set-cookies", Input).value.strip()

    def storage_paths(self) -> list[tuple[str, Path]]:
        """Liefert die Persistenz-Pfade fuer den Speicherort-Tab."""
        return [
            (t("settings.storage.config"), SETTINGS_FILE),
            (t("settings.storage.history"), History.HISTORY_FILE),
            (t("settings.storage.preview_cache"), PREVIEW_CACHE_DIR),
        ]

    def _int(self, selector: str, default: int, minimum: int = 1) -> int:
        """Liest einen Integer-Wert aus einem Input-Feld (mit Fallback).

        Args:
            selector: CSS-Selektor des Input-Felds.
            default: Rueckgabewert bei ungueltiger Eingabe.
            minimum: Untere Schranke (z.B. 0 fuer Retries, 1 fuer Anzahl-Felder).
        """
        try:
            return max(minimum, int(self.query_one(selector, Input).value))
        except (ValueError, TypeError):
            return default
