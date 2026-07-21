"""Tests fuer die robots.txt-Auswertung (Disallow/Allow inkl. Wildcards)."""

from __future__ import annotations

from sitemap_tracker.models.robots import RobotsChecker

_ROBOTS = """
# Kommentar wird ignoriert
User-agent: BadBot
Disallow: /

User-agent: *
Disallow: /intern/
Disallow: /suche
Allow: /intern/presse/
Sitemap: https://example.com/sitemap.xml
"""


def _checker(text: str) -> RobotsChecker:
    """Baut einen Checker direkt aus robots.txt-Text (ohne Netzwerk)."""
    checker = RobotsChecker()
    checker._parse(text)  # noqa: SLF001 - Parser gezielt ohne HTTP testen
    return checker


class TestRobotsChecker:
    def test_disallowed_path_blocked(self) -> None:
        assert _checker(_ROBOTS).is_allowed("https://example.com/intern/geheim") is False

    def test_allow_wins_over_shorter_disallow(self) -> None:
        """Laengere (spezifischere) Regel gewinnt - sonst waere die Presse gesperrt."""
        assert _checker(_ROBOTS).is_allowed("https://example.com/intern/presse/pm-1") is True

    def test_normal_page_allowed(self) -> None:
        assert _checker(_ROBOTS).is_allowed("https://example.com/produkte/strom") is True

    def test_other_agent_block_ignored(self) -> None:
        """Das `Disallow: /` von BadBot darf uns nicht treffen."""
        assert _checker(_ROBOTS).is_allowed("https://example.com/") is True

    def test_sitemaps_collected(self) -> None:
        assert _checker(_ROBOTS).sitemaps == ["https://example.com/sitemap.xml"]

    def test_no_rules_allows_everything(self) -> None:
        assert _checker("").is_allowed("https://example.com/intern/geheim") is True

    def test_empty_disallow_is_no_rule(self) -> None:
        """`Disallow:` ohne Pfad heisst ausdruecklich: alles erlaubt."""
        assert _checker("User-agent: *\nDisallow:\n").is_allowed("https://example.com/x") is True

    def test_wildcard_pattern(self) -> None:
        """`*` steht fuer eine beliebige Zeichenfolge (RFC 9309)."""
        checker = _checker("User-agent: *\nDisallow: /*/print\n")
        assert checker.is_allowed("https://example.com/news/print") is False
        assert checker.is_allowed("https://example.com/news/artikel") is True

    def test_end_anchor(self) -> None:
        """`$` verankert das Pfadende - echte Regel von spiegel.de."""
        checker = _checker("User-agent: *\nDisallow: /*CR-Dokumentation.pdf$\n")
        assert checker.is_allowed("https://example.com/a/CR-Dokumentation.pdf") is False
        assert checker.is_allowed("https://example.com/a/CR-Dokumentation.pdf.html") is True

    def test_allow_wins_on_equal_length(self) -> None:
        """Bei gleich langen Regeln gewinnt Allow (RFC 9309)."""
        checker = _checker("User-agent: *\nDisallow: /abc\nAllow: /abc\n")
        assert checker.is_allowed("https://example.com/abc") is True
