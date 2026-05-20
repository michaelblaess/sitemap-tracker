# Sitemap Generator

<p align="center">
  <img src="docs/flags/gb.svg" height="13" alt=""> <b>English</b> ·
  <img src="docs/flags/de.svg" height="13" alt=""> <a href="README.de.md">Deutsch</a>
</p>

---

[![Stars](https://img.shields.io/github/stars/michaelblaess/sitemap-generator?logo=github&logoColor=white&color=fbbf24)](https://github.com/michaelblaess/sitemap-generator/stargazers)
[![Forks](https://img.shields.io/github/forks/michaelblaess/sitemap-generator?logo=github&logoColor=white&color=34d399)](https://github.com/michaelblaess/sitemap-generator/network/members)
[![Issues](https://img.shields.io/github/issues/michaelblaess/sitemap-generator?logo=github&logoColor=white&color=f87171)](https://github.com/michaelblaess/sitemap-generator/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/michaelblaess/sitemap-generator?logo=github&logoColor=white&color=a78bfa)](https://github.com/michaelblaess/sitemap-generator/pulls)

[![Last Commit](https://img.shields.io/github/last-commit/michaelblaess/sitemap-generator?logo=git&logoColor=white&color=3b82f6)](https://github.com/michaelblaess/sitemap-generator/commits/main)
[![License](https://img.shields.io/badge/license-Apache_2.0-3b82f6)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-3b82f6?logo=python&logoColor=white)](https://www.python.org/)

Crawls websites and generates standard-compliant `sitemap.xml` files. Uses [Playwright](https://playwright.dev/) for JavaScript rendering or [httpx](https://www.python-httpx.org/) for fast HTTP crawling.

## Screenshots

### Main View
![Main View](docs/screenshots/01-main.png)

### Sitemap Tree
![Sitemap Tree](docs/screenshots/02-sitemap.png)

### Crawl History
![Crawl History](docs/screenshots/03-history.png)

## Installation

### One-Liner (Standalone, no Python required)

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/michaelblaess/sitemap-generator/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/michaelblaess/sitemap-generator/main/install.ps1 | iex
```

## Usage

```bash
# Simple crawl (httpx mode, fast)
sitemap-generator https://example.com

# With JavaScript rendering (Playwright)
sitemap-generator https://example.com --render

# Save sitemap directly
sitemap-generator https://example.com --output sitemap.xml

# Limit crawl depth
sitemap-generator https://example.com --max-depth 5

# More concurrency
sitemap-generator https://example.com --concurrency 16

# Ignore robots.txt
sitemap-generator https://example.com --ignore-robots

# With cookies (e.g. for login)
sitemap-generator https://example.com --cookie session=abc123
```

## CLI Parameters

| Parameter | Description | Default |
|---|---|---|
| `URL` | Start URL of the website | - |
| `--output`, `-o` | Output path for sitemap.xml | `sitemap_<host>_<timestamp>.xml` |
| `--max-depth`, `-d` | Maximum crawl depth | 10 |
| `--concurrency`, `-c` | Parallel requests | 8 |
| `--timeout`, `-t` | Timeout per page (seconds) | 30 |
| `--render` | Render JavaScript with Playwright | off |
| `--no-headless` | Browser visible (debugging) | off |
| `--ignore-robots` | Ignore robots.txt | off |
| `--user-agent` | Custom User-Agent | Chrome 131 |
| `--cookie` | Set cookie (NAME=VALUE, multiple) | - |

## Keyboard Shortcuts (TUI)

| Key | Function |
|---|---|
| `c` | Start crawl (URL dialog) |
| `x` | Cancel crawl / JSON error report |
| `m` | Save sitemap |
| `s` | Settings |
| `g` | Export form report (JSON) |
| `j` | JIRA table to clipboard |
| `e` | Show errors only |
| `f` | Sitemap diff |
| `d` | Copy URL details |
| `l` | Toggle log |
| `h` | History |
| `i` | Info dialog |
| `q` | Quit |

Copying / exporting the log runs via right-click on the log panel.
Hovering a shortcut in the footer reveals a full tooltip explaining what it does.
URLs in the log, header and detail panel are clickable without holding Ctrl.

## Features

- **Dual mode**: httpx (fast, HTML only) or Playwright (JavaScript rendering)
- **robots.txt**: Respected by default, `--ignore-robots` to disable
- **Auto-split**: With >50,000 URLs, an automatic sitemap index with partial sitemaps
- **Priority**: Automatically based on crawl depth (home page = 1.0)
- **lastmod**: From HTTP Last-Modified header
- **URL normalization**: Duplicates avoided through normalization
- **Form detection**: `<form>` tags are detected, marked in the table and exportable as JSON
- **Live TUI**: Progress, statistics and URL details in real time — results table and page tree split across two tabs
- **Sortable results**: Click any column header (Status, HTTP, Depth, Links, Form, Time, Size, Date, URL) to sort — second click reverses. Active column gets a ▲/▼ marker
- **Date & size columns**: Last-Modified date and page size are shown directly in the results table, side by side with the URL
- **Clickable links**: URLs in the log, crawl header and detail panel open in your default browser on a single click (no Ctrl required); local result files (sitemap.xml, JSON reports) open in the OS default app
- **Page tree**: Hierarchical view of all crawled URLs with HTTP status, dead-link and not-in-sitemap markers — embedded as a tab, siblings sorted alphabetically; the table's filter applies to the tree as well (matching nodes plus their ancestors stay visible)
- **URL dialog**: `c` opens a dialog (pre-filled with the last URL) to enter or change the target URL — no restart needed
- **Crawl header**: All crawl statistics — mode, robots.txt, concurrency, status codes, progress — grouped in one collapsible header
- **Page details**: Selecting a URL shows grouped panels — page info, issues, tech stack, SEO/meta data and HTTP headers
- **Footer tooltips**: Every shortcut shows a hover-tooltip explaining what it does — even the cryptic ones like JIRA table, sitemap diff or form report
- **Issue detection**: Flags common problems per page — HTTP errors, missing/overlong title & description, missing H1/viewport/canonical, `noindex`, slow load, large page
- **Tech-stack detection**: Detects the CMS, JS/CSS frameworks and server software of each page
- **Page preview**: Optional in-terminal screenshot of the selected page (TGP/Sixel with half-block fallback) — toggle in settings
- **Resizable panels**: Splitters to freely resize the URL table, log and stats panels
- **Log panel**: Right-click context menu — copy, export to file, or hide
- **Settings dialog**: Language, robots.txt, Playwright, page preview, concurrency, timeout and crawl depth — persisted across runs
- **Filter with history**: Filter the URL table by URL/status; recent filter terms in a dropdown
- **Crawl history**: Past crawls with date, URL, parameters and final stats (crawled / 2xx / errors); date in the UI's locale (DE: `dd.MM.yyyy`, EN: ISO)

## Browser Strategy

1. **System Chrome** preferred (faster startup, less memory)
2. **Bundled Chromium** as fallback (included in standalone installation)

## Privacy

**Important**: Crawling a website may be perceived as unusual traffic by the operator. Please note:

- Inform the website operator **before** crawling, especially for large websites
- Respect `robots.txt` (enabled by default)
- Use reasonable concurrency and timeout values
- This tool is intended for **your own websites** and **authorized analyses**

## Development

### Setup

```bash
git clone https://github.com/michaelblaess/sitemap-generator.git
cd sitemap-generator

# Windows
.\bootstrap.ps1

# Linux/macOS
./bootstrap.sh
```

### Local Start

```bash
# Windows
.\run.ps1 https://example.com

# Linux/macOS
./run.sh https://example.com
```

### Creating a Release

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

GitHub Actions automatically builds executables for Windows, Linux and macOS.

## License

Apache License 2.0 - see [LICENSE](LICENSE)
