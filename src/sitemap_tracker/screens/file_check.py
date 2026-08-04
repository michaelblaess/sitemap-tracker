"""Modal-Screen "Dateien pruefen": Erreichbarkeit verlinkter Dokumente.

Der Crawl selbst holt PDF, Office-Dokumente und Archive nicht ab - sie haben
keine Folgelinks und wuerden nur Bandbreite kosten. Damit faellt aber auch
nicht auf, wenn eines davon tot ist. Dieser Dialog nimmt die beim Crawl
eingesammelten Datei-Links, filtert sie nach Endung und prueft sie per HEAD.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Static

from ..i18n import t
from ..services.file_checker import FileChecker, filter_by_extensions, parse_extensions

if TYPE_CHECKING:
    from ..services.file_checker import FileCheckResult, FileCheckSummary

# Vorgabe, wenn der Anwender nichts eintippt.
STANDARD_ENDUNG = "pdf"


class FileCheckScreen(ModalScreen[None]):
    """Fragt die Endungen ab, prueft die Dateien und zeigt das Ergebnis.

    Der Dialog bleibt nach der Pruefung offen - das Ergebnis ist der Zweck,
    nicht ein Rueckgabewert. Die Treffer wandern zusaetzlich ins Log der App,
    damit sie nach dem Schliessen nicht verloren sind.
    """

    DEFAULT_CSS = """
    FileCheckScreen {
        align: center middle;
    }

    FileCheckScreen > Vertical {
        width: 90%;
        max-width: 120;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    FileCheckScreen #fc-title {
        height: auto;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: auto;
        margin-bottom: 1;
    }

    FileCheckScreen #fc-row {
        height: auto;
        margin-bottom: 1;
    }

    FileCheckScreen #fc-row Label,
    FileCheckScreen #fc-label {
        width: 14;
        padding: 1 1 0 0;
    }

    FileCheckScreen #fc-ext {
        width: 1fr;
    }

    FileCheckScreen #fc-info {
        height: auto;
        margin-bottom: 1;
    }

    FileCheckScreen #fc-scroll {
        height: auto;
        max-height: 60%;
    }

    FileCheckScreen #fc-hint {
        height: auto;
        color: $text-muted;
        margin-top: 1;
    }

    FileCheckScreen DataTable {
        height: auto;
        max-height: 20;
    }

    FileCheckScreen #fc-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    FileCheckScreen #fc-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "close"),
        Binding("ctrl+r", "run", "run"),
        Binding("ctrl+c", "copy", "copy", priority=True),
    ]

    def __init__(self, links: dict[str, str], checker: FileChecker) -> None:
        """
        Args:
            links:
                Alle beim Crawl gefundenen Datei-Links als ``URL -> Fundort``.
            checker:
                Der vorkonfigurierte Pruefer (Drosselung, Proxy, Timeout).
        """
        super().__init__()
        self._links = links
        self._checker = checker
        self._laeuft = False
        self._summary: FileCheckSummary | None = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(t("filecheck.title"), id="fc-title")
            with Horizontal(id="fc-row"):
                yield Static(t("filecheck.ext_label"), id="fc-label")
                yield Input(
                    value=STANDARD_ENDUNG,
                    placeholder=t("filecheck.ext_placeholder"),
                    id="fc-ext",
                )
            yield Static(self._info_text(), id="fc-info")
            with VerticalScroll(id="fc-scroll"):
                yield DataTable(id="fc-table", cursor_type="row", zebra_stripes=True)
            yield Static(t("filecheck.row_hint"), id="fc-hint")
            with Horizontal(id="fc-buttons"):
                yield Button(t("filecheck.btn_run"), variant="primary", id="fc-run")
                yield Button(t("filecheck.btn_copy"), variant="default", id="fc-copy")
                yield Button(t("binding.close"), variant="default", id="fc-close")

    def on_mount(self) -> None:
        """Richtet Tabelle und Fokus ein.

        Verzoegert ueber ``call_after_refresh``: die Tabelle liegt in einem
        VerticalScroll, und dessen Kinder sind zum Zeitpunkt von ``on_mount``
        noch nicht im DOM - ein direktes ``query_one`` scheitert dort mit
        NoMatches.
        """
        self.call_after_refresh(self._init_widgets)

    def _init_widgets(self) -> None:
        """Legt die Tabellenspalten an und setzt den Fokus ins Eingabefeld."""
        tabelle = self.query_one("#fc-table", DataTable)
        if not tabelle.columns:
            tabelle.add_columns(
                t("filecheck.col_status"),
                t("filecheck.col_size"),
                t("filecheck.col_url"),
                t("filecheck.col_source"),
            )
        tabelle.display = False
        self.query_one("#fc-ext", Input).focus()

    @on(Input.Changed, "#fc-ext")
    def _on_ext_changed(self) -> None:
        """Zeigt sofort, wie viele Dateien die Eingabe trifft."""
        self.query_one("#fc-info", Static).update(self._info_text())

    def _eingabe(self) -> str:
        """Aktueller Inhalt des Endungsfelds.

        Faellt auf die Vorgabe zurueck, solange das Feld noch nicht im DOM ist -
        ``compose`` baut die Infozeile, bevor das Eingabefeld gemountet wurde,
        und ein ungeschuetztes ``query_one`` wuerde dort die gesamte
        ``compose``-Methode abbrechen (der Dialog kaeme leer hoch).
        """
        try:
            return self.query_one("#fc-ext", Input).value
        except NoMatches:
            return STANDARD_ENDUNG

    def _gefiltert(self) -> dict[str, str]:
        """Die aktuell durch die Eingabe ausgewaehlten Dateien."""
        return filter_by_extensions(self._links, parse_extensions(self._eingabe()))

    def _info_text(self) -> Text:
        """Zeile ueber der Tabelle: gefunden / ausgewaehlt bzw. Ergebnis."""
        if self._summary is not None:
            fehler = len(self._summary.failed)
            text = Text()
            text.append(
                t("filecheck.result", total=self._summary.total, ok=self._summary.ok_count),
            )
            if fehler:
                text.append("  ")
                text.append(t("filecheck.result_failed", count=fehler), style="bold red")
            return text
        return Text(
            t("filecheck.info", total=len(self._links), selected=len(self._gefiltert())),
            style="dim",
        )

    @on(Button.Pressed, "#fc-run")
    def _on_run(self) -> None:
        self.action_run()

    @on(Button.Pressed, "#fc-copy")
    def _on_copy(self) -> None:
        self.action_copy()

    @on(Button.Pressed, "#fc-close")
    def _on_close(self) -> None:
        self.action_close()

    @on(DataTable.RowSelected, "#fc-table")
    def _on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Kopiert die URL der gewaehlten Zeile.

        In der Tabelle ist eine lange URL abgeschnitten. Sie dort nur zu sehen
        nuetzt nichts - man will sie im Browser aufrufen, und dafuer muss sie
        vollstaendig in die Zwischenablage.
        """
        if self._summary is None or event.cursor_row >= len(self._summary.results):
            return
        url = self._summary.results[event.cursor_row].url
        self.app.copy_to_clipboard(url)
        self.app.notify(t("filecheck.copied_one", url=url))

    def action_copy(self) -> None:
        """Legt die gesamte Ergebnisliste als Text in die Zwischenablage."""
        if self._summary is None or not self._summary.results:
            self.app.notify(t("filecheck.nothing_to_copy"), severity="warning")
            return
        zeilen = [self._als_text(e) for e in self._summary.results]
        self.app.copy_to_clipboard("\n".join(zeilen))
        self.app.notify(t("filecheck.copied", count=len(zeilen)))

    @staticmethod
    def _als_text(ergebnis: FileCheckResult) -> str:
        """Eine Ergebniszeile als Klartext - tabgetrennt, gut einfuegbar."""
        status = ergebnis.error_message or str(ergebnis.status_code)
        groesse = ergebnis.size_display if ergebnis.ok else ""
        return f"{status}\t{groesse}\t{ergebnis.url}\t{ergebnis.fundort}"

    def action_close(self) -> None:
        if self._laeuft:
            self._checker.cancel()
        self.dismiss(None)

    def action_run(self) -> None:
        """Startet die Pruefung der ausgewaehlten Dateien."""
        if self._laeuft:
            return
        auswahl = self._gefiltert()
        if not auswahl:
            self.app.notify(t("filecheck.nothing_selected"), severity="warning")
            return
        self._laeuft = True
        self._summary = None
        self.query_one("#fc-run", Button).disabled = True
        self.query_one("#fc-info", Static).update(
            Text(t("filecheck.running", total=len(auswahl)), style="bold")
        )
        self._pruefen(auswahl)

    @work(exclusive=True)
    async def _pruefen(self, auswahl: dict[str, str]) -> None:
        """Fuehrt die Pruefung aus und traegt das Ergebnis ein."""
        gesamt = len(auswahl)

        def fortschritt(fertig: int, _gesamt: int) -> None:
            # Laeuft im Event-Loop (Worker ist async) - direkter Zugriff ok.
            self.query_one("#fc-info", Static).update(
                Text(t("filecheck.progress", done=fertig, total=gesamt), style="bold")
            )

        summary = await self._checker.check(auswahl, on_progress=fortschritt)
        self._summary = summary
        self._laeuft = False
        self.query_one("#fc-run", Button).disabled = False
        self._fuelle_tabelle(summary)
        self.query_one("#fc-info", Static).update(self._info_text())
        self.post_message(self.Finished(summary))

    def _fuelle_tabelle(self, summary: FileCheckSummary) -> None:
        """Traegt die Ergebnisse ein - Fehler zuerst, rot markiert."""
        tabelle = self.query_one("#fc-table", DataTable)
        tabelle.clear()
        for ergebnis in summary.results:
            tabelle.add_row(*self._zeile(ergebnis))
        tabelle.display = bool(summary.results)

    @staticmethod
    def _zeile(ergebnis: FileCheckResult) -> tuple[Text, Text, Text, Text]:
        """Baut eine Tabellenzeile - Status farbig, Fehlertext statt Code."""
        if ergebnis.error_message:
            status = Text(t("filecheck.status_error"), style="bold red")
        elif ergebnis.ok:
            status = Text(str(ergebnis.status_code), style="green")
        else:
            status = Text(str(ergebnis.status_code), style="bold red")
        hinweis = ergebnis.error_message or ergebnis.fundort
        # Groesse nur bei erreichbaren Dateien - bei einem 404 waere es die
        # Groesse der Fehlerseite, und "404, 155 KB" liest sich widerspruechlich.
        groesse = ergebnis.size_display if ergebnis.ok else ""
        return (
            status,
            Text(groesse, style="dim"),
            Text(ergebnis.url, overflow="ellipsis", no_wrap=True),
            Text(hinweis, overflow="ellipsis", no_wrap=True, style="dim"),
        )

    class Finished(Message):
        """Meldet der App das Ergebnis, damit es ins Log wandern kann."""

        def __init__(self, summary: FileCheckSummary) -> None:
            super().__init__()
            self.summary = summary
