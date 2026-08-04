"""Text in die Zwischenablage legen - ueber das Betriebssystem statt OSC 52.

Textuals ``copy_to_clipboard`` schickt den Text als OSC-52-Sequenz ans
Terminal. Das ist elegant, aber unzuverlaessig: Windows Terminal reicht
mehrzeilige Inhalte nicht sauber durch, und manche Terminals begrenzen die
Nutzlast. Beim Kopieren einer Ergebnisliste kam so alles in einer einzigen
Zeile an - unbrauchbar, wenn man sie in eine Tabelle einfuegen will.

Deshalb zuerst der Weg ueber das Betriebssystem (``clip`` unter Windows,
``pbcopy`` unter macOS, ``wl-copy``/``xclip`` unter Linux) und nur als
Rueckfall die Terminal-Sequenz.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

# Kommandos je Plattform, in der Reihenfolge ihrer Verlaesslichkeit.
_KOMMANDOS: dict[str, tuple[list[str], ...]] = {
    "win32": (["clip"],),
    "darwin": (["pbcopy"],),
}
_LINUX_KOMMANDOS: tuple[list[str], ...] = (
    ["wl-copy"],
    ["xclip", "-selection", "clipboard"],
    ["xsel", "--clipboard", "--input"],
)


def in_zwischenablage(text: str) -> bool:
    """Legt Text in die Zwischenablage des Betriebssystems.

    Args:
        text:
            Der zu kopierende Text. Zeilenumbrueche bleiben erhalten.

    Returns:
        True, wenn ein Systemkommando den Text uebernommen hat. False, wenn
        keines verfuegbar war oder alle scheiterten - dann muss der Aufrufer
        auf ``App.copy_to_clipboard`` zurueckfallen.
    """
    if not text:
        return False

    kandidaten = _KOMMANDOS.get(sys.platform, _LINUX_KOMMANDOS if sys.platform.startswith("linux") else ())
    # clip.exe erwartet unter Windows CRLF, sonst landet alles in einer Zeile.
    nutzlast = text.replace("\r\n", "\n").replace("\n", "\r\n") if sys.platform == "win32" else text

    for kommando in kandidaten:
        if shutil.which(kommando[0]) is None:
            continue
        try:
            ergebnis = subprocess.run(
                kommando,
                input=nutzlast.encode("utf-8"),
                capture_output=True,
                timeout=10,
                check=False,
            )
        except Exception:
            continue
        if ergebnis.returncode == 0:
            return True
    return False
