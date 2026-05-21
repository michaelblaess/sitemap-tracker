"""Analyse einer gecrawlten Seite: Tech-Stack, SEO-Daten, HTTP-Details.

Alle Funktionen arbeiten ausschliesslich mit Daten, die der Crawler ohnehin
schon geladen hat (geparstes HTML + Response-Header) - kein zusaetzlicher
Request noetig.
"""

from __future__ import annotations

from bs4 import BeautifulSoup
from bs4.element import Tag

from ..i18n import t
from ..models.crawl_result import CrawlResult, SeoInfo

# Marker, die in Script-/Link-URLs (oder im Generator-Meta) auf eine
# Technologie hindeuten. (Suchbegriff in Kleinbuchstaben, Anzeigename).
_URL_MARKERS: list[tuple[str, str]] = [
    ("jquery", "jQuery"),
    ("bootstrap", "Bootstrap"),
    ("tailwind", "Tailwind CSS"),
    ("react", "React"),
    ("vue", "Vue.js"),
    ("angular", "Angular"),
    ("svelte", "Svelte"),
    ("htmx", "htmx"),
    ("alpine", "Alpine.js"),
    ("wp-content", "WordPress"),
    ("wp-includes", "WordPress"),
    ("googletagmanager.com", "Google Tag Manager"),
    ("google-analytics.com", "Google Analytics"),
    ("gtag/js", "Google Analytics"),
    ("matomo", "Matomo"),
    ("piwik", "Matomo"),
    ("fontawesome", "Font Awesome"),
    ("cdn.jsdelivr.net", "jsDelivr CDN"),
    ("cdnjs.cloudflare.com", "cdnjs"),
]

# Marker im Generator-Meta-Tag -> CMS / Generator.
_GENERATOR_MARKERS: list[tuple[str, str]] = [
    ("wordpress", "WordPress"),
    ("sitefinity", "Sitefinity"),
    ("typo3", "TYPO3"),
    ("drupal", "Drupal"),
    ("joomla", "Joomla"),
    ("hugo", "Hugo"),
    ("gatsby", "Gatsby"),
    ("jekyll", "Jekyll"),
    ("wix", "Wix"),
    ("squarespace", "Squarespace"),
    ("shopify", "Shopify"),
    ("webflow", "Webflow"),
]

# HTTP-Header, die im Detail-Panel angezeigt werden (Schluessel kleingeschrieben).
_INTERESTING_HEADERS: list[str] = [
    "server",
    "x-powered-by",
    "content-encoding",
    "cache-control",
    "etag",
    "age",
    "x-cache",
    "via",
]


def _attr(tag: Tag | None, name: str) -> str:
    """Liest ein Attribut eines Tags als String aus (leer wenn nicht vorhanden)."""
    if tag is None:
        return ""
    value = tag.get(name, "")
    if isinstance(value, list):
        return " ".join(value)
    return str(value)


def detect_tech(soup: BeautifulSoup, headers: dict[str, str]) -> list[str]:
    """Erkennt verwendete Technologien aus HTML und Response-Headern.

    Args:
        soup:
            Das geparste HTML der Seite.
        headers:
            Response-Header mit kleingeschriebenen Schluesseln.

    Returns:
        Liste der erkannten Technologien (ohne Duplikate, Reihenfolge stabil).
    """
    found: list[str] = []

    def add(name: str) -> None:
        if name not in found:
            found.append(name)

    # Generator-Meta-Tag -> CMS
    generator = _attr(soup.find("meta", attrs={"name": "generator"}), "content").lower()
    for marker, name in _GENERATOR_MARKERS:
        if marker in generator:
            add(name)

    # Script-src und Link-href durchsuchen
    urls: list[str] = []
    for script in soup.find_all("script", src=True):
        urls.append(_attr(script, "src").lower())
    for link in soup.find_all("link", href=True):
        urls.append(_attr(link, "href").lower())
    haystack = " ".join(urls)
    for marker, name in _URL_MARKERS:
        if marker in haystack:
            add(name)

    # Server- und X-Powered-By-Header
    server = headers.get("server", "").lower()
    for needle, name in (
        ("nginx", "nginx"),
        ("apache", "Apache"),
        ("iis", "IIS"),
        ("litespeed", "LiteSpeed"),
        ("caddy", "Caddy"),
        ("cloudflare", "Cloudflare"),
    ):
        if needle in server:
            add(name)
    powered = headers.get("x-powered-by", "").lower()
    for needle, name in (("php", "PHP"), ("asp.net", "ASP.NET"), ("express", "Express")):
        if needle in powered:
            add(name)

    return found


