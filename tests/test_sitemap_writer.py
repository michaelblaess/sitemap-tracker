"""Tests fuer den SitemapWriter - inkl. Aufloesung von Redirect-Zielen.

Schwerpunkt ist der Alias-Sonderfall: ein Redirect (301/302) auf eine Seite,
die nicht selbst gecrawlt/gelistet ist, muss als aufgeloestes Ziel in die
Sitemap - aber nur dedupliziert und nur auf DEMSELBEN Host (eine sitemap.xml
ist laut Standard host-gebunden, Schwester-Subdomains gehoeren nicht hinein).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from sitemap_tracker.models.crawl_result import CrawlResult, PageStatus
from sitemap_tracker.models.sitemap_writer import SITEMAP_NS, SitemapWriter

_BASE = "https://www.blog.kunde.example/"


def _ok(url: str, depth: int = 1) -> CrawlResult:
    return CrawlResult(
        url=url,
        status=PageStatus.OK,
        http_status_code=200,
        content_type="text/html; charset=utf-8",
        depth=depth,
    )


def _redirect(url: str, target: str, external: bool = False) -> CrawlResult:
    return CrawlResult(
        url=url,
        status=PageStatus.REDIRECT_EXTERNAL if external else PageStatus.REDIRECT,
        http_status_code=301,
        content_type="text/html; charset=utf-8",
        depth=1,
        redirect_url=target,
    )


def _written_locs(results: list[CrawlResult], tmp_path: Path) -> tuple[list[str], SitemapWriter]:
    out = tmp_path / "sitemap.xml"
    writer = SitemapWriter(results, base_url=_BASE)
    writer.write(str(out))
    tree = ET.parse(out)
    locs = [el.text or "" for el in tree.getroot().findall(f"{{{SITEMAP_NS}}}url/{{{SITEMAP_NS}}}loc")]
    return locs, writer


class TestSitemapWriterBasics:
    def test_only_200_html_pages_written(self, tmp_path: Path) -> None:
        results = [
            _ok(_BASE),
            CrawlResult(url=f"{_BASE}404", status=PageStatus.ERROR, http_status_code=404),
        ]
        locs, _ = _written_locs(results, tmp_path)
        assert locs == [_BASE]

    def test_no_pages_returns_empty(self, tmp_path: Path) -> None:
        writer = SitemapWriter([], base_url=_BASE)
        assert writer.write(str(tmp_path / "sitemap.xml")) == []


class TestRedirectResolution:
    def test_internal_alias_target_is_added(self, tmp_path: Path) -> None:
        # Interner Alias: /old -> /new auf DEMSELBEN Host, /new nicht gelistet
        target = f"{_BASE}neue-seite"
        results = [
            _ok(_BASE),
            _redirect(f"{_BASE}alte-seite", target),
        ]
        locs, writer = _written_locs(results, tmp_path)
        assert target in locs
        assert writer.resolved_targets == [target]

    def test_cross_host_target_excluded(self, tmp_path: Path) -> None:
        # Schwester-Subdomain (gleiche registrierbare Domain kunde.example, aber
        # ANDERER Host) -> gehoert NICHT in die Sitemap von www.blog.kunde.example
        target = "https://www.kunde.example/bereich-a/tarife/produkte"
        results = [
            _ok(_BASE),
            _redirect(f"{_BASE}bereich-a/tarife/alt", target, external=True),
        ]
        locs, writer = _written_locs(results, tmp_path)
        assert target not in locs
        assert all("kunde.example/bereich-a" not in u for u in locs)
        assert writer.resolved_targets == []

    def test_shop_subdomain_target_excluded(self, tmp_path: Path) -> None:
        target = "https://www.shop.kunde.example/produkte"
        results = [
            _ok(_BASE),
            _redirect(f"{_BASE}shop", target, external=True),
        ]
        locs, writer = _written_locs(results, tmp_path)
        assert target not in locs
        assert writer.resolved_targets == []

    def test_redirect_target_already_listed_is_skipped(self, tmp_path: Path) -> None:
        # Interner Alias auf eine bereits gelistete 200-Seite -> kein Doppeleintrag
        listed = f"{_BASE}geraete"
        results = [
            _ok(_BASE),
            _ok(listed),
            _redirect(f"{_BASE}wp", listed),
        ]
        locs, writer = _written_locs(results, tmp_path)
        assert locs.count(listed) == 1
        assert writer.resolved_targets == []

    def test_multiple_internal_redirects_same_target_dedup(self, tmp_path: Path) -> None:
        target = f"{_BASE}ziel"
        results = [
            _ok(_BASE),
            _redirect(f"{_BASE}a", target),
            _redirect(f"{_BASE}b", target),
            _redirect(f"{_BASE}c", target),
        ]
        locs, writer = _written_locs(results, tmp_path)
        assert locs.count(target) == 1
        assert writer.resolved_targets == [target]

    def test_foreign_domain_target_is_not_added(self, tmp_path: Path) -> None:
        results = [
            _ok(_BASE),
            _redirect(f"{_BASE}go", "https://www.google.com/search", external=True),
        ]
        locs, writer = _written_locs(results, tmp_path)
        assert "https://www.google.com/search" not in locs
        assert writer.resolved_targets == []

    def test_empty_redirect_url_ignored(self, tmp_path: Path) -> None:
        results = [
            _ok(_BASE),
            _redirect(f"{_BASE}broken", ""),
        ]
        locs, writer = _written_locs(results, tmp_path)
        assert locs == [_BASE]
        assert writer.resolved_targets == []

    def test_plan_reports_total_and_resolved_counts(self, tmp_path: Path) -> None:
        target = f"{_BASE}intern-neu"
        results = [
            _ok(_BASE),
            _ok(f"{_BASE}geraete"),
            _redirect(f"{_BASE}a", target),  # interner Alias -> zaehlt
            _redirect(f"{_BASE}b", target),  # Dublette
            _redirect(f"{_BASE}x", "https://www.kunde.example/x", external=True),  # cross-host raus
            _redirect(f"{_BASE}go", "https://www.google.com/x", external=True),  # fremd raus
        ]
        writer = SitemapWriter(results, base_url=_BASE)
        total, resolved = writer.plan()
        # 2 direkte 200er + 1 interner Alias (Dublette + cross-host + fremd raus)
        assert total == 3
        assert resolved == 1

    def test_encoded_internal_aliases_dedup(self, tmp_path: Path) -> None:
        # Zwei Aliase (encoded vs. nicht) auf dasselbe interne Ziel -> ein Eintrag
        target_plain = f"{_BASE}geräte"
        target_encoded = f"{_BASE}ger%C3%A4te"
        results = [
            _ok(_BASE),
            _redirect(f"{_BASE}a", target_plain),
            _redirect(f"{_BASE}b", target_encoded),
        ]
        locs, writer = _written_locs(results, tmp_path)
        wp_locs = [u for u in locs if "geräte" in u or "ger%C3%A4te" in u]
        assert len(wp_locs) == 1
        assert len(writer.resolved_targets) == 1
