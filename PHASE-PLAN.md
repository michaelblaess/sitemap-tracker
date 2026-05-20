# sitemap-generator: Drei-Phasen-Plan

Status: **Phase 1 erledigt** — alle sechs Items umgesetzt.

## Entscheidungen (Phase 1)

1. **Tab-Layout:** Eine Filterleiste oben, wirkt auf beide Tabs.
2. **History-Save-Timing:** Eintrag mit Params bei Crawl-Start, Stats per Update am Ende.
3. **EN-Datum:** ISO `2026-05-19 20:58` (DE bleibt `dd.MM.yyyy HH:mm`).
4. **Renaming:** Vorerst nicht entscheiden — bleibt `sitemap-generator` durch Phase 1.

## Phase 1 — UI-Umbau (jetzt)

### 1.1 "Feuer frei"-String entfernen
- `t("stats.ready")` aus `widgets/stats_panel.py` (compose: `#stats-content`)
  ganz raus. Den Static loeschen, nur `#url-detail` bleibt.
- i18n-Key `stats.ready` wird unused -> kann mitgeloescht werden.
- **Aufwand:** trivial.

### 1.2 Tabs unter der Filterleiste
- `widgets/url_table.py` erweitern: Filter bleibt oben (an einer Stelle), darunter
  `TabbedContent` mit zwei `TabPane`s:
  - **TabPane "Ergebnisse"** -> die bestehende `DataTable`
  - **TabPane "Baumansicht / Struktur"** -> neues eingebettetes Tree-Widget
- Tree-Logik aus `screens/tree.py` in ein neues `widgets/page_tree.py`-Widget
  extrahieren (Tree-Bau aus den CrawlResults). Wiederverwendbar.
- Filter wirkt **auf beide Tabs** (Empfehlung) — Frage 1 unten.
- Beide Tabs immer sichtbar, auch wenn Liste leer.
- **Aufwand:** gross. Tree-Extraktion + TabbedContent + Filter-Kopplung.

### 1.3 Modal-Tree-Dialog entfernen
- `screens/tree.py` loeschen.
- `action_show_tree` und Binding `b` aus `app.py` raus.
- `binding.tree` und `tooltip.tree`-i18n-Keys raus.
- **Aufwand:** klein (Cleanup).

