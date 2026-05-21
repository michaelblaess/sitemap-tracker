#!/usr/bin/env bash
# Rendert eine .tape unter WSL/Linux. vhs scheitert auf Windows-Host nativ
# (Issue #721), daher laeuft das Rendering hier.
#
# Aufruf:
#   bash demo/render-wsl.sh              # rendert demo/intro.tape
#   bash demo/render-wsl.sh demo/foo.tape
set -euo pipefail

TAPE="${1:-demo/intro.tape}"

# uv liegt nach dem Installer in ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"

# Repo-Pfad (Windows-Mount). Bei anderem Speicherort anpassen.
REPO="/mnt/c/Users/Michael/Repos/sitemap-tracker"
cd "$REPO"

# Die Windows-.venv ist unter Linux unbrauchbar (Symlinks zeigen auf
# C:\Python...). Eigene WSL-venv unter ~/.venvs anlegen lassen.
WSL_VENV="$HOME/.venvs/sitemap-tracker"
export UV_PROJECT_ENVIRONMENT="$WSL_VENV"
mkdir -p "$(dirname "$WSL_VENV")"
if [ ! -x "$WSL_VENV/bin/python" ]; then
    uv sync
    # Playwright-Browser fuer den Live-Crawl + die Seiten-Vorschau.
    uv run playwright install chromium
fi

vhs "$TAPE"
echo "Fertig: $REPO/${TAPE%.tape}.gif"
