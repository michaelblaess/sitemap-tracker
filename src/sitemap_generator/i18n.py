"""i18n — Einfache Internationalisierung ueber JSON-Sprachdateien."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from importlib import resources

logger = logging.getLogger(__name__)

_strings: dict[str, str] = {}
_current_lang: str = "de"

SUPPORTED_LANGUAGES = ("de", "en")
DEFAULT_LANGUAGE = "de"


def load_locale(lang: str) -> None:
    """Laedt eine Sprachdatei (z.B. 'de', 'en')."""
    global _strings, _current_lang

    if lang not in SUPPORTED_LANGUAGES:
        logger.warning("Sprache '%s' nicht unterstuetzt, verwende '%s'", lang, DEFAULT_LANGUAGE)
        lang = DEFAULT_LANGUAGE

    try:
        locale_files = resources.files("sitemap_generator") / "locale" / f"{lang}.json"
        raw = locale_files.read_text(encoding="utf-8")
        _strings = json.loads(raw)
        _current_lang = lang
    except Exception:
        logger.exception("Fehler beim Laden der Sprachdatei '%s'", lang)
        _strings = {}
        _current_lang = lang


def current_language() -> str:
    """Gibt die aktuell geladene Sprache zurueck."""
    return _current_lang


def t(key: str, **kwargs: object) -> str:
    """Uebersetzt einen Schluessel. Platzhalter via {name} und kwargs."""
    template = _strings.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def format_datetime(timestamp: str, lang: str | None = None) -> str:
    """Formatiert einen ISO-Timestamp culture-abhaengig (Datum + Uhrzeit).

    Regel fuer das Projekt:
    - DE: ``dd.MM.yyyy HH:mm`` (z.B. ``19.05.2026 20:58``)
    - EN / Fallback: ISO ``yyyy-MM-dd HH:mm``

    Args:
        timestamp:
            Zeitstempel als ISO-String (z.B. ``2026-05-19T20:58:00``). Leer
            oder ungueltig fuehrt zu ``"?"``.
        lang:
            Sprachkuerzel. Default: die aktuell geladene Sprache.

    Returns:
        Formatierter Datum/Zeit-String.
    """
    if not timestamp:
        return "?"
    if lang is None:
        lang = _current_lang
    try:
        dt = datetime.fromisoformat(timestamp)
    except (ValueError, TypeError):
        # Robust gegen schlecht gespeicherte Werte: nehmen was geht.
        return timestamp[:16].replace("T", " ")
    if lang == "de":
        return dt.strftime("%d.%m.%Y %H:%M")
    return dt.strftime("%Y-%m-%d %H:%M")


def format_date(timestamp: str, lang: str | None = None) -> str:
    """Formatiert einen ISO-Timestamp culture-abhaengig (nur Datum).

    DE: ``dd.MM.yyyy``, EN/Fallback: ISO ``yyyy-MM-dd``.
    """
    if not timestamp:
        return "?"
    if lang is None:
        lang = _current_lang
    try:
        dt = datetime.fromisoformat(timestamp)
    except (ValueError, TypeError):
        return timestamp[:10]
    if lang == "de":
        return dt.strftime("%d.%m.%Y")
    return dt.strftime("%Y-%m-%d")
