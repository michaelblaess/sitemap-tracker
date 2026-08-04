"""Vollstaendigkeit und Konsistenz der Sprachdateien.

Anlass: Der Dialog "Dateien pruefen" zeigte statt "Schliessen" den blanken
Schluessel ``common.btn_close`` an - der Schluessel existierte in diesem Projekt
gar nicht, er stammte aus einem anderen Werkzeug. Auffallen konnte das nicht:
``t()`` gibt einen unbekannten Schluessel unveraendert zurueck, wirft also
keinen Fehler, und die Tests pruefen Knoepfe ueber ihre ID statt ueber ihre
Beschriftung. Nur ein Blick auf den laufenden Dialog hat es gezeigt.

Diese Tests schliessen die Luecke - sie pruefen nicht die Texte selbst, sondern
ihre Vollstaendigkeit.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from string import Formatter

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src" / "sitemap_tracker"
_LOCALE = _SRC / "locale"

# t("...") bzw. t('...') - nur das Literal, keine berechneten Schluessel.
_T_AUFRUF = re.compile(r"""\bt\(\s*["']([a-z][a-z_0-9.]*)["']""")


def _lade(sprache: str) -> dict[str, str]:
    return json.loads((_LOCALE / f"{sprache}.json").read_text(encoding="utf-8"))


def _platzhalter(vorlage: str) -> set[str]:
    """Feldnamen einer Format-Vorlage, z.B. {count} -> {"count"}."""
    return {name for _, name, _, _ in Formatter().parse(vorlage) if name}


def _verwendete_schluessel() -> set[str]:
    """Alle im Quelltext per t(...) angeforderten Schluessel."""
    treffer: set[str] = set()
    for datei in _SRC.rglob("*.py"):
        treffer.update(_T_AUFRUF.findall(datei.read_text(encoding="utf-8")))
    return treffer


class TestParitaet:
    def test_gleiche_schluessel_in_beiden_sprachen(self) -> None:
        de, en = _lade("de"), _lade("en")
        assert set(de) == set(en), (
            f"nur in de: {sorted(set(de) - set(en))} | nur in en: {sorted(set(en) - set(de))}"
        )

    def test_gleiche_platzhalter_je_schluessel(self) -> None:
        """Ein abweichender Platzhalter liefert in EINER Sprache Rohtext."""
        de, en = _lade("de"), _lade("en")
        abweichung = {
            schluessel: (_platzhalter(de[schluessel]), _platzhalter(en[schluessel]))
            for schluessel in set(de) & set(en)
            if _platzhalter(de[schluessel]) != _platzhalter(en[schluessel])
        }
        assert not abweichung, f"unterschiedliche Platzhalter: {abweichung}"


class TestVollstaendigkeit:
    def test_kein_verwendeter_schluessel_fehlt(self) -> None:
        """Genau der Fall, der den Knopf 'common.btn_close' beschriften liess."""
        de = _lade("de")
        fehlend = sorted(s for s in _verwendete_schluessel() if s not in de)
        assert not fehlend, f"im Quelltext benutzt, aber nicht uebersetzt: {fehlend}"

    @pytest.mark.parametrize("sprache", ["de", "en"])
    def test_kein_schluessel_ohne_text(self, sprache: str) -> None:
        leer = sorted(k for k, v in _lade(sprache).items() if not str(v).strip())
        assert not leer, f"leere Texte in {sprache}: {leer}"
