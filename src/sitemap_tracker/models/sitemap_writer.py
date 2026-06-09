"""Sitemap-XML Generator - Erzeugt standardkonforme sitemap.xml Dateien."""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from xml.dom import minidom

from .crawl_result import CrawlResult, PageStatus
from .url_utils import normalize_url, same_host

# Max URLs pro Sitemap-Datei laut Standard
MAX_URLS_PER_SITEMAP = 50_000

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


class SitemapWriter:
    """Generiert sitemap.xml aus Crawl-Ergebnissen.

    Bei mehr als 50.000 URLs wird automatisch ein Sitemap-Index
    mit Teil-Sitemaps erstellt.
    """

    def __init__(self, results: list[CrawlResult], base_url: str = "") -> None:
        self._results = results
        self._base_url = base_url
        # URLs, die als aufgeloeste Redirect-Ziele ergaenzt wurden (Alias-Faelle).
        # Nach write() auslesbar, damit die UI die Anzahl melden kann.
        self.resolved_targets: list[str] = []

    def write(self, output_path: str) -> list[str]:
        """Schreibt die Sitemap-Datei(en).

        Args:
            output_path: Pfad fuer die Ausgabe-Datei (z.B. sitemap.xml).

        Returns:
            Liste der geschriebenen Dateien.
        """
        urls = self._collect_urls()

        if not urls:
            return []

        if len(urls) <= MAX_URLS_PER_SITEMAP:
            self._write_single(urls, output_path)
            return [output_path]

        return self._write_index(urls, output_path)

    def plan(self) -> tuple[int, int]:
        """Berechnet die Sitemap-Zusammensetzung, ohne eine Datei zu schreiben.

        Nuetzlich fuer die Crawl-Zusammenfassung, die die Kennzahlen anzeigen
        will, bevor (oder ohne dass) der Nutzer exportiert.

        Returns:
            Tuple ``(gesamt_urls, aufgeloeste_redirect_ziele)``.
        """
        urls = self._collect_urls()
        return len(urls), len(self.resolved_targets)

    def _collect_urls(self) -> list[CrawlResult]:
        """Stellt die Liste der Sitemap-URLs zusammen.

        Zwei Quellen:
        1. Direkt gecrawlte HTTP-200-HTML-Seiten (die Standard-Sitemap-URLs).
        2. Aufgeloeste Redirect-Ziele (Alias-Fall): Zeigt ein Redirect (301/302)
           auf eine Seite, die NICHT bereits unter (1) erfasst ist, wird das
           Ziel in die Sitemap aufgenommen. Sonst fielen Seiten durchs Raster,
           die nur ueber einen Alias erreichbar sind (z.B.
           ``/tarife/alt`` -> ``www.kunde.example/.../Produkte``).

        Deduplizierung und Host-Scope:
        - Ein Ziel, das schon als 200-Seite gelistet ist (interner Alias auf
          eine bekannte Seite), wird verworfen - es wuerde sonst doppelt
          gescannt.
        - Mehrere Redirects auf dasselbe Ziel ergeben nur EINEN Eintrag.
        - Nur Ziele auf demselben Host werden aufgenommen. Eine sitemap.xml
          darf laut Standard nur URLs desselben Hosts enthalten - Redirects auf
          Schwester-Subdomains (z.B. www.kunde.example, shop.kunde.example) oder
          fremde Domains gehoeren NICHT hinein und werden uebersprungen.

        Returns:
            Liste der Sitemap-Eintraege als CrawlResult (inkl. synthetischer
            Eintraege fuer aufgeloeste Redirect-Ziele).
        """
        self.resolved_targets = []

        # 1) Direkt gecrawlte 200-OK-HTML-Seiten
        direct = [r for r in self._results if r.http_status_code == 200 and self._is_html(r)]
        seen = {normalize_url(r.url) for r in direct}
        urls = list(direct)

        base_host = urlparse(self._base_url).netloc if self._base_url else ""

        # 2) Aufgeloeste Redirect-Ziele ergaenzen
        for result in self._results:
            if result.status not in (PageStatus.REDIRECT, PageStatus.REDIRECT_EXTERNAL):
                continue
            target = result.redirect_url.strip()
            if not target:
                continue

            norm = normalize_url(target)
            if norm in seen:
                continue  # schon abgedeckt oder Dublette

            # Host-Scope: nur Ziele auf demselben Host (sitemap.xml ist
            # per Standard host-gebunden - keine Schwester-Subdomains)
            if base_host and not same_host(base_host, urlparse(target).netloc):
                continue

            seen.add(norm)
            self.resolved_targets.append(target)
            urls.append(self._synthetic_target(target, result))

        return urls

    @staticmethod
    def _synthetic_target(target: str, redirect: CrawlResult) -> CrawlResult:
        """Erzeugt einen Sitemap-Eintrag fuer ein aufgeloestes Redirect-Ziel.

        Das Ziel wurde selbst nicht gecrawlt (es existiert nur als
        ``redirect_url`` am 301-Eintrag). Daher wird kein ``last_modified``
        gesetzt - das des Redirects gehoert zur Weiterleitung, nicht zum Ziel.
        Die Crawl-Tiefe des Redirects wird fuer die Priority uebernommen.

        Args:
            target:
                Die Ziel-URL.
            redirect:
                Das urspruengliche Redirect-Ergebnis.

        Returns:
            Synthetisches CrawlResult fuer die Sitemap.
        """
        return CrawlResult(
            url=target,
            http_status_code=200,
            content_type="text/html",
            depth=redirect.depth,
        )

    def _write_single(self, urls: list[CrawlResult], path: str) -> None:
        """Schreibt eine einzelne sitemap.xml.

        Args:
            urls: Liste der URLs.
            path: Ausgabe-Pfad.
        """
        root = ET.Element("urlset")
        root.set("xmlns", SITEMAP_NS)

        for result in urls:
            url_elem = ET.SubElement(root, "url")

            loc = ET.SubElement(url_elem, "loc")
            loc.text = result.url

            if result.last_modified:
                lastmod = ET.SubElement(url_elem, "lastmod")
                lastmod.text = result.last_modified

            # Priority basierend auf Crawl-Tiefe schaetzen
            priority = ET.SubElement(url_elem, "priority")
            priority.text = self._estimate_priority(result.depth)

        self._write_pretty_xml(root, path)

    def _write_index(self, urls: list[CrawlResult], path: str) -> list[str]:
        """Schreibt einen Sitemap-Index mit Teil-Sitemaps.

        Args:
            urls: Liste aller URLs.
            path: Basis-Pfad (z.B. sitemap.xml -> sitemap-1.xml, sitemap-2.xml, ...).

        Returns:
            Liste aller geschriebenen Dateien.
        """
        base, ext = os.path.splitext(path)
        written_files: list[str] = []

        # Teil-Sitemaps schreiben
        chunks = [urls[i : i + MAX_URLS_PER_SITEMAP] for i in range(0, len(urls), MAX_URLS_PER_SITEMAP)]
        for idx, chunk in enumerate(chunks, 1):
            part_path = f"{base}-{idx}{ext}"
            self._write_single(chunk, part_path)
            written_files.append(part_path)

        # Sitemap-Index schreiben
        root = ET.Element("sitemapindex")
        root.set("xmlns", SITEMAP_NS)

        for part_path in written_files:
            sitemap_elem = ET.SubElement(root, "sitemap")
            loc = ET.SubElement(sitemap_elem, "loc")
            # Relativer Dateiname
            loc.text = os.path.basename(part_path)

        self._write_pretty_xml(root, path)
        written_files.insert(0, path)

        return written_files

    @staticmethod
    def _estimate_priority(depth: int) -> str:
        """Schaetzt die Priority basierend auf der Crawl-Tiefe.

        Tiefe 0 (Startseite) = 1.0, Tiefe 1 = 0.8, Tiefe 2 = 0.6, etc.
        Minimum: 0.1

        Args:
            depth: Crawl-Tiefe der Seite.

        Returns:
            Priority als String (z.B. "0.8").
        """
        priority = max(0.1, 1.0 - (depth * 0.2))
        return f"{priority:.1f}"

    @staticmethod
    def _is_html(result: CrawlResult) -> bool:
        """Prueft ob ein Ergebnis eine HTML-Seite ist.

        Args:
            result: Das Crawl-Ergebnis.

        Returns:
            True wenn Content-Type text/html enthaelt.
        """
        ct = result.content_type.lower()
        return "text/html" in ct or not ct

    @staticmethod
    def _write_pretty_xml(root: ET.Element, path: str) -> None:
        """Schreibt ein XML-Element huebsch formatiert in eine Datei.

        Args:
            root: XML Root-Element.
            path: Ausgabe-Pfad.
        """
        rough = ET.tostring(root, encoding="unicode", xml_declaration=False)
        pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="UTF-8")

        with open(path, "wb") as f:
            f.write(pretty)