def extract_seo(soup: BeautifulSoup) -> SeoInfo:
    """Liest SEO-/Meta-Daten aus dem HTML.

    Args:
        soup:
            Das geparste HTML der Seite.

    Returns:
        Gefuellte SeoInfo.
    """
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    og_tags: list[str] = []
    for prop in ("og:title", "og:description", "og:image"):
        if soup.find("meta", attrs={"property": prop}) is not None:
            og_tags.append(prop)

    return SeoInfo(
        title=title,
        description=_attr(soup.find("meta", attrs={"name": "description"}), "content").strip(),
        h1_count=len(soup.find_all("h1")),
        canonical=_attr(soup.find("link", attrs={"rel": "canonical"}), "href"),
        lang=_attr(soup.find("html"), "lang"),
        has_viewport=soup.find("meta", attrs={"name": "viewport"}) is not None,
        robots=_attr(soup.find("meta", attrs={"name": "robots"}), "content"),
        og_tags=og_tags,
    )


def detect_issues(result: CrawlResult) -> list[str]:
    """Erkennt typische Probleme einer Seite aus den bereits geladenen Daten.

    Schnelle Pruefungen ohne zusaetzlichen Request: HTTP-Fehler,
    fehlende/zu lange SEO-Elemente, fehlende Mobile-Optimierung,
    langsame Ladezeit, grosse Seite.

    Args:
        result:
            Das CrawlResult der Seite.

    Returns:
        Liste der gefundenen Probleme als lesbare Texte (leer = keine Probleme).
    """
    issues: list[str] = []

    if result.http_status_code >= 400:
        issues.append(t("issue.http_error", code=result.http_status_code))

    # SEO-Pruefungen nur fuer HTML-Seiten.
    if "html" in result.content_type.lower():
        seo = result.seo
        if not seo.title:
            issues.append(t("issue.no_title"))
        elif len(seo.title) > 60:
            issues.append(t("issue.title_long", count=len(seo.title)))
        if not seo.description:
            issues.append(t("issue.no_description"))
        elif len(seo.description) > 160:
            issues.append(t("issue.description_long", count=len(seo.description)))
        if seo.h1_count == 0:
            issues.append(t("issue.no_h1"))
        elif seo.h1_count > 1:
            issues.append(t("issue.multiple_h1", count=seo.h1_count))
        if not seo.has_viewport:
            issues.append(t("issue.no_viewport"))
        if not seo.lang:
            issues.append(t("issue.no_lang"))
        if not seo.canonical:
            issues.append(t("issue.no_canonical"))
        if "noindex" in seo.robots.lower():
            issues.append(t("issue.noindex"))

    if result.load_time_ms > 3000:
        issues.append(t("issue.slow"))
    if result.page_size > 2_000_000:
        issues.append(t("issue.large"))

    return issues


def extract_http_details(headers: dict[str, str]) -> dict[str, str]:
    """Filtert die fuer die Anzeige interessanten HTTP-Header heraus.

    Args:
        headers:
            Response-Header mit kleingeschriebenen Schluesseln.

    Returns:
        Dict mit den vorhandenen interessanten Headern.
    """
    return {key: headers[key] for key in _INTERESTING_HEADERS if headers.get(key)}
