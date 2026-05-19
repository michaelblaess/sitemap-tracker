"""Tests fuer die Seiten-Analyse (Tech-Stack, SEO, HTTP-Details)."""

from __future__ import annotations

from bs4 import BeautifulSoup

from sitemap_generator.services.page_analysis import detect_tech, extract_http_details, extract_seo


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


class TestDetectTech:
    def test_generator_meta_wordpress(self) -> None:
        soup = _soup('<meta name="generator" content="WordPress 6.4">')
        assert "WordPress" in detect_tech(soup, {})

    def test_script_src_jquery(self) -> None:
        soup = _soup('<script src="/assets/jquery.min.js"></script>')
        assert "jQuery" in detect_tech(soup, {})

    def test_link_href_bootstrap(self) -> None:
        soup = _soup('<link rel="stylesheet" href="/css/bootstrap.css">')
        assert "Bootstrap" in detect_tech(soup, {})

    def test_server_header(self) -> None:
        assert "nginx" in detect_tech(_soup(""), {"server": "nginx/1.24.0"})

    def test_x_powered_by_php(self) -> None:
        assert "PHP" in detect_tech(_soup(""), {"x-powered-by": "PHP/8.2.1"})

    def test_no_duplicates(self) -> None:
        soup = _soup('<script src="jquery.js"></script><script src="jquery-ui.js"></script>')
        assert detect_tech(soup, {}).count("jQuery") == 1

    def test_empty_page(self) -> None:
        assert detect_tech(_soup("<html></html>"), {}) == []


class TestExtractSeo:
    def test_title_and_description(self) -> None:
        soup = _soup('<title>Hello</title><meta name="description" content="A page">')
        seo = extract_seo(soup)
        assert seo.title == "Hello"
        assert seo.description == "A page"

    def test_h1_count(self) -> None:
        assert extract_seo(_soup("<h1>A</h1><h1>B</h1>")).h1_count == 2

    def test_lang(self) -> None:
        assert extract_seo(_soup('<html lang="de"></html>')).lang == "de"

    def test_canonical(self) -> None:
        soup = _soup('<link rel="canonical" href="https://example.com/">')
        assert extract_seo(soup).canonical == "https://example.com/"

    def test_viewport_present(self) -> None:
        soup = _soup('<meta name="viewport" content="width=device-width">')
        assert extract_seo(soup).has_viewport is True

    def test_viewport_absent(self) -> None:
        assert extract_seo(_soup("")).has_viewport is False

    def test_og_tags(self) -> None:
        soup = _soup('<meta property="og:title" content="X"><meta property="og:image" content="i.png">')
        og = extract_seo(soup).og_tags
        assert "og:title" in og
        assert "og:image" in og
        assert "og:description" not in og


class TestExtractHttpDetails:
    def test_picks_interesting_headers(self) -> None:
        headers = {"server": "nginx", "content-encoding": "gzip", "x-secret": "hidden"}
        assert extract_http_details(headers) == {"server": "nginx", "content-encoding": "gzip"}

    def test_empty_when_nothing_interesting(self) -> None:
        assert extract_http_details({"x-foo": "bar"}) == {}

    def test_skips_empty_values(self) -> None:
        assert extract_http_details({"server": ""}) == {}
