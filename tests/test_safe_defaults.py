"""Sichert die schonenden Vorgabewerte ab.

Diese Tests halten die Zusicherung fest, dass ein Crawl ohne weitere Angaben
gedrosselt ist und robots.txt beachtet. Wird ein Vorgabewert versehentlich auf
"ungebremst" gesetzt, schlagen sie fehl.
"""

from __future__ import annotations

import locale
from pathlib import Path

from sitemap_tracker.models.settings import Settings, detect_language
from sitemap_tracker.services.crawler import Crawler
from sitemap_tracker.services.rate_limit import RateLimiter


class TestSafeDefaults:
    def test_crawler_is_throttled_by_default(self) -> None:
        assert Crawler(start_url="https://example.com").rate_per_minute == 60

    def test_crawler_limiter_is_active_by_default(self) -> None:
        assert RateLimiter(Crawler(start_url="https://example.com").rate_per_minute).enabled is True

    def test_settings_enable_the_rate_limit(self) -> None:
        assert Settings().rate_limit_enabled is True

    def test_settings_default_rate(self) -> None:
        assert Settings().rate_per_minute == 60

    def test_robots_is_respected_by_default(self) -> None:
        assert Settings().respect_robots is True

    def test_rate_settings_survive_a_roundtrip(self, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """Die Werte muessen Speichern und Laden ueberstehen.

        Ohne diesen Weg bliebe unbemerkt, wenn save() oder load() einen der
        beiden Schluessel nicht kennt - die Einstellung waere dann nach einem
        Neustart wieder auf dem Standardwert.
        """
        from sitemap_tracker.models import settings as settings_module

        monkeypatch.setattr(settings_module, "SETTINGS_DIR", tmp_path)
        monkeypatch.setattr(settings_module, "SETTINGS_FILE", tmp_path / "settings.json")

        original = Settings()
        original.rate_per_minute = 20
        original.rate_limit_enabled = False
        original.save()

        loaded = Settings.load()
        assert loaded.rate_per_minute == 20
        assert loaded.rate_limit_enabled is False


class TestLanguageDetection:
    """Beim Erststart soll niemand einen Rechtstext in einer fremden Sprache sehen."""

    def test_german_environment(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(locale, "getlocale", lambda *a: ("de_DE", "UTF-8"))
        assert detect_language() == "de"

    def test_austrian_environment_is_german_too(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(locale, "getlocale", lambda *a: ("de_AT", "UTF-8"))
        assert detect_language() == "de"

    def test_english_environment(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(locale, "getlocale", lambda *a: ("en_US", "UTF-8"))
        assert detect_language() == "en"

    def test_other_language_falls_back_to_english(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(locale, "getlocale", lambda *a: ("pt_BR", "UTF-8"))
        assert detect_language() == "en"

    def test_env_variable_is_used_when_locale_is_empty(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.setattr(locale, "getlocale", lambda *a: (None, None))
        monkeypatch.delenv("LC_ALL", raising=False)
        monkeypatch.setenv("LANG", "de_DE.UTF-8")
        assert detect_language() == "de"

    def test_broken_locale_does_not_crash(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        """locale.getlocale() wirft auf manchen Systemen ValueError."""

        def boom(*args: object) -> tuple[str, str]:
            raise ValueError("unknown locale")

        monkeypatch.setattr(locale, "getlocale", boom)
        monkeypatch.delenv("LC_ALL", raising=False)
        monkeypatch.delenv("LANG", raising=False)
        assert detect_language() == "en"
