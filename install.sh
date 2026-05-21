#!/usr/bin/env bash
# Sitemap Tracker - One-Line Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/michaelblaess/sitemap-tracker/main/install.sh | bash
set -e

REPO="michaelblaess/sitemap-tracker"
INSTALL_DIR="$HOME/.sitemap-tracker"
BIN_DIR="$HOME/.local/bin"

echo "=== Sitemap Tracker - Installer ==="
echo ""

# OS und Architektur erkennen
os="$(uname -s)"; arch="$(uname -m)"
case "$os" in
    Linux)  os_key="linux" ;;
    Darwin) os_key="macos" ;;
    *) echo "Nicht unterstuetztes Betriebssystem: $os" >&2; exit 1 ;;
esac
case "$arch" in
    x86_64|amd64)  arch_key="x86_64" ;;
    arm64|aarch64) arch_key="arm64" ;;
    *) arch_key="$arch" ;;
esac

echo "Plattform: $os_key ($arch_key)"

# Neuestes Release von GitHub holen
echo "Suche neuestes Release..."
RELEASE_JSON=$(curl -fsSL "https://api.github.com/repos/$REPO/releases/latest")

# Asset versionsunabhaengig per OS+Arch waehlen (ohne jq)
candidates=("${os_key}-${arch_key}")
[ "$os_key" = "macos" ] && [ "$arch_key" = "arm64" ] && candidates+=("macos-x86_64")

urls="$(echo "$RELEASE_JSON" | grep -oE '"browser_download_url": *"[^"]*"' \
        | sed -E 's/.*"(https[^"]*)"/\1/')"
DOWNLOAD_URL=""
for want in "${candidates[@]}"; do
    DOWNLOAD_URL="$(echo "$urls" | grep -E "${want}[^/]*\.(zip|tar\.gz)$" | head -1)"
    [ -n "$DOWNLOAD_URL" ] && break
done

if [ -z "$DOWNLOAD_URL" ]; then
    echo "Kein passendes Asset fuer ${os_key}-${arch_key} gefunden. Verfuegbar:" >&2
    echo "$urls" | sed 's#.*/##' >&2
    exit 1
fi

VERSION=$(echo "$RELEASE_JSON" | grep -o '"tag_name":[[:space:]]*"[^"]*"' | grep -o '"v[^"]*"' | tr -d '"')
echo "Version: $VERSION"
echo "Download: $DOWNLOAD_URL"

# Altes Verzeichnis entfernen
rm -rf "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Herunterladen und entpacken
echo "Lade herunter..."
TMPFILE=$(mktemp)
curl -fsSL "$DOWNLOAD_URL" -o "$TMPFILE"

echo "Entpacke..."
tar -xzf "$TMPFILE" -C "$INSTALL_DIR" --strip-components=1
rm -f "$TMPFILE"

# Executable finden und ausfuehrbar machen
chmod +x "$INSTALL_DIR/sitemap-tracker" 2>/dev/null || true

# Wrapper-Skript in ~/.local/bin
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/sitemap-tracker" << 'WRAPPER'
#!/usr/bin/env bash
exec "$HOME/.sitemap-tracker/sitemap-tracker" "$@"
WRAPPER
chmod +x "$BIN_DIR/sitemap-tracker"

echo ""
echo "Installation abgeschlossen!"
echo ""

# PATH pruefen
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$BIN_DIR"; then
    echo "HINWEIS: $BIN_DIR ist nicht im PATH."
    echo "Fuege folgende Zeile zu ~/.bashrc oder ~/.zshrc hinzu:"
    echo ""
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
fi

echo "Starten mit: sitemap-tracker https://example.com"
