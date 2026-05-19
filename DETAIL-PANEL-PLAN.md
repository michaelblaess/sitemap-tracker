# Plan: Detail-Panel ausbauen

Status: **Entwurf** - wartet auf Bestaetigung. Umsetzung nach den bereits
erledigten Punkten (Header-Umbau, Crawl-Dialog, Tooltips).

## Ziel

Das rechte Detail-Panel (`StatsPanel` -> `#url-detail`) soll zur ausgewaehlten
Seite mehr Informationen zeigen. Von Michael gewuenscht (alle vier):

1. Tech-Stack-Erkennung
2. SEO-/Meta-Daten
3. Mehr HTTP-/Response-Details
4. Seiten-Vorschau als Bild - **per Setting ein-/ausschaltbar**

## Phasen

### Phase 1 - "kostenlose" Infos (kein neuer Request, keine neue Dependency)

Alle drei aus Daten, die der Crawler ohnehin schon hat (HTML + Response).
Neue Felder auf `CrawlResult`, befuellt im Crawler, angezeigt im Detail-Panel.

**Tech-Stack** (aus dem HTML, BeautifulSoup ist schon im Crawler):
- `<meta name="generator">` -> WordPress, Sitefinity, TYPO3, Drupal, Hugo ...
- Script-/Link-URLs + globale JS-Objekte -> jQuery, React, Vue, Angular,
  Bootstrap, Tailwind, htmx ...
- Analytics: Google Analytics / GTM, Matomo
- Ergebnis: `CrawlResult.tech: list[str]`

**SEO-/Meta-Daten** (aus dem HTML):
- title + Laenge, meta description + Laenge, h1-Anzahl, canonical,
  `lang`-Attribut, viewport vorhanden, robots-meta, Open-Graph (og:title/
  og:image vorhanden)
- Ergebnis: einzelne Felder oder `CrawlResult.seo: dict[str, str]`

**HTTP-/Response-Details** (aus der Response):
- Server-Header, wichtige Caching-Header (Cache-Control, ETag, Age),
  Content-Encoding (gzip/br), gesetzte Cookies (Anzahl), Redirect-Kette
- Ergebnis: `CrawlResult.response_headers: dict[str, str]` (gefiltert)

Anzeige: zusaetzliche `_detail_line`-Bloecke im Detail-Panel, evtl. mit
`Rule`-Trennern gruppiert (Tech / SEO / HTTP).

### Phase 2 - Seiten-Vorschau als Bild

Aufwaendiger, daher getrennt:
- **Dependency** `textual-image[textual]` (TGP/Sixel) + Halfblock-Fallback -
  Muster wie retro-amp Cover-Art (`cover_art_panel.py`).
- **Screenshot-Quelle**: Playwright `page.screenshot()`. Im httpx-Modus gibt
  es keinen Browser -> Vorschau dann entweder deaktiviert oder ein separater
  Playwright-Start nur fuer den Screenshot (teuer).
- **Setting**: neuer Schalter in den Settings ("Seiten-Vorschau anzeigen",
  evtl. mit Renderer-Wahl graphics/aus) - via `BaseSettingsScreen`-Hook.
- **Speicher/Zeit**: Screenshot pro Seite kostet Zeit und Platz; nur bei
  aktivem Setting erzeugen, ggf. lazy beim Auswaehlen der Zeile.
- DA1/Cell-Size-Query-Stolperstein beachten (textual-image vor `App.run()`
  eager importieren - siehe python-specialist-Skill).

## Offene Fragen

- Phase 1 zuerst umsetzen und ausliefern, Phase 2 danach? (empfohlen)
- Vorschau: im httpx-Modus deaktivieren, oder Screenshots immer per
  Playwright-Sidecar holen?
- Tech-Stack: erstmal kleine kuratierte Liste oder eine groessere
  Erkennungs-Datenbank (Wappalyzer-Stil)?
