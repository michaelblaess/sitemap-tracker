# sitemap-generator: Drei-Phasen-Plan

Status: **Phase 1 erledigt** — alle sechs Items umgesetzt. Seither
deutlich darueber hinausgegangen (v1.14.0): klickbare Links ueber das
ClickableLinksMixin in textual-widgets, Detail-Panel-Reorg, History-Pick
nimmt nur die URL, Cursor-Reset am Crawl-Ende, sortierbare Tabellen-
Spalten, Datum+Groesse als Spalten, Rechtsklick-Kontextmenue mit Bulk-
Aktionen, Footer-Sync fuer den e-Toggle, Responsible-Crawling-Hinweis
im About, und vor allem der **Dead-Link-Quelltext-Viewer** mit
Pygments-Highlighting + 3 Action-Buttons (Browser/Treffer-kopieren/HTML-
speichern).

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

### 2.7 Save-As-Dialog (cross-app, textual-widgets)
Aktuell schreiben alle Save-Aktionen (Sitemap-XML, Fehler-JSON,
Formular-JSON, HTML-Speichern im Quelltext-Viewer) in das CWD mit
auto-generiertem Dateinamen. Vorschlag:

- Neuer ``FileSaveAsScreen`` in textual-widgets: Pfad-Input (vorbelegt
  mit dem Default-Namen), Speichern/Abbrechen. Erste Version OHNE
  File-Browser — nur freie Pfad-Eingabe. Tab-Completion oder DirectoryTree
  spaeter.
- Ergebnis: ``str | None`` — der absolute Pfad oder ``None`` bei
  Abbruch.
- Alle Save-Stellen in sitemap-generator umstellen.

### 2.8 Export-Dialog (statt verstreuter Footer-Bindings)
Heute hat der Footer ``m Sitemap | g Forms report | j JIRA | x Fehler-JSON``
— vier Tasten fuer „etwas exportieren". Konsolidieren auf **eine** Taste
``x Export``:

- ``ExportScreen``: Liste der verfuegbaren Formate (Sitemap-XML,
  Fehler-JSON, JIRA-Tabelle, Formular-JSON, spaeter HTML-Report
  und Screenshot-Ordner) + Pfad/Zwischenablage als Ziel.
- Tastatur-Auswahl: 1-9 Sofort-Trigger, Enter aus der Liste.
- Footer wird damit aufgeraeumt (drei freie Tasten — z.B. fuer ein
  zukuenftiges Bookmarks-/Notizen-Feature).
- Migration: alte Bindings als versteckte ``show=False``-Shortcuts
  beibehalten, damit Muskelgedaechtnis nicht stirbt.

### 2.9 Eingebaute TUI-Screenshot-Funktion
Textuals ``App.save_screenshot()`` exportiert die aktuelle TUI als SVG.
Nutzen:

- Action ``F12`` oder ``Ctrl+Shift+S`` -> Screenshot des aktuellen
  Zustands ins CWD (oder via Save-As-Dialog 2.7).
- Optional: SVG -> PNG ueber ``cairosvg`` (kleine Extra-Dep), damit
  Marketing-Pipelines, Twitter/X, README-Bilder direkt nutzbar sind.
- Nuetzlich fuer Bug-Reports (User screenshot-t den Fehlerzustand und
  schickt ihn).

### 2.6 Renaming -> **"Sitemap Tracker"**
Name **fixiert**: ``Sitemap Tracker`` (Display) / ``sitemap-tracker``
(CLI/Paket/Repo). Beschreibt das, was das Tool tatsaechlich tut — nicht
nur sitemap.xml erzeugen, sondern *tracken* was sich auf der Site
bewegt (Dead-Links, Last-Modified, neue/verschwundene Pages).
Trademark-Check via DPMA/WIPO durch Michael — Stand: scheint frei.

**Migrations-Checkliste fuer morgen:**

GitHub & Distribution
- [ ] GitHub-Repo umbenennen: ``sitemap-generator`` -> ``sitemap-tracker``
      (legt automatisch einen Redirect an)
- [ ] ``.github/workflows/release.yml``: Artefakt-Namen anpassen
      (``sitemap-tracker-v*-windows-x64.zip`` etc.)
- [ ] ``install.ps1`` / ``install.sh``: URLs in den raw.githubusercontent-
      Pfaden + Zielverzeichnis-Name + Wrapper-Script-Name
- [ ] ``compile-*.{ps1,sh}``: ``--output-filename=sitemap-tracker``,
      Zip/Tar-Naming, ``--include-package=sitemap_tracker``,
      ``--product-name="Sitemap Tracker"``

Package
- [ ] ``pyproject.toml``: ``name = "sitemap-tracker"``,
      ``[project.scripts] sitemap-tracker = "sitemap_tracker.__main__:main"``,
      ``package-data`` Pfad, ``packages.find`` Konfiguration
- [ ] Package-Ordner umbenennen:
      ``src/sitemap_generator/`` -> ``src/sitemap_tracker/``
- [ ] ``src/sitemap_tracker/__init__.py``: Docstring anpassen
- [ ] Alle Module-Imports ``from sitemap_generator...`` -> ``from sitemap_tracker...``
- [ ] ``tests/`` -> entsprechende Imports + ``import sitemap_tracker``
- [ ] ``run.ps1`` / ``run.sh``: ``-m sitemap_tracker`` (statt
      ``sitemap_generator``)
- [ ] ``__main__.py``: ``set_terminal_title(f"sitemap-tracker v{...}")``

App-sichtbare Strings
- [ ] ``TITLE = "Sitemap Tracker v{...}"``
- [ ] ``AboutScreen(app_name="Sitemap Tracker", ...)``
- [ ] i18n-Keys ``log.version`` (``[bold]Sitemap Tracker v{version}[/bold]``),
      ``cli.banner``, ``about.description`` (Tool-Name)
- [ ] Logger-Namen optional: ``logger = logging.getLogger("sitemap_tracker")``

User-Daten — wichtig fuer Bestandskunden
- [ ] Settings-Verzeichnis ``~/.sitemap-generator/`` -> ``~/.sitemap-tracker/``
- [ ] **Migration beim Start**: wenn alter Pfad existiert UND neuer nicht,
      einmalig kopieren (``shutil.copytree``) und beim alten Pfad eine
      ``.migrated``-Marker-Datei ablegen — damit Bestands-Crawls, History
      und Settings nicht verloren gehen
- [ ] History-Dateipfad analog

Doku
- [ ] README.md / README.de.md: Tool-Name, install-URLs, Screenshots-Captions
- [ ] docs/index.html: title, og:title, alle ``sitemap-generator``-Erwaehnungen
- [ ] PHASE-PLAN.md: dieser Eintrag dann als ``[x]`` markieren

Branding fuer handmade-software.de
- [ ] Free-Variante: ``Sitemap Tracker`` (Phase-1-Funktionalitaet)
- [ ] PRO-Variante: ``Sitemap Tracker Pro`` mit Phase-2-Features

**Release-Strategie:** Ein einziger ``release: v2.0.0``-Cut. MAJOR-Bump
ist gerechtfertigt — Package-Name aendert sich, alte Install-Pfade
brechen (mit Redirect). User mit ``pip install -e .`` muessen einmal
neu installieren; mit dem One-Click-Installer ist es automatisch.

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
