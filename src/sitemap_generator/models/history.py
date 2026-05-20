"""History-Modell fuer Sitemap Generator.

Speichert und laedt vergangene Crawl-Konfigurationen aus
~/.sitemap-generator/history.json.
"""

from __future__ import annotations

import getpass
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class HistoryEntry:
    """Einzelner Eintrag in der Crawl-History.

    Speichert alle Parameter eines Crawls, damit dieser
    spaeter wiederholt werden kann.

    Attributes:
        url: Start-URL des Crawls.
        timestamp: Zeitstempel im ISO-Format.
        user: Benutzername zum Zeitpunkt des Crawls.
        max_depth: Maximale Crawl-Tiefe.
        concurrency: Parallele Anfragen.
        timeout: Timeout pro Seite in Sekunden.
        render: True=Playwright-Rendering, False=httpx.
        respect_robots: True=robots.txt beachten.
        user_agent: Custom User-Agent oder leer.
        cookies: Liste der Cookies als Dicts.
        total_crawled: Anzahl gecrawlter URLs (nach Crawl-Ende).
        total_2xx: Anzahl 2xx-Responses.
        total_3xx: Anzahl 3xx-Responses (Redirects).
        total_4xx: Anzahl 4xx-Responses.
        total_5xx: Anzahl 5xx-Responses.
    """

    url: str
    timestamp: str = ""
    user: str = ""
    max_depth: int = 10
    concurrency: int = 8
    timeout: int = 30
    render: bool = False
    respect_robots: bool = True
    user_agent: str = ""
    cookies: list[dict[str, str]] = field(default_factory=list)
    total_crawled: int = 0
    total_2xx: int = 0
    total_3xx: int = 0
    total_4xx: int = 0
    total_5xx: int = 0

    def to_dict(self) -> dict:
        """Konvertiert den Eintrag in ein Dictionary fuer JSON.

        Returns:
            Dictionary mit allen Feldern.
        """
        return {
            "url": self.url,
            "timestamp": self.timestamp,
            "user": self.user,
            "max_depth": self.max_depth,
            "concurrency": self.concurrency,
            "timeout": self.timeout,
            "render": self.render,
            "respect_robots": self.respect_robots,
            "user_agent": self.user_agent,
            "cookies": self.cookies,
            "total_crawled": self.total_crawled,
            "total_2xx": self.total_2xx,
            "total_3xx": self.total_3xx,
            "total_4xx": self.total_4xx,
            "total_5xx": self.total_5xx,
        }

    @staticmethod
    def from_dict(data: dict) -> HistoryEntry:
        """Erstellt einen HistoryEntry aus einem Dictionary.

        Args:
            data: Dictionary mit den Feldern des Eintrags.

        Returns:
            Neuer HistoryEntry.
        """
        return HistoryEntry(
            url=data.get("url", ""),
            timestamp=data.get("timestamp", ""),
            user=data.get("user", ""),
            max_depth=data.get("max_depth", 10),
            concurrency=data.get("concurrency", 8),
            timeout=data.get("timeout", 30),
            render=data.get("render", False),
            respect_robots=data.get("respect_robots", True),
            user_agent=data.get("user_agent", ""),
            cookies=data.get("cookies", []),
            total_crawled=int(data.get("total_crawled", 0)),
            total_2xx=int(data.get("total_2xx", 0)),
            total_3xx=int(data.get("total_3xx", 0)),
            total_4xx=int(data.get("total_4xx", 0)),
            total_5xx=int(data.get("total_5xx", 0)),
        )

    def display_label(self) -> str:
        """Erzeugt ein kompaktes Label fuer die Anzeige in der History-Liste.

        Format: "2026-02-13 14:30 | www.example.com | --render | --ignore-robots"

        Returns:
            Kurzform-String fuer die Listenanzeige.
        """
        # Datum culture-abhaengig formatieren (de: TT.MM.JJJJ, en: ISO)
        from ..i18n import format_datetime

        date_part = format_datetime(self.timestamp)

        # Hostname extrahieren
        try:
            host = urlparse(self.url).hostname or self.url
        except Exception:
            host = self.url

        parts = [date_part, host]

        if self.render:
            parts.append("--render")

        if not self.respect_robots:
            parts.append("--ignore-robots")

        if self.concurrency != 8:
            parts.append(f"-c {self.concurrency}")

        if self.timeout != 30:
            parts.append(f"-t {self.timeout}")

        if self.cookies:
            cookie_names = ", ".join(c.get("name", "?") for c in self.cookies)
            parts.append(f"--cookie {cookie_names}")

        if self.user_agent:
            parts.append("--user-agent ...")

        return " | ".join(parts)


