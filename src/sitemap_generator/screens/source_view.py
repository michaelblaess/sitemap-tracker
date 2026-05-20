"""Modal-Dialog, der den HTML-Quellcode einer verweisenden Seite zeigt.

Springt zur Zeile, an der der defekte Link im HTML auftaucht — read-only,
mit Zeilennummern und (sofern Tree-Sitter-HTML verfuegbar) Syntax-
Highlighting.
"""

from __future__ import annotations

import contextlib

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static, TextArea

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
    SourceViewScreen TextArea {
        height: 1fr;
    }
    /* Sichtbare Markierung fuer den gefundenen Treffer. */
    SourceViewScreen TextArea > .text-area--selection {
        background: $warning 80%;
        color: $background;
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
            # Tree-Sitter-HTML ist optional — bei Fehlen faellt TextArea
            # still auf no-highlight zurueck und zeigt nur Zeilennummern.
            try:
                ta = TextArea.code_editor(
                    self._html,
                    language="html",
                    read_only=True,
                    show_line_numbers=True,
                )
            except Exception:
                ta = TextArea(self._html, read_only=True, show_line_numbers=True)
            yield ta
            with Horizontal(id="button-row"):
                yield Button(t("source_view.close"), variant="primary", id="close")

    def on_mount(self) -> None:
        if self._line > 0:
            with contextlib.suppress(Exception):
                from textual.widgets.text_area import Selection

                ta = self.query_one(TextArea)
                col = max(0, self._column - 1)
                start = (self._line - 1, col)
                if self._length > 0:
                    end = (self._line - 1, col + self._length)
                    ta.selection = Selection(start=start, end=end)
                else:
                    ta.cursor_location = start
                ta.scroll_cursor_visible(center=True, animate=False)
                ta.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
