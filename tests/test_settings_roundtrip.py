"""Regression: Crawl-Einstellungen ueberleben Speichern + erneutes Oeffnen.

Deckt den Bug ab, bei dem der Settings-Dialog Felder zwar schreibt
(``collect_app_settings``), die App sie aber weder in den Dialog hineinreicht
(``action_show_settings`` -> ``current``-Dict) noch aus dem Ergebnis zurueck in
die persistierten Einstellungen uebernimmt (``_on_settings_closed``). Folge:
Dialog zeigt beim Oeffnen Defaults statt der gespeicherten Werte, und eine
Aenderung springt nach dem Speichern zurueck.

Betroffen waren ``jira_format`` (Export-Tab) und - seit v2.9.0 - die
Drossel-Einstellung (``rate_limit_enabled``). Der reine ``to_dict()``-Roundtrip
in test_safe_defaults deckt das NICHT ab, weil er das App-Mapping ueberspringt.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.widgets import Checkbox, Select

from sitemap_tracker import app as app_module
from sitemap_tracker.app import SitemapTrackerApp
from sitemap_tracker.i18n import load_locale
from sitemap_tracker.models import settings as settings_module
from sitemap_tracker.models.settings import Settings


@pytest.fixture
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Verlegt die settings.json nach tmp_path und ueberspringt den Disclaimer."""
    settings_file = tmp_path / "settings.json"
    monkeypatch.setattr(settings_module, "SETTINGS_DIR", tmp_path)
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(app_module, "SETTINGS_FILE", settings_file)
    monkeypatch.setattr(SitemapTrackerApp, "_ask_disclaimer", lambda self: None)
    load_locale("de")
    return settings_file


async def test_jira_format_and_rate_survive_save_and_reopen(isolated_settings: Path) -> None:
    app = SitemapTrackerApp(start_url="https://example.com")
    async with app.run_test() as pilot:
        app.action_show_settings()
        await pilot.pause()
        app.screen.query_one("#set-jira-format", Select).value = "wiki"
        app.screen.query_one("#set-rate-on", Checkbox).value = False
        await pilot.pause()
        await pilot.press("ctrl+s")
        await pilot.pause()

        # Erneut oeffnen: der Dialog muss den gespeicherten Zustand zeigen
        # (deckt die fehlenden Keys im current-Dict ab).
        app.action_show_settings()
        await pilot.pause()
        assert app.screen.query_one("#set-jira-format", Select).value == "wiki"
        assert app.screen.query_one("#set-rate-on", Checkbox).value is False

    # Und auf der Platte gelandet (deckt das fehlende Mapping in
    # _on_settings_closed ab).
    reloaded = Settings.load()
    assert reloaded.jira_format == "wiki"
    assert reloaded.rate_limit_enabled is False
