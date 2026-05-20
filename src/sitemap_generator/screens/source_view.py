"""Modal-Dialog, der den HTML-Quellcode einer verweisenden Seite zeigt.

Rendert das HTML ueber Rich's ``Syntax`` (Pygments) mit Zeilennummern und
hervorgehobener Fundstelle. Read-only — bewusst nicht editierbar; die
TextArea-Loesung scheiterte am tree-sitter-html-Build, der nicht
standardmaessig in Textual mitkommt.
"""

from __future__ import annotations

import contextlib

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

    def _build_syntax(self) -> Syntax:
        """Baut die ``Syntax``-Renderable mit Pygments-Highlight + Fundstelle.

        ``highlight_lines`` markiert die Treffer-Zeile mit dem Theme-Background
        — exakt das, was wir wollen, um den User direkt auf die richtige
        Stelle zu lenken.
        """
        highlight = {self._line} if self._line > 0 else set()
        return Syntax(
            self._html,
            "html",
            line_numbers=True,
            highlight_lines=highlight,
            theme="monokai",
            word_wrap=False,
            indent_guides=False,
            background_color="default",
        )

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
