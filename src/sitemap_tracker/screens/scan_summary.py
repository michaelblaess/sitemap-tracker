"""Modal-Screen "Crawl-Zusammenfassung": Site-Score + Findings als Tabelle.

Wird am Ende eines Crawls angezeigt: ein Gesamtscore (0-100 %, Anteil
fehlerfreier Seiten) und eine tabellarische Findings-Uebersicht (gecrawlte
Seiten, fehlerfreie/fehlerhafte Seiten, HTTP-Status-Verteilung, gefundene
interne Links).
"""

from __future__ import annotations

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ..i18n import t
from ..services.site_score import SiteScore


def _score_style(score: int) -> str:
    """Farbstil zum Score (gruen/gelb/rot)."""
    if score >= 75:
        return "bold green"
    if score >= 45:
        return "bold yellow"
    return "bold red"


class ScanSummaryScreen(ModalScreen[str | None]):
    """Zeigt Site-Score und Findings (tabellarisch) nach einem Crawl.

    Rueckgabe ueber ``dismiss``:
    - ``"save"`` wenn der Nutzer "Sitemap speichern" gewaehlt hat,
    - ``None`` beim Schliessen (Button, Esc, q).
    """

    DEFAULT_CSS = """
    ScanSummaryScreen {
        align: center middle;
    }

    ScanSummaryScreen > Vertical {
        width: 80%;
        max-width: 90;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    ScanSummaryScreen #summary-title {
        height: auto;
        max-height: 5;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: auto;
        margin-bottom: 1;
        padding: 1 2;
    }

    ScanSummaryScreen #summary-scroll {
        /* Auf Inhaltshoehe schrumpfen (kein 1fr - das fuellt sonst den ganzen
           verfuegbaren Platz und draengt den Button mit grosser Luecke nach
           unten). max-height: 90% kappt bei langem Inhalt -> der Bereich
           scrollt; bei kurzem Inhalt sitzt der (unten angedockte) Button direkt
           darunter, ohne Luecke. */
        height: auto;
        max-height: 90%;
    }

    ScanSummaryScreen #summary-content {
        height: auto;
        padding: 1;
    }

    ScanSummaryScreen #summary-buttons {
        /* Unten angedockt: bleibt bei langem (scrollendem) Inhalt immer sichtbar
           und sitzt bei kurzem Inhalt direkt unter dem Scroll-Bereich. */
        dock: bottom;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    ScanSummaryScreen #summary-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q,Q", "close", "Close"),
    ]

    def __init__(self, score: SiteScore, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._score = score

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(t("summary.title"), id="summary-title")
            with VerticalScroll(id="summary-scroll"):
                yield Static(self._build_content(), id="summary-content")
            with Horizontal(id="summary-buttons"):
                yield Button(t("summary.btn_save_sitemap"), variant="primary", id="summary-save")
                yield Button(t("binding.close"), variant="default", id="summary-close")

    def _score_text(self) -> Text:
        """Baut die grosse Score-Zeile inkl. Bewertungs-Hinweis."""
        s = self._score
        text = Text()
        text.append(t("summary.score_label") + " ", style="bold")
        text.append(f"{s.score} %", style=_score_style(s.score))
        text.append(f"  ({s.grade})", style=_score_style(s.score))
        text.append("\n")
        text.append(
            t("summary.score_breakdown", clean=s.clean_pages, total=s.total_pages),
            style="dim",
        )
        return text

    def _findings_table(self) -> Table:
        """Baut die Findings als zweispaltige Label/Wert-Tabelle."""
        s = self._score
        table = Table(box=None, show_header=False, pad_edge=False, padding=(0, 3, 0, 0))
        table.add_column(justify="left")
        table.add_column(justify="right")

        def row(label: str, value: int, value_style: str = "") -> None:
            table.add_row(label, Text(str(value), style=value_style))

        # Eine Fehlerzahl > 0 rot einfaerben, fehlerfreie Seiten gruen.
        err_style = "bold red"
        row(t("summary.row_crawled"), s.total_pages)
        row(t("summary.row_clean"), s.clean_pages, "green" if s.clean_pages else "")
        row(t("summary.row_errors"), s.pages_with_errors, err_style if s.pages_with_errors else "dim")
        row(t("summary.row_2xx"), s.total_2xx)
        row(t("summary.row_3xx"), s.total_3xx)
        row(t("summary.row_4xx"), s.total_4xx, err_style if s.total_4xx else "dim")
        row(t("summary.row_5xx"), s.total_5xx, err_style if s.total_5xx else "dim")
        row(t("summary.row_links"), s.total_links)
        row(t("summary.row_sitemap_urls"), s.sitemap_urls, "bold")
        row(
            t("summary.row_resolved_redirects"),
            s.resolved_redirects,
            "cyan" if s.resolved_redirects else "dim",
        )
        return table

    def _build_content(self) -> RenderableType:
        """Score-Zeile, Findings-Ueberschrift und Findings-Tabelle als Gruppe.

        Ergaenzt oben eine Warnung, wenn der Lauf keine einzige 200er-Seite
        ergeben hat - dann ist die Sitemap zwangslaeufig leer, und der Grund
        gehoert genau dorthin, wo der Anwender nach dem Crawl hinsieht.
        """
        teile: list[RenderableType] = [self._score_text(), Text("")]
        warnung = self._warning_text()
        if warnung is not None:
            teile.extend((warnung, Text("")))
        teile.extend((Text(t("summary.findings"), style="bold underline"), self._findings_table()))
        return Group(*teile)

    def _warning_text(self) -> Text | None:
        """Baut die Warnzeile fuer den Fall "alles weitergeleitet".

        Returns:
            Die Warnung, oder None wenn der Lauf unauffaellig war.
        """
        s = self._score
        if s.total_2xx or not s.total_3xx:
            return None
        return Text(
            t("summary.warn_all_redirected", count=s.total_3xx),
            style="bold red",
        )

    @on(Button.Pressed, "#summary-save")
    def _on_save_button(self) -> None:
        self.dismiss("save")

    @on(Button.Pressed, "#summary-close")
    def _on_close_button(self) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
