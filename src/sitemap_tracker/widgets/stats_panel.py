"""Statistik-Panel Widget - Zeigt die URL-Detailansicht an."""

from __future__ import annotations

from urllib.parse import quote, urlparse, urlunparse

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from ..i18n import t
from ..models.crawl_result import CrawlResult, SeoInfo
from ..services.page_analysis import detect_issues


def _sanitize_url(url: str) -> str:
    """Bereinigt eine URL fuer Terminal-CTRL+Click-Kompatibilitaet.

    Kodiert Non-ASCII-Zeichen (Umlaute etc.) als Percent-Encoding,
    damit Terminals die URL beim CTRL+Click korrekt erkennen.
    Klammern werden ebenfalls kodiert.

    Args:
        url: Die zu bereinigende URL.

    Returns:
        Bereinigte URL mit Percent-Encoding fuer Non-ASCII-Zeichen.
    """
    parsed = urlparse(url)
    # Pfad und Query separat kodieren, bereits kodierte Zeichen beibehalten.
    # '%' muss safe sein, damit bereits kodierte Sequenzen (%C3%A4 etc.)
    # nicht doppelt kodiert werden (%25C3%25A4).
    safe_path = quote(parsed.path, safe="/:@!$&'*+,;=-._~%")
    safe_query = quote(parsed.query, safe="/:@!$&'*+,;=-._~?=%")
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            safe_path,
            parsed.params,
            safe_query,
            parsed.fragment,
        )
    )


def _format_load_time(ms: float) -> str:
    """Formatiert eine Ladezeit (de-DE).

    Ab einer Sekunde als Sekundenwert mit einer Nachkommastelle
    (z.B. "1,8s"), darunter in Millisekunden (z.B. "839ms").

    Args:
        ms: Ladezeit in Millisekunden.

    Returns:
        Formatierte Ladezeit, "-" wenn keine Zeit vorliegt.
    """
    if ms <= 0:
        return "-"
    if ms >= 1000:
        return f"{ms / 1000:.1f}".replace(".", ",") + "s"
    return f"{ms:.0f}ms"


def _format_size(num_bytes: int) -> str:
    """Formatiert eine Byte-Groesse als B / KB / MB (de-DE).

    Args:
        num_bytes: Groesse in Bytes.

    Returns:
        Formatierte Groesse, "-" wenn keine Groesse vorliegt.
    """
    if num_bytes <= 0:
        return "-"
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f}".replace(".", ",") + " KB"
    return f"{num_bytes / (1024 * 1024):.1f}".replace(".", ",") + " MB"