### 1.4 Alle Footer-Eintraege mit ausfuehrlichem Tooltip
Aktuell haben nur `j`, `g`, `f` einen Tooltip. Erweitern auf ALLE Bindings.
Bindings im Footer (nach #1.3): `q c x m s g j e f d l h i` (13 Tasten).
- Pro Binding ein `tooltip.<action>`-Key in `de.json` + `en.json`.
- Tooltip-Erweiterung in `_init_bindings()` (per `dataclasses.replace`).
- **Aufwand:** mittel — 13 Texte de+en, mechanisch.

### 1.5 History speichert Statistiken
`HistoryEntry` erweitern um:
- `total_crawled: int = 0` (Gecrawlt)
- `total_2xx: int = 0` (200er)
- `total_3xx: int = 0` (Redirects)
- `total_4xx: int = 0` (Fehler)
- `total_5xx: int = 0` (Server-Fehler)

`models/history.py`: in `to_dict()` + `from_dict()` aufnehmen. Alte History-
Eintraege ohne Stats lesen mit Default 0.

`screens/history.py`: zusaetzliche Spalten in der Tabelle anzeigen.

**Save-Timing:** Frage 2 unten.

**Aufwand:** mittel.

### 1.6 History-Datum culture-abhaengig (wird REGEL)
- DE: `19.05.2026 20:58` (`dd.MM.yyyy HH:mm`)
- EN: `2026-05-19 20:58` (ISO, oder US `05/19/2026 08:58 PM` — Frage 3)
- Helfer `format_datetime(dt, lang)` in `i18n.py` (oder neuem
  `services/formatting.py`).
- **Regel fuer die Zukunft:** Jede Datums-/Zeitanzeige laeuft ueber den Helfer,
  nicht direkt aus `dt.isoformat()`. Wird in den `python-specialist`-Skill
  aufgenommen.
- **Aufwand:** klein.

## Phase 2 — Erweiterungen (nach Phase 1)

### 2.1 Kontextmenues fuer Ergebnisliste + Baum
- `textual-widgets.ContextMenuScreen` ist bereits vorhanden — wiederverwenden.
- Rechtsklick auf Tabelle / Tree -> Menue mit Aktionen.
- Konkrete Items: noch zu definieren (siehe 2.2 Custom-Actions).

### 2.2 Custom-Actions fuer Kontextmenues
Diskussion noch offen. Optionen:
- **Eingebaute Aktionen** mit fester Auswahl (z.B. "URL kopieren", "Im Browser oeffnen",
  "Aus History entfernen", "Als Startpunkt fuer Sub-Crawl").
- **Plugin-System** mit User-definierten Actions (z.B. Python-Plugins unter
  `~/.sitemap-generator/plugins/`).
- Empfehlung: erst eingebaute Aktionen, Plugin-System spaeter, wenn der Bedarf
  konkret wird.

### 2.3 Berichtsfunktion
Format: HTML vs. PowerPoint — Frage 5 unten.
Inhalte (Vorschlag):
- Crawl-Zusammenfassung (Datum, URL, Stats, Dauer)
- Liste aller Dead-Links (4xx/5xx) mit Quellseiten
- Seitenbaum als Grafik (Mermaid in HTML, oder SVG)
- Tech-Stack-Statistik (welche CMS/Frameworks am haeufigsten)
- SEO-Probleme aggregiert (welche Issues am haeufigsten)
- Screenshots der Top-Probleme

### 2.4 Screenshots-Export aller Seiten
- Existierendes `PreviewService` erweitern: alle URLs durchgehen, je Seite
  Screenshot in einen Ordner schreiben (`screenshots/<sanitized-url>.png`).
- Als Action (Footer-Taste oder Kontextmenue) ausloesbar.
- Fortschrittsanzeige im Log.

### 2.5 Komplett-Site-Backup
Format-Frage 6 unten: MHT / WARC / Ordner.
- WARC ist der Web-Archive-Standard (genutzt von Internet Archive).
- MHT ist alt, nur in MS-Browsern gut.
- Ordner (HTML + Assets) ist intuitiv aber gross.

### 2.6 Renaming
Aktuell "sitemap-generator" — der Tool-Umfang ist deutlich groesser geworden.
- Frage 4 unten: Welcher Name, wann?
- Migration: GitHub-Repo umbenennen (GitHub legt automatisch einen Redirect an),
  pyproject/`__init__.py`/Package-Ordner umbenennen, install.ps1/sh-URLs anpassen,
  README + docs aktualisieren, release.yml-Artefakt-Pfade anpassen.

## Phase 3 — Marketing / Distribution

### 3.1 Animiertes GIF / Video
- Empfehlung: **vhs (Charmbracelet)** — VHS-Skripte, deterministisch, GIF/MP4-Export.
- Alternative: asciinema-agg (asciinema -> GIF).
- Pro Feature ein kurzes Demo-GIF (10-20s), einbinden in README.md + docs/.

### 3.2 App-Stores
Verteilung neben den bestehenden install.ps1/sh:
- **Microsoft Store** (MSIX-Paket) — kostenlos fuer Devs, MSIX-Bau-Tooling noetig
- **winget** (Microsoft) — PR an `microsoft/winget-pkgs`
- **Chocolatey** (Windows community) — chocolateyinstall.ps1
- **Scoop** (Windows community) — Manifest in einer Bucket
- **Homebrew** (macOS) — Cask oder Formula
- **Snap** (Linux) — Canonical Snap Store
Aufwand pro Store ist real (Submission, Signierung, Update-Pipeline) — sinnvoll
erst NACH dem Renaming und mit klarem App-Versprechen.

---

## Offene Fragen (Phase 1 zuerst)

1. **Tab-Layout:** Filter ueber den Tabs (eine Filterleiste, wirkt auf beide
   Tabs), oder pro Tab eine eigene Filterleiste?
2. **History-Save-Timing:** Entry beim Crawl-Start mit Params persistieren und
   am Ende mit Stats updaten? Oder erst am Ende speichern (atomar, aber bei
   Cancel verloren)?
3. **EN-Datumsformat:** ISO `2026-05-19 20:58` (kompakt, gebraeuchlich) oder
   US `05/19/2026 08:58 PM` (US-Locale-Default)?
4. **Renaming-Timing + Name:** jetzt mit Phase 1, oder am Anfang von Phase 2?
   Name-Vorschlaege: `site-scanner`, `site-inspector`, `sitewright`,
   `websight`, `siteguard`, `sitepulse`.
5. **Bericht-Format (Phase 2):** HTML, PowerPoint, oder beide?
6. **Site-Backup-Format (Phase 2):** WARC, MHT, oder Ordner mit HTML+Assets?