class History:
    """Verwaltet die Crawl-History in ~/.sitemap-generator/history.json.

    Stellt statische Methoden zum Laden, Speichern und Hinzufuegen
    von History-Eintraegen bereit.
    """

    HISTORY_DIR = Path.home() / ".sitemap-generator"
    HISTORY_FILE = HISTORY_DIR / "history.json"
    MAX_ENTRIES = 50

    @staticmethod
    def load() -> list[HistoryEntry]:
        """Laedt die History aus der JSON-Datei.

        Gibt eine leere Liste zurueck bei Fehler oder fehlender Datei.

        Returns:
            Liste der HistoryEntry-Objekte (neueste zuerst).
        """
        if not History.HISTORY_FILE.is_file():
            return []

        try:
            raw = History.HISTORY_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, list):
                return []
            return [HistoryEntry.from_dict(item) for item in data]
        except Exception as exc:
            logger.warning("History konnte nicht geladen werden: %s", exc)
            return []

    @staticmethod
    def save(entries: list[HistoryEntry]) -> None:
        """Speichert die History in die JSON-Datei.

        Erstellt das Verzeichnis falls es nicht existiert.

        Args:
            entries: Liste der HistoryEntry-Objekte.
        """
        try:
            History.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            data = [entry.to_dict() for entry in entries]
            History.HISTORY_FILE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("History konnte nicht gespeichert werden: %s", exc)

    @staticmethod
    def add(entry: HistoryEntry) -> None:
        """Fuegt einen neuen Eintrag an den Anfang der History hinzu.

        Laedt die aktuelle History, stellt den neuen Eintrag voran,
        kuerzt auf MAX_ENTRIES und speichert.

        Args:
            entry: Der neue HistoryEntry.
        """
        # Timestamp und User setzen falls nicht vorhanden
        if not entry.timestamp:
            entry.timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        if not entry.user:
            try:
                entry.user = getpass.getuser()
            except Exception:
                entry.user = "unknown"

        entries = History.load()
        entries.insert(0, entry)

        # Auf Maximum kuerzen
        if len(entries) > History.MAX_ENTRIES:
            entries = entries[: History.MAX_ENTRIES]

        History.save(entries)

    @staticmethod
    def update_latest_stats(
        total_crawled: int,
        total_2xx: int,
        total_3xx: int,
        total_4xx: int,
        total_5xx: int,
    ) -> None:
        """Aktualisiert die Statistik-Felder des juengsten Eintrags.

        Wird am Ende eines Crawls aufgerufen, wenn die Stats feststehen.
        Der zugehoerige Eintrag wurde bei Crawl-Start via `add()` an Index 0
        gelegt; abgebrochene Crawls behalten ihre Default-Stats (0).

        Args:
            total_crawled: Gesamtzahl gecrawlter URLs.
            total_2xx: Anzahl 2xx-Responses.
            total_3xx: Anzahl 3xx-Responses.
            total_4xx: Anzahl 4xx-Responses.
            total_5xx: Anzahl 5xx-Responses.
        """
        entries = History.load()
        if not entries:
            return
        latest = entries[0]
        latest.total_crawled = total_crawled
        latest.total_2xx = total_2xx
        latest.total_3xx = total_3xx
        latest.total_4xx = total_4xx
        latest.total_5xx = total_5xx
        History.save(entries)