class StatsPanel(VerticalScroll):
    """Panel mit URL-Detail-Ansicht (scrollbar bei langem Inhalt)."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected_result: CrawlResult | None = None

    def compose(self) -> ComposeResult:
        """Erstellt das Panel-Layout."""
        yield Static("", id="url-detail")

    def _detail_value(
        self,
        value: str,
        value_style: str = "",
        link_url: str = "",
    ) -> Text:
        """Erzeugt das Wert-Renderable einer Detail-Zeile (fold-Umbruch).

        Bei ``link_url`` wird der Wert ueber das App-weite Klick-Mixin als
        Textual-Action-Markup eingebettet — klickbar ohne CTRL, mit Hover-
        Highlight. Faellt auf einen OSC-8-Link zurueck, wenn die App das
        Mixin nicht hat (z.B. in Unit-Tests ohne run_test).

        Args:
            value: Der anzuzeigende Wert.
            value_style: Optionaler Rich-Style fuer den Wert.
            link_url: Optionale URL oder Pfad — macht den Wert klickbar.

        Returns:
            Text-Objekt mit fold-overflow (nur der Wert, ohne Label).
        """
        if link_url:
            link_markup_fn = getattr(self.app, "link_markup", None)
            if callable(link_markup_fn):
                sub = Text.from_markup(link_markup_fn(value, link_url), overflow="fold")
                if value_style:
                    sub.stylize(value_style)
                return sub
            # Fallback: OSC-8 + CTRL+Klick
            style = f"{value_style} link {link_url}".strip()
            return Text(value, style=style, overflow="fold")
        if value_style:
            return Text(value, style=value_style, overflow="fold")
        return Text(value, overflow="fold")

    @staticmethod
    def _kv_table(rows: list[tuple[str, Text]]) -> Table:
        """Baut ein 2-spaltiges Grid (Label | Wert).

        Der Wert bricht innerhalb seiner eigenen Spalte um (haengender
        Einzug) und laeuft NICHT mehr in die Label-Spalte hinein. Die
        Label-Spalte richtet sich nach dem laengsten Label des Panels.

        Args:
            rows: Liste aus (Label, Wert-Renderable)-Paaren.

        Returns:
            Ein expandierendes Rich-Grid mit zwei Spalten.
        """
        grid = Table.grid(expand=True, padding=(0, 1))
        grid.add_column(no_wrap=True, style="dim", justify="left")
        grid.add_column(ratio=1, overflow="fold")
        for label, value in rows:
            grid.add_row(label, value)
        return grid

    @staticmethod
    def _panel(title: str, body: list, border_style: str = "grey37") -> Panel:
        """Baut ein bordiertes Panel mit linksbuendigem Titel.

        Args:
            title: Der Panel-Titel.
            body: Die Renderables im Panel.
            border_style: Rich-Style fuer den Rahmen.

        Returns:
            Das fertige Panel.
        """
        return Panel(
            Group(*body),
            title=f" {title} ",
            title_align="left",
            border_style=border_style,
            padding=(0, 1),
        )

    def _seo_rows(self, seo: SeoInfo) -> list[tuple[str, Text]]:
        """Baut die SEO-Detailzeilen als Label/Wert-Paare.

        Args:
            seo:
                Die SEO-Daten der Seite.

        Returns:
            Liste aus (Label, Wert)-Paaren, leer wenn keine SEO-Daten vorliegen.
        """
        if not (seo.title or seo.description or seo.h1_count):
            return []
        title = f"{seo.title}  ({len(seo.title)})" if seo.title else "-"
        description = f"{seo.description}  ({len(seo.description)})" if seo.description else "-"
        viewport = t("detail.form_yes") if seo.has_viewport else t("detail.form_no")
        rows: list[tuple[str, Text]] = [
            (t("detail.seo_title"), self._detail_value(title)),
            (t("detail.seo_desc"), self._detail_value(description)),
            (t("detail.seo_h1"), self._detail_value(str(seo.h1_count))),
            (t("detail.seo_lang"), self._detail_value(seo.lang or "-")),
            (t("detail.seo_canonical"), self._detail_value(_sanitize_url(seo.canonical) if seo.canonical else "-")),
            (t("detail.seo_viewport"), self._detail_value(viewport)),
        ]
        if seo.robots:
            rows.append((t("detail.seo_robots"), self._detail_value(seo.robots)))
        if seo.og_tags:
            rows.append((t("detail.seo_og"), self._detail_value(", ".join(seo.og_tags))))
        return rows

    def _page_panel(self, result: CrawlResult) -> Panel:
        """Baut das Panel mit den Basis-Infos der Seite."""
        safe_url = _sanitize_url(result.url)
        rows: list[tuple[str, Text]] = [
            (t("detail.url"), self._detail_value(safe_url, "bold", link_url=safe_url)),
            (t("detail.status"), self._detail_value(f"{result.status_icon} {result.status.value}")),
        ]
        if result.redirect_url:
            safe_redirect = _sanitize_url(result.redirect_url)
            rows.append((t("detail.redirect"), self._detail_value(safe_redirect, link_url=safe_redirect)))
        rows.append(
            (t("detail.http"), self._detail_value(str(result.http_status_code) if result.http_status_code else "-"))
        )
        rows.append((t("detail.depth"), self._detail_value(str(result.depth))))
        rows.append((t("detail.links"), self._detail_value(str(result.links_found))))
        rows.append((t("detail.load_time"), self._detail_value(_format_load_time(result.load_time_ms))))
        rows.append((t("detail.size"), self._detail_value(_format_size(result.page_size))))
        form_value = t("detail.form_yes") if result.has_form else t("detail.form_no")
        rows.append((t("detail.form"), self._detail_value(form_value, "green" if result.has_form else "dim")))
        if result.content_type:
            rows.append((t("detail.content_type"), self._detail_value(result.content_type)))
        if result.last_modified:
            rows.append((t("detail.last_modified"), self._detail_value(result.last_modified)))
        if result.parent_url:
            safe_parent = _sanitize_url(result.parent_url)
            rows.append((t("detail.parent"), self._detail_value(safe_parent, link_url=safe_parent)))
        # Tech-Stack inline mitnehmen — eine knappe Zeile, dafuer kein
        # eigenes 1-Zeilen-Panel.
        if result.tech:
            rows.append((t("detail.tech"), self._detail_value(", ".join(result.tech))))
        if result.error_message:
            rows.append((t("detail.error"), self._detail_value(result.error_message, "red")))
        return self._panel(t("detail.page_heading"), [self._kv_table(rows)])

    def _issues_panel(self, result: CrawlResult) -> Panel | None:
        """Panel mit erkannten Problemen — None wenn keine, dann wird nichts gezeigt."""
        issues = detect_issues(result)
        if not issues:
            return None
        body: list = [Text(f"  • {issue}", style="yellow") for issue in issues]
        return self._panel(t("detail.issues_heading"), body, border_style="red")

    def _referring_panel(self, result: CrawlResult) -> Panel:
        """Baut das Panel mit den verweisenden Seiten (fuer 4xx/5xx).

        Pro Eintrag: Linktext, URL (klickbar ohne CTRL) und — sofern die
        App ``source_link_markup`` anbietet — ein zusaetzlicher
        ``[Code anzeigen]``-Klick, der den HTML-Quellcode der Quelle laedt
        und zur Linkstelle scrollt.
        """
        ref_lines: list = []
        link_markup_fn = getattr(self.app, "link_markup", None)
        source_markup_fn = getattr(self.app, "source_link_markup", None)
        target_url = result.url
        entries = list(result.referring_pages)
        for idx, ref in enumerate(entries):
            link_text = ref.get("link_text", "").strip() or "Link"
            ref_url = _sanitize_url(ref.get("url", ""))
            ref_line = Text(overflow="fold")
            ref_line.append(f'  "{link_text}" → ')
            if callable(link_markup_fn) and ref_url:
                ref_line.append_text(Text.from_markup(link_markup_fn(ref_url, ref_url), overflow="fold"))
            elif ref_url:
                ref_line.append(ref_url, style=f"link {ref_url}")
            ref_lines.append(ref_line)
            if callable(source_markup_fn) and ref_url:
                # Action-Link linksbuendig auf eigener Zeile. Link-Text
                # mitgeben — _locate nutzt ihn als Fallback.
                action_line = Text(overflow="fold")
                action_line.append_text(
                    Text.from_markup(source_markup_fn(t("detail.show_source"), ref_url, target_url, link_text))
                )
                ref_lines.append(action_line)
            # Trenner zwischen mehreren Eintraegen.
            if idx < len(entries) - 1:
                ref_lines.append(Text("─" * 60, style="dim"))
        border = "red" if result.http_status_code >= 400 else "grey37"
        return self._panel(t("detail.referring_pages"), ref_lines, border_style=border)

    def show_url_detail(self, result: CrawlResult) -> None:
        """Zeigt Detail-Infos zur markierten URL.

        Jeder thematische Block (Seite, Probleme, Tech-Stack, SEO,
        HTTP-Header, verweisende Seiten) ist ein eigenes bordiertes Panel.

        Args:
            result: Das CrawlResult der markierten URL.
        """
        self._selected_result = result

        # Reihenfolge: Seite (Tech inline) > Probleme (nur wenn vorhanden)
        # > Verweisende Seiten (nur 4xx/5xx — direkt nach den Problemen,
        # damit der User bei Fehlerseiten nicht erst durch SEO/HTTP scrollen
        # muss) > HTTP-Header > SEO/Meta.
        panels: list = [self._page_panel(result)]

        issues_panel = self._issues_panel(result)
        if issues_panel is not None:
            panels.append(issues_panel)

        if result.referring_pages and result.http_status_code >= 400:
            panels.append(self._referring_panel(result))

        if result.response_headers:
            http_rows = [(name, self._detail_value(value)) for name, value in result.response_headers.items()]
            panels.append(self._panel(t("detail.http_heading"), [self._kv_table(http_rows)]))

        seo_rows = self._seo_rows(result.seo)
        if seo_rows:
            panels.append(self._panel(t("detail.seo_heading"), [self._kv_table(seo_rows)]))

        detail = self.query_one("#url-detail", Static)
        detail.update(Group(*panels))

    def clear_detail(self) -> None:
        """Setzt das URL-Detail-Panel zurueck."""
        self._selected_result = None
        detail = self.query_one("#url-detail", Static)
        detail.update("")
