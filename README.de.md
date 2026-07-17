<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/icon-globe-dark.svg">
    <img src="docs/icon-globe-light.svg" width="120" alt="Sitemap Tracker Logo">
  </picture>
</p>

# Sitemap Tracker

<p align="center">
  <img src="docs/flags/gb.svg" height="13" alt=""> <a href="README.md">English</a> ·
  <img src="docs/flags/de.svg" height="13" alt=""> <b>Deutsch</b>
</p>

---

[![Stars](https://img.shields.io/github/stars/michaelblaess/sitemap-tracker?logo=github&logoColor=white&color=fbbf24)](https://github.com/michaelblaess/sitemap-tracker/stargazers)
[![Forks](https://img.shields.io/github/forks/michaelblaess/sitemap-tracker?logo=github&logoColor=white&color=34d399)](https://github.com/michaelblaess/sitemap-tracker/network/members)
[![Issues](https://img.shields.io/github/issues/michaelblaess/sitemap-tracker?logo=github&logoColor=white&color=f87171)](https://github.com/michaelblaess/sitemap-tracker/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/michaelblaess/sitemap-tracker?logo=github&logoColor=white&color=a78bfa)](https://github.com/michaelblaess/sitemap-tracker/pulls)

[![Last Commit](https://img.shields.io/github/last-commit/michaelblaess/sitemap-tracker?logo=git&logoColor=white&color=3b82f6)](https://github.com/michaelblaess/sitemap-tracker/commits/main)
[![License](https://img.shields.io/badge/license-Apache_2.0-3b82f6)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3b82f6?logo=python&logoColor=white)](https://www.python.org/)

Crawlt Websites und generiert standardkonforme `sitemap.xml` Dateien. Nutzt [Playwright](https://playwright.dev/) für JavaScript-Rendering oder [httpx](https://www.python-httpx.org/) für schnelles HTTP-Crawling.

## Screenshots

### Hauptansicht
![Hauptansicht](docs/screenshots/01-main.png)

### Seitenbaum
![Seitenbaum](docs/screenshots/02-sitemap.png)

### Crawl-History
![Crawl-History](docs/screenshots/03-history.png)

## Installation

### One-Liner (Standalone, kein Python nötig)

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/michaelblaess/sitemap-tracker/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/michaelblaess/sitemap-tracker/main/install.ps1 | iex
```

## Verwendung

```bash
# Einfach crawlen (httpx-Modus, schnell)
sitemap-tracker https://example.com

# Mit JavaScript-Rendering (Playwright)
sitemap-tracker https://example.com --render

# Sitemap direkt speichern
sitemap-tracker https://example.com --output sitemap.xml

# Crawl-Tiefe begrenzen
sitemap-tracker https://example.com --max-depth 5

# Mehr Parallelitaet
sitemap-tracker https://example.com --concurrency 16

# robots.txt ignorieren
sitemap-tracker https://example.com --ignore-robots

# Mit Cookies (z.B. fuer Login)
sitemap-tracker https://example.com --cookie session=abc123
```

## CLI-Parameter

| Parameter | Beschreibung | Default |
|---|---|---|
| `URL` | Start-URL der Website | - |
| `--output`, `-o` | Ausgabe-Pfad für sitemap.xml | `sitemap_<host>_<timestamp>.xml` |
| `--max-depth`, `-d` | Maximale Crawl-Tiefe | 10 |
| `--concurrency`, `-c` | Parallele Requests | 8 |
| `--timeout`, `-t` | Timeout pro Seite (Sekunden) | 30 |
| `--render` | JavaScript mit Playwright rendern | aus |
| `--no-headless` | Browser sichtbar (Debugging) | aus |
| `--ignore-robots` | robots.txt ignorieren | aus |
| `--user-agent` | Custom User-Agent | Chrome 131 |
| `--cookie` | Cookie setzen (NAME=VALUE, mehrfach) | - |

## Tastenkürzel (TUI)

| Taste | Funktion |
|---|---|
| `c` | Crawl starten (URL-Dialog) |
| `x` | Crawl abbrechen / JSON-Fehlerbericht |
| `m` | Sitemap speichern (Speichern-unter-Dialog) |
| `s` | Einstellungen |
| `g` | Formular-Report exportieren (JSON) |
| `j` | JIRA-Tabelle in Zwischenablage |
| `e` | Nur Fehler anzeigen |
| `f` | Sitemap-Diff |
| `d` | URL-Details kopieren |
| `l` | Log ein/aus |
| `h` | History |
| `z` | Crawl-Zusammenfassung (Score, Ergebnisse) |
| `?` | HTTP-Statuscode-Referenz |
| `i` | Info-Dialog |
| `q` | Beenden |

Log kopieren / exportieren läuft über Rechtsklick auf das Log-Panel.
Beim Hovern über ein Tastenkürzel im Footer erscheint ein ausführlicher Tooltip mit der Erklärung.
URLs im Log, im Header und im Detail-Panel sind ohne festgehaltenes Strg klickbar.

## Features

- **Dual-Modus**: httpx (schnell, nur HTML) oder Playwright (JavaScript-Rendering)
- **robots.txt**: Wird standardmäßig respektiert, `--ignore-robots` zum Deaktivieren
- **Auto-Split**: Bei >50.000 URLs automatisch Sitemap-Index mit Teil-Sitemaps
- **Priority**: Automatisch basierend auf Crawl-Tiefe (Startseite = 1.0)
- **lastmod**: Aus HTTP Last-Modified Header
- **URL-Normalisierung**: Duplikate durch Normalisierung vermieden
- **Redirect-Ziele auflösen (Alias auf gleichem Host)**: Eine Sitemap listet normalerweise nur gecrawlte HTTP-200-HTML-Seiten — reine Weiterleitungen (301/302) bleiben draußen, weil sie keinen eigenen Inhalt haben. Es gibt aber einen Sonderfall: Zeigt ein Redirect auf eine Seite **auf demselben Host, die sonst nicht gelistet** ist (ein interner *Alias*, z.B. `/alter-pfad` → `/neuer-pfad`, wobei `/neuer-pfad` nur über die Weiterleitung erreichbar ist), würde dieses aufgelöste Ziel durchs Raster fallen und nie in der Sitemap landen. Der Writer schreibt deshalb das **aufgelöste Ziel** in die Sitemap, statt den Redirect stillschweigend wegzuwerfen. Drei Regeln halten das sauber und standardkonform:
  1. **Schon abgedeckt → übersprungen.** Löst der Redirect auf eine Seite auf, die bereits als 200-Seite gelistet ist, wird er verworfen — ein erneutes Scannen wäre nur ein Duplikat der vorhandenen Seite.
  2. **Gleiches Ziel → ein Eintrag.** Mehrere Redirects auf dasselbe Ziel ergeben genau einen Sitemap-Eintrag.
  3. **Nur gleicher Host.** Nur Ziele auf **exakt demselben Host** werden aufgenommen. Eine `sitemap.xml` darf laut [sitemaps.org-Standard](https://www.sitemaps.org/protocol.html#location) nur URLs des Hosts enthalten, auf dem sie liegt — Redirects auf **Schwester-Subdomains** (z.B. `www.blog.kunde.example`, das auf `www.kunde.example` oder `www.shop.kunde.example` weiterleitet) oder fremde Domains werden **ausgeschlossen**. Sie gehören in die Sitemap *ihrer eigenen* Site, nicht in diese. Wenn du diese Seiten scannen willst, crawle den jeweiligen Host direkt.

  Hinweis: Der *finale* HTTP-Status des aufgelösten Ziels wird nicht erneut abgerufen (der Crawler hat nur den ursprünglichen 301 gespeichert), ein defektes gleicher-Host-Alias-Ziel taucht also als Fehler im nachgelagerten Scan auf — genau das, was man sehen will.
- **Formular-Erkennung**: `<form>`-Tags werden erkannt, in der Tabelle markiert und als JSON exportierbar
- **Dead-Link-Quelltext-Viewer**: Für jede 4xx/5xx-Seite springst du direkt in den HTML-Quelltext der verweisenden Seite und siehst exakt die Zeile mit dem defekten Link — Pygments-eingefärbt, die Treffer-Zeile in warmem Gold hervorgehoben. Von dort: Quell-URL im Browser öffnen, ein paste-fertiges Snippet (defekte URL + ±3 Zeilen Kontext + Zeilennummer) in die Zwischenablage kopieren, oder das komplette HTML als Beweisstück speichern
- **Kontextmenü auf der Ergebnis-Tabelle**: Rechtsklick öffnet die fünf Bulk-Aktionen (Nur-Fehler-Filter, Sitemap als XML speichern, Fehlerbericht als JSON speichern, JIRA-Tabelle kopieren, Formular-Report). 4xx/5xx-Zeilen bekommen zusätzlich einen Direkteinstieg in den Quelltext-Viewer
- **JIRA-Tabelle in zwei Formaten** (Einstellungen -> Export): **Markdown** für Jira Cloud (wandelt sich beim Einfügen ins Kommentarfeld automatisch in eine echte Tabelle um) und **Wiki Markup** für ältere Jira-Server/Data-Center-Instanzen
- **Live-TUI**: Fortschritt, Statistiken und URL-Details in Echtzeit — Ergebnis-Tabelle und Seitenbaum auf zwei Tabs verteilt
- **Sortierbare Ergebnisse**: Klick auf eine Spaltenüberschrift sortiert die Tabelle (Status, HTTP, Tiefe, Links, Formular, Zeit, Größe, Datum, URL) — zweiter Klick kehrt um. Aktive Spalte mit ▲/▼-Pfeil gekennzeichnet. Beim Überfahren des "Links"-Spaltenkopfs erklärt ein Tooltip, dass dort die internen Links der Seite gezählt werden
- **Crawl-Zusammenfassung**: Am Ende eines Crawls zeigt ein Modal einen Site-Score (0-100 %, Anteil fehlerfreier Seiten, mit Note A-F) und eine Ergebnis-Tabelle (gecrawlte / fehlerfreie / fehlerhafte Seiten, HTTP-Status-Verteilung, gefundene interne Links, **URLs in der Sitemap und wie viele davon aufgelöste Redirect-Ziele sind** — siehe "Redirect-Ziele auflösen" oben). Neben "Schließen" gibt es einen Button "Sitemap speichern". Mit `z` jederzeit wieder aufrufbar
- **HTTP-Statuscode-Referenz**: Mit `?` öffnet sich eine schnelle Nachschlage-Tabelle aller gängigen HTTP-Statuscodes, gruppiert nach Klasse (2xx/3xx/4xx/5xx) mit Bedeutung und Erklärung - praktisch, um etwa einen 301 von einem 307 zu unterscheiden
- **Proxy-/SSO-Erkennung**: Vor dem Crawl wird die Start-URL einmal geprüft. Wird sie auf eine fremde Domain umgeleitet (typisch für einen Proxy, ein Auth-Gateway wie Zscaler oder ein SSO-Login wie Microsoft), erklärt ein Warn-Modal die Lage und der Crawl wird abgebrochen - statt stillschweigend nur die Seed-URLs zu liefern. Weiterleitungen innerhalb derselben Registrable-Domain (z. B. Alias-301 auf eine Schwester-Subdomain) lösen es nicht aus
- **Datum & Größe direkt in der Tabelle**: Last-Modified-Datum und Seitengröße sind als eigene Spalten neben der URL sichtbar. **Hinweis zur Größe:** Der "Größe"-Wert ist die HTML-Dokumentgröße (der gelieferte Quelltext). Beim Crawlen werden Ressourcen wie Bilder, CSS, JS und Fonts **nicht** geladen und zählen daher nicht mit - die echte Gesamt-Seitengröße (wie ein Browser sie meldet) ist höher. Beim Überfahren des "Größe"-Spaltenkopfs wird das erklärt
- **Klickbare Links**: URLs im Log, im Crawl-Header und im Detail-Panel öffnen mit einem einzelnen Klick (ohne Strg) im Standard-Browser; lokale Ergebnisdateien (sitemap.xml, JSON-Reports) öffnen sich im jeweiligen OS-Standardprogramm
- **Seitenbaum**: Hierarchische Sicht aller gecrawlten URLs mit HTTP-Status, Dead-Link- und Nicht-in-Sitemap-Markern — eingebettet als Tab, Geschwister alphabetisch sortiert; der Tabellen-Filter wirkt auf den Baum mit (passende Knoten und ihre Vorfahren bleiben sichtbar)
- **URL-Dialog**: `c` öffnet einen Dialog (mit der zuletzt verwendeten URL vorbelegt), um die Ziel-URL einzugeben oder zu ändern — ohne Neustart
- **Crawl-Header**: Alle Crawl-Statistiken — Modus, robots.txt, Concurrency, Statuscodes, Fortschritt — gebündelt in einem einklappbaren Kopf-Panel
- **Seiten-Details**: Beim Auswählen einer URL erscheinen gruppierte Panels — Seiteninfo, Probleme, Tech-Stack, SEO-/Meta-Daten und HTTP-Header
- **Footer-Tooltips**: Zu jedem Tastenkürzel erscheint beim Hovern ein ausführlicher Tooltip — auch zu den kryptischen wie JIRA-Tabelle, Sitemap-Diff oder Formular-Report
- **Problem-Erkennung**: Markiert typische Schwachstellen pro Seite — HTTP-Fehler, fehlender/zu langer Titel & Description, fehlende H1/Viewport/Canonical, `noindex`, langsame Ladezeit, große Seite
- **Tech-Stack-Erkennung**: Erkennt CMS, JS-/CSS-Frameworks und Server-Software jeder Seite
- **Seiten-Vorschau**: Optionaler Screenshot der ausgewählten Seite direkt im Terminal (TGP/Sixel mit Half-Block-Fallback) — in den Einstellungen abschaltbar. Vor dem Schuss wird der Cookie-Consent akzeptiert, auf Netzwerk-Ruhe gewartet und Lazy-Loading angestoßen, damit Hero-Bilder gerendert werden statt abgeschnitten zu sein. Eine Live-Phasenanzeige (Seite wird geladen, Consent wird akzeptiert, Bilder werden nachgeladen, Screenshot wird erstellt) erklärt, warum es 2-3 Sekunden dauern kann
- **Speichern-unter-Dialog**: `m` öffnet einen Datei-Dialog zur Wahl des Speicherorts der `sitemap.xml`, mit Namensvorschlag vorbelegt und merkt sich den zuletzt genutzten Ordner
- **Anpassbare Panels**: Splitter zum freien Anpassen von URL-Tabelle, Log und Statistik-Panel
- **Log-Panel**: Rechtsklick-Kontextmenü — kopieren, in Datei exportieren oder ausblenden
- **Einstellungen-Dialog**: Sprache, robots.txt, Playwright, Seiten-Vorschau, Concurrency, Timeout und Crawl-Tiefe — dauerhaft gespeichert
- **Filter mit Verlauf**: URL-Tabelle nach URL/Status filtern; letzte Filterbegriffe im Dropdown
- **Crawl-History**: Vergangene Crawls mit Datum, URL, Parametern und finalen Statistiken (gecrawlt / 200er / Fehler); Datum im Format der UI-Sprache (DE: `TT.MM.JJJJ`, EN: ISO). Nach Auswahl einer URL aus der History blinkt die Footer-Taste `c` (Crawl) als Hinweis, dass du startklar bist

## Browser-Strategie

1. **System-Chrome** bevorzugt (schnellerer Start, weniger Speicher)
2. **Gebündeltes Chromium** als Fallback (bei Standalone-Installation enthalten)

## Datenschutz

**Wichtig**: Das Crawlen einer Website kann je nach Umfang und Häufigkeit vom Betreiber als ungewöhnlicher Traffic wahrgenommen werden. Bitte beachte:

- Informiere den Website-Betreiber **vor** dem Crawlen, insbesondere bei großen Websites
- Respektiere die `robots.txt` (ist standardmäßig aktiviert)
- Setze angemessene Concurrency- und Timeout-Werte
- Dieses Tool ist für **eigene Websites** und **autorisierte Analysen** gedacht

## Entwickler

### Setup

```bash
git clone https://github.com/michaelblaess/sitemap-tracker.git
cd sitemap-tracker

# Windows
.\bootstrap.ps1

# Linux/macOS
./bootstrap.sh
```

### Lokaler Start

```bash
# Windows
.\run.ps1 https://example.com

# Linux/macOS
./run.sh https://example.com
```

### Release erstellen

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

GitHub Actions baut automatisch Executables für Windows, Linux und macOS.

## Lizenz

Apache License 2.0 - siehe [LICENSE](LICENSE)
