# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace Structure

Three independent projects live here. Each has its own detailed CLAUDE.md — read it before working on that project.

| Project | Path | CLAUDE.md |
|---------|------|-----------|
| Majors Golf Pool | `Majors Golf Pool/` | [`Majors Golf Pool/CLAUDE.md`](Majors Golf Pool/CLAUDE.md) |
| Sleeper Fantasy Football | `Sleeper FF/The Other League/` | [`Sleeper FF/The Other League/CLAUDE.md`](Sleeper FF/The Other League/CLAUDE.md) |
| Basic Bros Ryder Cup | `Basic Bros Ryder Cup/` | [`Basic Bros Ryder Cup/CLAUDE.md`](Basic Bros Ryder Cup/CLAUDE.md) |

## Shared Conventions

All projects are **static HTML / Vanilla JS** sites. No npm, no Node, no build step. All dependencies load from CDN `<script>` tags. Never introduce a build tool.

- **Majors Golf Pool** is hosted on **DreamHost** — push to `main` and GitHub Actions deploys via SFTP automatically. Live at https://basic-bros-pga-pickems.com
- **Basic Bros Ryder Cup** is hosted on **DreamHost** — push to `main` and GitHub Actions deploys via SFTP automatically. Live at https://basic-bros-ryder-cup.com
- **Sleeper FF** is hosted on **GitHub Pages** — push to `main` and the site updates automatically. Live at https://bova4389.github.io/the-other-league/

## Cache Busting (Required on All DreamHost Projects)

Safari on mobile aggressively caches pages. Users should never need to manually clear their cache to see updates. Every DreamHost project must have both layers of cache busting in place:

**Layer 1 — `.htaccess` (server-side headers):**
Every DreamHost project must have a `.htaccess` file that sends `no-cache, no-store, must-revalidate` for all `.html`, `.js`, and `.css` files, and allows a 30-day cache for images. See the existing `.htaccess` files in `Majors Golf Pool/` and `Basic Bros Ryder Cup/` as the template.

**Layer 2 — Query string version on CSS/JS links (HTML-side):**
Every `<link rel="stylesheet">` and `<script src>` tag that references a local file must include a `?v=YYYYMMDD` query string (e.g. `css/styles.css?v=20260522`). **Update the date whenever you make changes to the CSS or JS files.** This breaks any CDN or ISP-level caching that ignores server headers.

Example:
```html
<link rel="stylesheet" href="css/styles.css?v=20260522" />
<script src="js/app.js?v=20260522"></script>
```

These two layers together ensure users — especially on Safari mobile — always see the latest version without having to clear their cache.

## Git Setup

These are **two separate git repositories**:

- `Majors Golf Pool/` has its own `.git` and remote: `https://github.com/bova4389/the-majors-golf.git` — commit and push from inside that directory.
- The outer workspace repo tracks everything else (Sleeper FF, root files). Remote: `https://github.com/bova4389/the-other-league`
- All Sleeper FF / The Other League files live under `Sleeper FF/The Other League/` — the repo root `index.html` is only a redirect stub.

Never `git add Majors Golf Pool/` from the outer repo — it will be treated as a submodule and its files will not be tracked.

## Project States (as of May 2026)

**Majors Golf Pool** — Masters 2026 ✅, PGA Championship 2026 ✅, Masters 2025 ✅, PGA Championship 2025 ✅, and U.S. Open 2025 ✅ are all fully hardcoded in `standings.js` (Total, R1–R4, Payouts). The Open Championship 2025 scoreboard is hardcoded but pool standings (`THEOPEN_2025_TOTAL` + rounds) are not yet entered. U.S. Open 2026 is the next upcoming tournament (ESPN event ID `401811952`).

**Sleeper FF / The Other League** — Active development project. All files are in `Sleeper FF/The Other League/` — `index.html` (4900+ lines), logo PNGs, `ktc-values.json`, `stats-history.json`, and `scripts/`. Full feature set for roster management, trade evaluation (with live KTC values), draft picks, and standings. See its CLAUDE.md for the complete function and data reference.
