"""Tests fuer den JIRA-Tabellen-Export (Markdown fuer Cloud, Wiki fuer Server/DC)."""

from __future__ import annotations

import pytest

from sitemap_tracker.i18n import load_locale
from sitemap_tracker.models.crawl_result import CrawlResult, PageStatus
from sitemap_tracker.services.reporter import Reporter


@pytest.fixture(autouse=True)
def _german_locale() -> None:
    load_locale("de")


def _error(url: str, code: int = 404, referring: list[dict] | None = None) -> CrawlResult:
    # Der Fehlerfilter greift ueber http_status_code >= 400, Status bleibt OK.
    return CrawlResult(
        url=url,
        status=PageStatus.OK,
        http_status_code=code,
        referring_pages=referring or [],
    )


def test_no_errors_returns_empty() -> None:
    ok = CrawlResult(url="https://ex.com/a", status=PageStatus.OK, http_status_code=200)
    assert Reporter.generate_jira_table([ok], "https://ex.com") == ""


def test_markdown_is_default_with_separator_row() -> None:
    err = _error(
        "https://ex.com/tot",
        referring=[{"link_text": "Impressum", "url": "https://ex.com/imp"}],
    )
    out = Reporter.generate_jira_table([err], "https://ex.com").splitlines()
    # Header aus dem uebersetzten Wiki-Header abgeleitet + Trennzeile
    assert out[0].startswith("| URL | HTTP |")
    assert out[1] == "| --- | --- | --- | --- |"
    assert "https://ex.com/tot" in out[2]
    assert "404" in out[2]
    # Referring als echter Markdown-Link, mehrere mit <br> getrennt
    assert "[Impressum](https://ex.com/imp)" in out[2]


def test_markdown_escapes_pipe_in_cells() -> None:
    err = _error("https://ex.com/a|b", referring=[{"link_text": "x|y", "url": "https://ex.com/r"}])
    row = Reporter.generate_jira_table([err], "https://ex.com").splitlines()[2]
    assert "https://ex.com/a\\|b" in row
    assert "[x\\|y](https://ex.com/r)" in row


def test_wiki_format_uses_wiki_header_and_links() -> None:
    err = _error("https://ex.com/tot", referring=[{"link_text": "", "url": "https://ex.com/r"}])
    out = Reporter.generate_jira_table([err], "https://ex.com", fmt="wiki").splitlines()
    assert out[0].startswith("||URL||HTTP||")
    assert out[1].startswith("|[https://ex.com/tot]|404|")
    assert "[https://ex.com/r]" in out[1]


def test_fmt_is_case_insensitive() -> None:
    err = _error("https://ex.com/tot")
    assert Reporter.generate_jira_table([err], "https://ex.com", fmt="WIKI").startswith("||URL||")
    assert Reporter.generate_jira_table([err], "https://ex.com", fmt="Markdown").startswith("| URL |")
