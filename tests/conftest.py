"""Gemeinsame Test-Vorbereitung.

**Kein Test darf in das echte Benutzerverzeichnis schreiben.** Die App legt
Verlauf, Einstellungen und Vorschau-Bilder unter ``~/.sitemap-tracker`` ab.
Ein Test, der die App hochfaehrt und einen Crawl anstoesst, traegt sonst
Wegwerf-Laeufe in den Verlauf des Anwenders ein - genau das ist am 03.08.2026
passiert (17 Eintraege "example.invalid" in einer echten Crawl-History).

Das blosse Umbiegen von ``USERPROFILE``/``HOME`` genuegt hier NICHT: die Pfade
stehen als Modul- und Klassenkonstanten fest und werden beim Import einmal aus
``Path.home()`` berechnet. Sie muessen deshalb einzeln umgehaengt werden.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sitemap_tracker import app as app_module
from sitemap_tracker.models import history as history_module
from sitemap_tracker.models import settings as settings_module
from sitemap_tracker.services import preview_service as preview_module


@pytest.fixture(autouse=True)
def _isolated_home(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Verlegt Verlauf, Einstellungen und Vorschau-Cache in ein Wegwerf-Verzeichnis.

    Bewusst ueber ``tmp_path_factory`` und NICHT unter ``tmp_path``: Letzteres
    gehoert dem einzelnen Test, und mindestens einer prueft, dass sein
    Verzeichnis leer bleibt.
    """
    home = tmp_path_factory.mktemp("home")

    # Zur Laufzeit gelesene Pfade (z.B. das Ausgabeverzeichnis).
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("HOME", str(home))

    # Beim Import berechnete Konstanten.
    monkeypatch.setattr(history_module.History, "HISTORY_DIR", home)
    monkeypatch.setattr(history_module.History, "HISTORY_FILE", home / "history.json")
    monkeypatch.setattr(settings_module, "SETTINGS_DIR", home)
    monkeypatch.setattr(settings_module, "SETTINGS_FILE", home / "settings.json")
    monkeypatch.setattr(app_module, "SETTINGS_FILE", home / "settings.json")
    monkeypatch.setattr(preview_module, "CACHE_DIR", home / "preview-cache")
    return home
