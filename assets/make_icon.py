"""Erzeugt das App-Icon fuer sitemap-tracker (.ico + .png + SVG-Varianten).

Motiv: ein radialer Crawl-Graph - ein Zentralknoten mit sechs Speichen zu
Aussenknoten in einer Status-Palette (Teal, Cyan, Gruen, Amber, Violett, Rot).
Der rote Knoten steht fuer einen defekten Link.

Drei Darstellungs-Varianten (gleiche Geometrie):
- "tile"  : dunkles, abgerundetes Tile mit Verlauf (App-Icon-Look) - fuer
            .ico/.png (Nuitka, Favicon) und einen branded Logo-Block.
- "dark"  : transparenter Hintergrund, helle Toene - fuer DUNKLE Untergruende.
- "light" : transparenter Hintergrund, kraeftige Toene - fuer HELLE Untergruende.

Die Rasterbilder (.ico/.png) nutzen die "tile"-Variante mit 4x-Supersampling.
Die SVGs kommen aus derselben Geometrie und bleiben so deckungsgleich. Erzeugt:
- assets/icon.ico         (16/32/48/64/128/256 px)  - --windows-icon-from-ico
- assets/icon.icns        (1024 px, nativ)           - --macos-app-icon
- assets/icon.png         (512 px)                   - og:image / Social-Card
- assets/icon.svg         (tile, skalierbar)         - branded Logo
- assets/icon-dark.svg    (transparent, fuer dunkle Untergruende)
- assets/icon-light.svg   (transparent, fuer helle Untergruende)

Fuer GitHub-READMEs die transparenten Varianten via <picture> kombinieren
(prefers-color-scheme schaltet zwischen icon-dark und icon-light um).

Aufruf (aus dem Repo-Root):
    uv run --no-sync python assets/make_icon.py
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

# ── Geometrie (Basis-Koordinaten, viewBox 0..256) ────────────────────────────
_BASE = 256
_SS = 4  # Supersampling fuer die Rasterbilder
_CENTER = (128.0, 128.0)
_SPOKE_R = 76.0
_OUTER_R = 16.0
_CENTER_R = 28.0
_SPOKE_W = 9.0
_RING_FACTOR = 0.18
_TILE_RADIUS = _BASE * 0.22
_N = 6
_GAP = 3.0  # Luecke zwischen Speiche und Knoten bei den transparenten Varianten

# Globus-Zentrum (nur fuer die "globe-*"-Varianten, gedacht fuer grosse Logos).
_GLOBE_R = 34.0  # groesser als _CENTER_R, damit das Gitter Platz hat
_GLOBE_GW = 2.4  # Strichstaerke des Meridian-/Parallelen-Gitters
_GLOBE_OCEAN = (20, 184, 166)  # teal-500 (Ozean)
_GLOBE_GRID = (224, 255, 250)  # helles Gitter

# ── Paletten ──────────────────────────────────────────────────────────────────
# Helle Status-Toene (gut auf dunklem Untergrund).
_OUTER_BRIGHT = [
    (45, 212, 191),  # Teal
    (34, 211, 238),  # Cyan
    (74, 222, 128),  # Gruen
    (251, 191, 36),  # Amber
    (167, 139, 250),  # Violett
    (244, 90, 90),  # Rot (defekter Link)
]
# Kraeftigere 600er-Toene (gut auf hellem Untergrund).
_OUTER_DEEP = [
    (13, 148, 136),  # Teal-600
    (8, 145, 178),  # Cyan-600
    (22, 163, 74),  # Gruen-600
    (217, 119, 6),  # Amber-600
    (124, 58, 237),  # Violett-600
    (220, 38, 38),  # Rot-600
]

_BG_TOP = (16, 28, 26)
_BG_BOTTOM = (9, 13, 17)
_RING_DARK = (9, 13, 17)

# Eine Variante = Untergrund-Tile ja/nein, Knoten-Ring ja/nein, Speichen-,
# Zentrum- und Aussenknoten-Farben.
_VARIANTS = {
    "tile": {
        "tile": True,
        "ring": True,
        "spoke": (45, 156, 142),
        "center": (235, 240, 238),
        "outer": _OUTER_BRIGHT,
    },
    "dark": {
        "tile": False,
        "ring": False,
        "spoke": (52, 180, 163),
        "center": (235, 240, 238),
        "outer": _OUTER_BRIGHT,
    },
    "light": {
        "tile": False,
        "ring": False,
        "spoke": (15, 118, 110),
        "center": (148, 163, 184),  # slate-400 - heller Hub, aber auf Weiss sichtbar
        "outer": _OUTER_DEEP,
    },
    # Globus im Zentrum - nur fuer GROSSE Logos (ab ~64 px), sonst verschwindet
    # das Gitter. Globus selbst ist in beiden Themes gleich (teal + helles
    # Gitter), nur Speichen/Aussenknoten sind theme-abhaengig.
    "globe-dark": {
        "tile": False,
        "ring": False,
        "globe": True,
        "spoke": (52, 180, 163),
        "outer": _OUTER_BRIGHT,
    },
    "globe-light": {
        "tile": False,
        "ring": False,
        "globe": True,
        "spoke": (15, 118, 110),
        "outer": _OUTER_DEEP,
    },
}


def _points() -> list[tuple[float, float]]:
    """Berechnet die sechs Aussenknoten (Index 0 = oben, im Uhrzeigersinn)."""
    cx, cy = _CENTER
    pts = []
    for i in range(_N):
        angle = math.pi * 2 * i / _N - math.pi / 2
        pts.append((cx + _SPOKE_R * math.cos(angle), cy + _SPOKE_R * math.sin(angle)))
    return pts


def _hex(c: tuple[int, int, int]) -> str:
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


def _globe_svg(cx: float, cy: float, r: float) -> str:
    """Zeichnet einen stilisierten Globus (Ozean + Meridian-/Parallelen-Gitter)."""
    hx = r * math.cos(math.pi / 6)  # halbe Breite der Parallelen bei +/- r/2
    grid = _hex(_GLOBE_GRID)
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{_hex(_GLOBE_OCEAN)}"/>'
        f'<g stroke="{grid}" stroke-width="{_GLOBE_GW}" fill="none" stroke-linecap="round">'
        f'<line x1="{cx - r}" y1="{cy}" x2="{cx + r}" y2="{cy}"/>'  # Aequator
        f'<line x1="{cx}" y1="{cy - r}" x2="{cx}" y2="{cy + r}"/>'  # Mittelmeridian
        f'<ellipse cx="{cx}" cy="{cy}" rx="{r * 0.5:.2f}" ry="{r}"/>'  # Meridian-Ellipse
        f'<line x1="{cx - hx:.2f}" y1="{cy - r * 0.5:.2f}" x2="{cx + hx:.2f}" y2="{cy - r * 0.5:.2f}"/>'
        f'<line x1="{cx - hx:.2f}" y1="{cy + r * 0.5:.2f}" x2="{cx + hx:.2f}" y2="{cy + r * 0.5:.2f}"/>'
        f"</g>"
    )


# ── Rasterbild (Pillow) - nutzt die "tile"-Variante ──────────────────────────
def _vertical_gradient(size: int) -> Image.Image:
    grad = Image.new("RGBA", (size, size))
    px = grad.load()
    assert px is not None
    for y in range(size):
        f = y / (size - 1)
        color = tuple(int(_BG_TOP[i] + (_BG_BOTTOM[i] - _BG_TOP[i]) * f) for i in range(3)) + (255,)
        for x in range(size):
            px[x, y] = color
    return grad


def build_master() -> Image.Image:
    """Baut das supersamplete Master-Rasterbild (tile-Variante, RGBA)."""
    v = _VARIANTS["tile"]
    size = _BASE * _SS
    img = _vertical_gradient(size)
    draw = ImageDraw.Draw(img)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=int(_TILE_RADIUS * _SS), fill=255)

    cx, cy = _CENTER[0] * _SS, _CENTER[1] * _SS
    points = [(x * _SS, y * _SS) for x, y in _points()]
    spoke = (*v["spoke"], 255)

    for px, py in points:
        draw.line((cx, cy, px, py), fill=spoke, width=int(_SPOKE_W * _SS))
        half = _SPOKE_W * _SS / 2
        for ex, ey in ((cx, cy), (px, py)):
            draw.ellipse((ex - half, ey - half, ex + half, ey + half), fill=spoke)

    def node(x: float, y: float, r: float, fill: tuple[int, int, int]) -> None:
        ring = r * _RING_FACTOR
        draw.ellipse((x - r - ring, y - r - ring, x + r + ring, y + r + ring), fill=(*_RING_DARK, 255))
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(*fill, 255))

    for i, (px, py) in enumerate(points):
        node(px, py, _OUTER_R * _SS, v["outer"][i])
    node(cx, cy, _CENTER_R * _SS, v["center"])

    img.putalpha(mask)
    return img


# ── SVG (variantenabhaengig) ───────────────────────────────────────────────────
def build_svg(variant: str) -> str:
    """Baut das Icon als SVG-String fuer eine der Varianten."""
    v = _VARIANTS[variant]
    cx, cy = _CENTER
    points = _points()
    # Globus-Varianten haben ein groesseres Zentrum.
    r_center = _GLOBE_R if v.get("globe") else _CENTER_R

    if v["ring"]:
        # Volle Speichen - die bg-farbenen Knoten-Ringe kappen sie optisch.
        lines = "".join(f'<line x1="{cx}" y1="{cy}" x2="{px:.2f}" y2="{py:.2f}"/>' for px, py in points)
    else:
        # Gekuerzte Speichen mit Luecke zu den Knoten (kein bg-Ring noetig).
        # Endpunkte um den halben Strich nach innen, damit die runden Caps
        # genau an der Wunsch-Luecke enden statt darueber hinaus.
        inner_d = r_center + _GAP + _SPOKE_W / 2
        outer_d = (_SPOKE_R - _OUTER_R) - _GAP - _SPOKE_W / 2
        seg = []
        for i in range(_N):
            a = math.pi * 2 * i / _N - math.pi / 2
            ux, uy = math.cos(a), math.sin(a)
            seg.append(
                f'<line x1="{cx + inner_d * ux:.2f}" y1="{cy + inner_d * uy:.2f}" '
                f'x2="{cx + outer_d * ux:.2f}" y2="{cy + outer_d * uy:.2f}"/>'
            )
        lines = "".join(seg)

    def node_svg(px: float, py: float, r: float, color: tuple[int, int, int]) -> str:
        out = ""
        if v["ring"]:
            ring_r = r * (1 + _RING_FACTOR)
            out += f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{ring_r:.2f}" fill="{_hex(_RING_DARK)}"/>'
        out += f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{r:.2f}" fill="{_hex(color)}"/>'
        return out

    nodes = "".join(node_svg(px, py, _OUTER_R, v["outer"][i]) for i, (px, py) in enumerate(points))
    if v.get("globe"):
        nodes += _globe_svg(cx, cy, _GLOBE_R)
    else:
        nodes += node_svg(cx, cy, _CENTER_R, v["center"])

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_BASE} {_BASE}" '
        f'width="{_BASE}" height="{_BASE}" role="img" aria-label="Sitemap Tracker">'
    ]
    if v["tile"]:
        parts.append(
            "<defs>"
            '<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{_hex(_BG_TOP)}"/>'
            f'<stop offset="1" stop-color="{_hex(_BG_BOTTOM)}"/>'
            "</linearGradient>"
            f'<clipPath id="tile"><rect width="{_BASE}" height="{_BASE}" '
            f'rx="{_TILE_RADIUS:.2f}" ry="{_TILE_RADIUS:.2f}"/></clipPath>'
            "</defs>"
            '<g clip-path="url(#tile)">'
            f'<rect width="{_BASE}" height="{_BASE}" fill="url(#bg)"/>'
        )
    else:
        parts.append("<g>")
    parts.append(f'<g stroke="{_hex(v["spoke"])}" stroke-width="{_SPOKE_W}" stroke-linecap="round">{lines}</g>')
    parts.append(nodes)
    parts.append("</g></svg>\n")
    return "".join(parts)


def main() -> None:
    """Rendert das Master-Icon und schreibt .ico + .png + SVG-Varianten."""
    assets = Path(__file__).resolve().parent
    master_full = build_master()  # 1024 px (256 * _SS)
    master = master_full.resize((_BASE, _BASE), Image.Resampling.LANCZOS)

    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    master.save(assets / "icon.ico", sizes=ico_sizes)
    master_full.resize((512, 512), Image.Resampling.LANCZOS).save(assets / "icon.png")
    # Natives macOS-Icon (1024 px) - Nuitkas --macos-app-icon nimmt .icns direkt;
    # ein PNG braeuchte dort sonst das Zusatzpaket imageio.
    master_full.save(assets / "icon.icns")

    (assets / "icon.svg").write_text(build_svg("tile"), encoding="utf-8")
    (assets / "icon-dark.svg").write_text(build_svg("dark"), encoding="utf-8")
    (assets / "icon-light.svg").write_text(build_svg("light"), encoding="utf-8")
    (assets / "icon-globe-dark.svg").write_text(build_svg("globe-dark"), encoding="utf-8")
    (assets / "icon-globe-light.svg").write_text(build_svg("globe-light"), encoding="utf-8")

    print(f"icon.ico geschrieben ({', '.join(f'{w}x{h}' for w, h in ico_sizes)})")
    print("icon.png geschrieben (512x512)")
    print("icon.icns geschrieben (1024x1024)")
    print("icon.svg / icon-dark.svg / icon-light.svg geschrieben")
    print("icon-globe-dark.svg / icon-globe-light.svg geschrieben")


if __name__ == "__main__":
    main()
