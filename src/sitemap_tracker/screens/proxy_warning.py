"""Modal-Screen "Proxy / Gateway erkannt".

Wird am Ende eines Crawls angezeigt, wenn ein vorgeschaltetes Proxy-/Auth-
Gateway (z. B. Zscaler) erkannt wurde - also ein grosser Anteil der Seiten
extern auf einen fremden Host umleitet. Erklaert dem Nutzer, warum der Crawl
unvollstaendig ist und was zu tun ist.
"""

from __future__ import annotations

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from ..i18n import t
from ..services.proxy_detect import ProxyDetection


class ProxyWarningScreen(ModalScreen[None]):
    """Warnt, dass ein Proxy-/Auth-Gateway den Crawl abgefangen hat."""

    DEFAULT_CSS = """
    ProxyWarningScreen {
        align: center middle;
    }

    ProxyWarningScreen > Vertical {
        width: 80%;
        max-width: 90;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $warning;
        padding: 1 2;
    }

    ProxyWarningScreen #proxy-title {
        height: auto;
        max-height: 5;
        content-align: center middle;
        text-style: bold;
        background: $warning;
        color: auto;
        margin-bottom: 1;
        padding: 1 2;
    }

    ProxyWarningScreen #proxy-scroll {
        height: auto;
        max-height: 90%;
    }

    ProxyWarningScreen #proxy-content {
        height: auto;
        padding: 1;
    }

    ProxyWarningScreen #proxy-buttons {
        dock: bottom;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    ProxyWarningScreen #proxy-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q,Q", "close", "Close"),
    ]

    def __init__(self, detection: ProxyDetection, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._detection = detection

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(t("proxy.title"), id="proxy-title")
            with VerticalScroll(id="proxy-scroll"):
                yield Static(self._build_content(), id="proxy-content")
            with Horizontal(id="proxy-buttons"):
                yield Button(t("binding.close"), variant="primary", id="proxy-close")

    def _build_content(self) -> Text:
        d = self._detection
        text = Text()
        text.append(t("proxy.intro"), style="bold")
        text.append("\n\n")
        text.append(t("proxy.host_label") + " ", style="dim")
        text.append(d.host, style="bold yellow")
        text.append("\n\n")
        text.append(t("proxy.advice"))
        return text

    @on(Button.Pressed, "#proxy-close")
    def _on_close_button(self) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
