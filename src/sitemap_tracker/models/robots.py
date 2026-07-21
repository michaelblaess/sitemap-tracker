"""robots.txt Parser - Prueft ob URLs gecrawlt werden duerfen."""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

import httpx


def _compile_pattern(pattern: str) -> re.Pattern[str]:
    """Uebersetzt ein robots-Pfadmuster in eine Regex.

    Der Standard (RFC 9309) kennt zwei Sonderzeichen: `*` fuer eine beliebige
    Zeichenfolge und `$` am Ende fuer "Pfad endet hier". Ohne diese Behandlung
    greifen reale Regeln nie - z.B. `Disallow: /*CR-Dokumentation.pdf$` von
    spiegel.de, weil kein Pfad buchstaeblich mit `/*CR-` beginnt.

    Args:
        pattern:
        Pfadmuster aus einer Disallow-/Allow-Zeile.

    Returns:
        Kompilierte Regex, die am Pfadanfang ankert.
    """
    anchored_end = pattern.endswith("$")
    raw = pattern[:-1] if anchored_end else pattern
    body = "".join(".*" if char == "*" else re.escape(char) for char in raw)
    return re.compile(f"^{body}$" if anchored_end else f"^{body}")


class RobotsChecker:
    """Laedt und parst robots.txt fuer eine Domain.

    Unterstuetzt Disallow/Allow-Regeln (inkl. `*`/`$`) und Sitemap-Eintraege.
    """

    def __init__(self) -> None:
        # (Musterlaenge, kompiliertes Muster, erlaubt) - die Laenge entscheidet,
        # welche Regel bei mehreren Treffern gewinnt (spezifischste zuerst).
        self._rules: list[tuple[int, re.Pattern[str], bool]] = []
        self._sitemaps: list[str] = []
        self._loaded = False

    async def load(
        self,
        base_url: str,
        cookies: list[dict[str, str]] | None = None,
        proxy: str = "",
    ) -> None:
        """Laedt robots.txt von der angegebenen Domain.

        Args:
            base_url: Basis-URL der Website.
            cookies: Optionale Cookies.
            proxy: Optionale Proxy-URL (Corporate-Proxy/Zscaler).
        """
        parsed = urlparse(base_url)
        robots_url = urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))

        jar = httpx.Cookies()
        for c in cookies or []:
            jar.set(c["name"], c["value"])

        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                follow_redirects=True,
                verify=False,
                cookies=jar,
                proxy=proxy.strip() or None,
            ) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    self._parse(response.text)
                    self._loaded = True
        except Exception:
            # robots.txt nicht erreichbar - alles erlaubt
            self._loaded = True

    def _parse(self, text: str) -> None:
        """Parst den robots.txt Inhalt.

        Beruecksichtigt nur den User-agent: * Block.

        Args:
            text: Inhalt der robots.txt.
        """
        in_wildcard_block = False
        in_specific_block = False

        for line in text.splitlines():
            line = line.strip()

            # Kommentare entfernen
            if "#" in line:
                line = line[: line.index("#")].strip()
            if not line:
                continue

            lower = line.lower()

            # User-agent Zeilen
            if lower.startswith("user-agent:"):
                agent = line[len("user-agent:") :].strip()
                if agent == "*":
                    in_wildcard_block = True
                    in_specific_block = False
                else:
                    in_wildcard_block = False
                    in_specific_block = True
                continue

            # Nur Wildcard-Block verarbeiten
            if not in_wildcard_block or in_specific_block:
                # Sitemap-Eintraege sind global
                if lower.startswith("sitemap:"):
                    url = line[len("sitemap:") :].strip()
                    if url:
                        self._sitemaps.append(url)
                continue

            # Disallow/Allow Regeln
            if lower.startswith("disallow:"):
                path = line[len("disallow:") :].strip()
                if path:  # "Disallow:" ohne Pfad heisst: alles erlaubt
                    self._rules.append((len(path), _compile_pattern(path), False))
            elif lower.startswith("allow:"):
                path = line[len("allow:") :].strip()
                if path:
                    self._rules.append((len(path), _compile_pattern(path), True))
            elif lower.startswith("sitemap:"):
                url = line[len("sitemap:") :].strip()
                if url:
                    self._sitemaps.append(url)

    def is_allowed(self, url: str) -> bool:
        """Prueft ob eine URL gecrawlt werden darf.

        Bei mehreren passenden Regeln gewinnt die laengste (spezifischste); bei
        gleicher Laenge gewinnt Allow - so schreibt es RFC 9309 vor.

        Args:
            url: Die zu pruefende URL.

        Returns:
            True wenn die URL laut robots.txt erlaubt ist.
        """
        if not self._rules:
            return True

        parsed = urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        best_length = -1
        allowed = True
        for length, pattern, rule_allows in self._rules:
            if not pattern.search(path):
                continue
            if length > best_length or (length == best_length and rule_allows):
                best_length = length
                allowed = rule_allows
        return allowed

    @property
    def sitemaps(self) -> list[str]:
        """Gibt die in robots.txt gefundenen Sitemap-URLs zurueck."""
        return self._sitemaps

    @property
    def is_loaded(self) -> bool:
        """Gibt zurueck ob robots.txt geladen wurde."""
        return self._loaded
