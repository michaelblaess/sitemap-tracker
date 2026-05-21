# Sitemap Tracker - Intro-Demo
# Render NUR unter WSL/Linux/macOS - vhs scheitert auf Windows-Host nativ.
#   bash demo/render-wsl.sh        (aus WSL)
#   .\tape.ps1 intro               (aus Windows, ruft WSL)
#
# Story: Start mit URL -> Settings (Concurrency 32) -> Crawl -> nur Fehler
#        -> Fehlerseite markieren (Vorschau laedt) -> v = Im Quelltext zeigen.
#
# Settings-Tastenfolge ist headless verifiziert (s -> right -> tab x4 landet
# auf 'Parallele Requests'). Aendert sich nur, wenn die Feldreihenfolge im
# Crawl-Tab umsortiert wird.
#
# TUNING nach dem ERSTEN Render (datenabhaengig):
#   [C] 'Down N' so anpassen, dass eine 4xx/5xx-Zeile MIT verweisender Seite
#       markiert ist - im Footer erscheint dann 'v Im Quelltext zeigen'.
#       Ohne so eine Zeile tut 'v' nichts und der Quelltext-Wait laeuft in
#       den Timeout (= recording failed).

Output demo/intro.gif

Require uv

Set Shell "bash"
Set FontSize 14
Set Width 1500
Set Height 920
Set Padding 18
Set Margin 18
Set MarginFill "#1e1e2e"
Set BorderRadius 8
Set WindowBar Colorful
Set WindowBarSize 40
Set Theme "Catppuccin Mocha"
Set TypingSpeed 80ms
Set LoopOffset 5%
Set CursorBlink false

# --- Setup (nicht im Video): App mit URL starten, auf TUI warten ---
Hide
Type "clear"
Enter
Type "uv run sitemap-tracker --lang en https://textual.textualize.io/"
Enter
Wait+Screen@40s /Sitemap Tracker/
Sleep 600ms
Show

# 1. Startzustand kurz zeigen
Sleep 1800ms

# 2. Settings oeffnen: Vorschau einschalten + Concurrency auf 32
#    (Vorschau ist per Default AUS - ohne sie bleibt das Panel rechts leer.)
Type@180ms "s"
Wait+Screen@10s /Einstellungen|Settings/
Sleep 700ms
Right              # Tab-Leiste: Sprache -> Crawl
Sleep 400ms
Tab                # VerticalScroll-Container (scrollbarer Tab-Inhalt)
Tab                # robots
Tab                # playwright
Tab                # -> Seiten-Vorschau
Sleep 300ms
Space              # Vorschau aktivieren
Sleep 600ms
Tab                # -> Parallele Requests
Sleep 400ms
Backspace 4        # Feld leeren (Default "8")
Type@140ms "16"
Sleep 800ms
Ctrl+S             # Speichern
Wait+Screen@8s /gespeichert|saved/
Sleep 1000ms

# 3. Crawl starten: 'c' oeffnet den URL-Dialog (mit der URL vorbelegt),
#    Enter bestaetigt -> Crawl laeuft.
Type@180ms "c"
Wait+Screen@10s /URL eingeben|Enter URL/
Sleep 800ms
Enter              # vorbelegte URL uebernehmen -> Crawl startet
Wait+Screen@180s /abgeschlossen|completed/
Sleep 1500ms

# 4. Nur Fehler anzeigen
Type@180ms "e"
Sleep 1800ms

# 5. Fehlerseite markieren -> Vorschau rechts laedt [C]
Down 1
Sleep 800ms
Down 1
Sleep 3000ms       # Screenshot der Vorschau rendern lassen

# 6. v = Im Quelltext der verweisenden Seite zeigen
Type@180ms "v"
Wait+Screen@20s /Quell|source|Zeile|line/
Sleep 3500ms

# Quelltext-Ansicht schliessen
Escape
Sleep 1200ms

# --- Cleanup (nicht im Video) ---
Hide
Type "q"
Sleep 300ms
