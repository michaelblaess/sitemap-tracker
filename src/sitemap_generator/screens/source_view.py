"""Modal-Dialog, der den HTML-Quellcode einer verweisenden Seite zeigt.

Rendert das HTML ueber Rich's ``Syntax`` (Pygments) mit Zeilennummern und
hervorgehobener Fundstelle. Read-only — bewusst nicht editierbar; die
TextArea-Loesung scheiterte am tree-sitter-html-Build, der nicht
standardmaessig in Textual mitkommt.
"""

from __future__ import annotations

import contextlib

from rich.console import Group, RenderableType
from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ..i18n import t


class SourceViewScreen(ModalScreen[None]):
    """Zeigt das HTML einer verweisenden Seite + scrollt zum Link-Treffer."""

    DEFAULT_CSS = """
    SourceViewScreen {
        align: center middle;
    }
    SourceViewScreen > Vertical {
        width: 95%;
        height: 90%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }
    SourceViewScreen #source-title {
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $accent;
        color: auto;
        margin-bottom: 1;
    }
    SourceViewScreen #source-info {
        height: auto;
        padding: 0 1;
        color: $text-muted;
        margin-bottom: 1;
    }
    SourceViewScreen #src-scroll {
        height: 1fr;
        border: solid $surface-lighten-2;
    }
    SourceViewScreen #src-content {
        height: auto;
        width: auto;
        padding: 0 1;
    }
    SourceViewScreen #button-row {
        height: 3;
        align: center middle;
        margin-top: 1;
    }
    """

    BINDINGS = [Binding("escape", "close", "Schliessen")]

    def __init__(
        self,
        *,
        html: str,
        line: int,
        source_url: str,
        target_url: str,
        column: int = 0,
        length: int = 0,
    ) -> None:
        super().__init__()
        self._html = html
        self._line = line
        self._column = column
        self._length = length
        self._source_url = source_url
        self._target_url = target_url

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(t("source_view.title"), id="source-title")
            info = f"{t('source_view.source')}: {self._source_url}\n{t('source_view.target')}: {self._target_url}"
            if self._line > 0:
                info += f"\n{t('source_view.found_line', line=self._line)}"
            else:
                info += f"\n{t('source_view.not_found')}"
            yield Static(info, id="source-info")
            with ScrollableContainer(id="src-scroll"):
                yield Static(self._build_syntax(), id="src-content")
            with Horizontal(id="button-row"):
                yield Button(t("source_view.close"), variant="primary", id="close")

    # Theme + Highlight-Farbe — github-dark als Basis, ein warmer
    # Gold-Ton (#3a2f00) fuer die Treffer-Zeile, deutlich abgesetzt
    # vom Theme-Background.
    _THEME = "github-dark"
    _HIGHLIGHT_BG = "#3a2f00"

    def _build_syntax(self) -> RenderableType:
        """Baut die Code-Anzeige mit Pygments-Highlight + sichtbarer Fundstelle.

        Rich's ``highlight_lines`` zeichnet nur einen schmalen ``>``-Marker
        am linken Rand — kein vollflaechiges Background-Highlight. Daher
        rendern wir die Treffer-Zeile in einem eigenen ``Syntax``-Block mit
        explizitem ``background_color``, eingebettet zwischen den ``Syntax``-
        Bloecken fuer Code davor und danach. ``start_line=`` haelt die
        Zeilennummerierung durchgaengig.
        """
        if self._line <= 0:
            return Syntax(
                self._html,
                "html",
                line_numbers=True,
                theme=self._THEME,
                word_wrap=False,
                indent_guides=False,
            )
        lines = self._html.split("\n")
        idx = self._line - 1
        if idx >= len(lines):
            return Syntax(
                self._html,
                "html",
                line_numbers=True,
                theme=self._THEME,
                word_wrap=False,
                indent_guides=False,
            )
        before = "\n".join(lines[:idx])
        target = lines[idx]
        after = "\n".join(lines[idx + 1 :])
        blocks: list[RenderableType] = []
        if before:
            blocks.append(
                Syntax(
                    before,
                    "html",
                    line_numbers=True,
                    theme=self._THEME,
                    word_wrap=False,
                    indent_guides=False,
                    start_line=1,
                )
            )
        blocks.append(
            Syntax(
                target,
                "html",
                line_numbers=True,
                theme=self._THEME,
                word_wrap=False,
                indent_guides=False,
                start_line=self._line,
                background_color=self._HIGHLIGHT_BG,
            )
        )
        if after:
            blocks.append(
                Syntax(
                    after,
                    "html",
                    line_numbers=True,
                    theme=self._THEME,
                    word_wrap=False,
                    indent_guides=False,
                    start_line=self._line + 1,
                )
            )
        return Group(*blocks)

    def on_mount(self) -> None:
        # Scroll-Position auf die Fundstelle — verzoegert, bis das erste
        # Layout fertig ist; sonst kennt der ScrollableContainer seine
        # Sichtbarkeitsregion noch nicht.
        if self._line > 0:
            self.call_after_refresh(self._scroll_to_match)

    def _scroll_to_match(self) -> None:
        """Scrollt so, dass die Treffer-Zeile zentriert sichtbar wird."""
        with contextlib.suppress(Exception):
            scroll = self.query_one("#src-scroll", ScrollableContainer)
            target_y = max(0, self._line - 5)
            scroll.scroll_to(y=target_y, animate=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
