"""Persistente Einstellungen fuer den Sitemap Tracker."""

from __future__ import annotations

import contextlib
import json
import locale
import os
from pathlib import Path

# Einstellungsdatei im User-Verzeichnis.
# Hinweis: bis v1.x lag das Verzeichnis unter ``~/.sitemap-generator/`` —
# die einmalige Kopier-Migration laeuft beim App-Start in ``__main__.py``.
SETTINGS_DIR = Path.home() / ".sitemap-tracker"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


def detect_language() -> str:
    """Leitet die Startsprache aus der Systemumgebung ab.

    Nur beim allerersten Start relevant - danach steht die Sprache in den
    Einstellungen. Ohne diese Ableitung bekaeme jeder Nutzer weltweit eine
    deutsche Oberflaeche und einen deutschen Haftungshinweis, obwohl das
    Projekt englischsprachig dokumentiert ist.

    Deutsch wird nur bei einer nachweislich deutschsprachigen Umgebung gewaehlt.
    Jeder andere Fall - unbekannte Sprache, leere Umgebung oder ein Fehler beim
    Auslesen (locale.getlocale() wirft auf manchen Systemen) - fuehrt zu
    Englisch: die Sprache, in der das Projekt dokumentiert ist.

    Returns:
        "de" fuer eine deutschsprachige Umgebung, sonst immer "en".
    """
    code = ""
    with contextlib.suppress(Exception):
        code = locale.getlocale()[0] or ""
    if not code:
        with contextlib.suppress(Exception):
            code = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    return "de" if code.lower().startswith("de") else "en"


# textual-themes 0.5 hat 25 Themes umbenannt (trademark-safety pass).
# Settings-Files aelterer Versionen koennen alte Slugs gespeichert
# haben — die werden beim Laden transparent gemappt.
_LEGACY_THEME_MAP: dict[str, str] = {
    "c64": "brotkasten",
    "amiga": "boing",
    "atari-st": "gemstone",
    "ibm-terminal": "classic-terminal",
    "nextstep": "next",
    "beos": "bebox",
    "ubuntu": "bunty",
    "macos": "cupertino",
    "windows-xp": "luna",
    "msdos": "commandr",
    "solaris-cde": "motif",
    "os2-warp": "warp",
    "opensuse": "geeko",
    "linux-mint": "minty",
    "red-hat": "crimson",
    "raspberry-pi": "razzy",
    "freebsd": "beastie",
    "tudor": "fifty-eight",
    "goldfinger": "goldfinder",
    "hulk": "hulkula",
    "batman": "flughund",
    "gameboy": "brick",
    "pan-am": "clipper",
    "miami-vice": "miami",
    "martini-racing": "racing",
    "superman": "metropolis",
    "spiderman": "spiderized",
    "gulf-racing": "textual-dark",  # entferntes Theme -> Textual Default
}


class Settings:
    """Persistente Einstellungen (Theme etc.)."""

    def __init__(self) -> None:
        self.theme: str = "textual-dark"
        self.respect_robots: bool = True
        self.render: bool = False
        # Erststart: Sprache aus der Systemumgebung, danach aus der Datei.
        self.language: str = detect_language()
        self.concurrency: int = 8
        # Requests pro Minute; 0 = ungebremst. Voreingestellt gedrosselt, weil
        # ein Crawl sonst mehrere hundert Requests pro Minute erzeugen kann.
        self.rate_limit_enabled: bool = True
        self.rate_per_minute: int = 60
        self.timeout: int = 30
        self.max_depth: int = 10
        # Wiederholungen bei Verbindungsproblemen (zusaetzlich zum 1. Versuch).
        self.max_retries: int = 2
        self.show_preview: bool = False
        # Sichtbarer Browser (Debugging) — entspricht CLI --no-headless.
        self.no_headless: bool = False
        # Leer = eingebauter Chrome-131-User-Agent des Crawlers.
        self.user_agent: str = ""
        # Roh-String "name=value, name2=value2" — Parsing via parse_cookies().
        self.cookies: str = ""
        # Optionaler Corporate-Proxy (Zscaler) "http://host:port" fuer httpx
        # UND den Playwright-Browser. Leer = kein expliziter Proxy.
        self.proxy_url: str = ""
        # JIRA-Export-Format: "markdown" fuer Jira Cloud (Paste-Konvertierung),
        # "wiki" fuer Jira Server/Data Center (klassisches Wiki Markup).
        self.jira_format: str = "markdown"

    def save(self) -> None:
        """Speichert die Einstellungen in eine JSON-Datei."""
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "theme": self.theme,
            "respect_robots": self.respect_robots,
            "render": self.render,
            "language": self.language,
            "concurrency": self.concurrency,
            "rate_limit_enabled": self.rate_limit_enabled,
            "rate_per_minute": self.rate_per_minute,
            "timeout": self.timeout,
            "max_depth": self.max_depth,
            "max_retries": self.max_retries,
            "show_preview": self.show_preview,
            "no_headless": self.no_headless,
            "user_agent": self.user_agent,
            "cookies": self.cookies,
            "proxy_url": self.proxy_url,
            "jira_format": self.jira_format,
        }
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> Settings:
        """Laedt die Einstellungen oder gibt Defaults zurueck.

        Migriert dabei alte Theme-Slugs aus textual-themes < 0.5 auf
        ihre aktuellen Namen und persistiert die Migration.

        Returns:
            Settings-Instanz.
        """
        settings = cls()
        if SETTINGS_FILE.is_file():
            try:
                data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
                settings.theme = data.get("theme", settings.theme)
                settings.respect_robots = data.get("respect_robots", settings.respect_robots)
                settings.render = data.get("render", settings.render)
                settings.language = data.get("language", settings.language)
                settings.concurrency = int(data.get("concurrency", settings.concurrency))
                settings.rate_limit_enabled = bool(data.get("rate_limit_enabled", settings.rate_limit_enabled))
                settings.rate_per_minute = int(data.get("rate_per_minute", settings.rate_per_minute))
                settings.timeout = int(data.get("timeout", settings.timeout))
                settings.max_depth = int(data.get("max_depth", settings.max_depth))
                settings.max_retries = int(data.get("max_retries", settings.max_retries))
                settings.show_preview = bool(data.get("show_preview", settings.show_preview))
                settings.no_headless = bool(data.get("no_headless", settings.no_headless))
                settings.user_agent = str(data.get("user_agent", settings.user_agent))
                settings.cookies = str(data.get("cookies", settings.cookies))
                settings.proxy_url = str(data.get("proxy_url", settings.proxy_url))
                jira_format = str(data.get("jira_format", settings.jira_format))
                settings.jira_format = jira_format if jira_format == "wiki" else "markdown"
            except Exception:
                pass

        # Legacy-Theme-Slug migrieren
        if settings.theme in _LEGACY_THEME_MAP:
            settings.theme = _LEGACY_THEME_MAP[settings.theme]
            with contextlib.suppress(Exception):
                settings.save()

        return settings


def parse_cookies(raw: str) -> list[dict[str, str]]:
    """Zerlegt einen Cookie-String in eine Liste von Cookie-Dicts.

    Format: ``name=value, name2=value2`` (Komma-getrennt). Eintraege ohne
    ``=`` werden ignoriert.

    Args:
        raw:
            Roh-String, wie er in den Settings gespeichert ist.

    Returns:
        Liste von ``{"name": ..., "value": ...}``-Dicts (ggf. leer).
    """
    if not raw or not raw.strip():
        return []
    cookies: list[dict[str, str]] = []
    for part in raw.split(","):
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip()
        if name:
            cookies.append({"name": name, "value": value.strip()})
    return cookies
