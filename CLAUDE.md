# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace Structure

Independent projects live here. Each has its own detailed CLAUDE.md — read it before working on that project.

| Project | Path | CLAUDE.md |
|---------|------|-----------|
| Majors Golf Pool | `Majors Golf Pool/` | [`Majors Golf Pool/CLAUDE.md`](Majors Golf Pool/CLAUDE.md) |
| Sleeper Fantasy Football | `Sleeper FF/The Other League/` | [`Sleeper FF/The Other League/CLAUDE.md`](Sleeper FF/The Other League/CLAUDE.md) |
| Basic Bros Ryder Cup | `Basic Bros Ryder Cup/` | [`Basic Bros Ryder Cup/CLAUDE.md`](Basic Bros Ryder Cup/CLAUDE.md) |
| Poker Learning Site | `Poker/` | [`Poker/CLAUDE.md`](Poker/CLAUDE.md) |
| Family Travel Map | `Travel Map/` | [`Travel Map/CLAUDE.md`](Travel%20Map/CLAUDE.md) |
| Bova's Picks | `NFL Pickems/` | [`NFL Pickems/CLAUDE.md`](NFL%20Pickems/CLAUDE.md) |
| Draft Assistant 2026 | `Draft Assistant 2026/` | [`Draft Assistant 2026/README.md`](Draft%20Assistant%202026/README.md) |

## Shared Conventions

All projects are **static HTML / Vanilla JS** sites. No npm, no Node, no build step. All dependencies load from CDN `<script>` tags. Never introduce a build tool.

- **Majors Golf Pool** is hosted on **DreamHost** — push to `main` and GitHub Actions deploys via SFTP automatically. Live at https://basic-bros-pga-pickems.com
- **Basic Bros Ryder Cup** is hosted on **DreamHost** — push to `main` and GitHub Actions deploys via SFTP automatically. Live at https://basic-bros-ryder-cup.com
- **Sleeper FF** is hosted on **GitHub Pages** — push to `main` and the site updates automatically. Live at https://bova4389.github.io/the-other-league/
- **Draft Assistant 2026** is hosted on **GitHub Pages** — push to `main` and the site updates automatically. Live at https://bova4389.github.io/bovas-draft-assistant/

The "no build step" rule above is about the *sites*: every one of them is static HTML that a
browser runs as-is. `Draft Assistant 2026` has offline Python scripts that fold ranking CSVs
into its single HTML file — that is data prep run by hand, not a toolchain the site depends
on, and the deployed page still has zero build and zero dependencies.

## Cache Busting (Required on All DreamHost Projects)

Safari on mobile aggressively caches pages. Users should never need to manually clear their cache to see updates. Every DreamHost project must have both layers of cache busting in place — except that Layer 2 does not apply to `Basic Bros Ryder Cup`, which is a single HTML file with all CSS and JS inline and therefore has no local asset URLs to version.

**Layer 1 — `.htaccess` (server-side headers):**
Every DreamHost project must have a `.htaccess` file that sends `no-cache, no-store, must-revalidate` for all `.html`, `.js`, and `.css` files, and allows a 30-day cache for images. See the existing `.htaccess` files in `Majors Golf Pool/` and `Basic Bros Ryder Cup/` as the template.

**`.htaccess` needs two things to actually reach the server — both are easy to break:**

1. It must be **tracked in git**. Never add it to `.gitignore`. (It sat in the Majors
   `.gitignore` for months, so Layer 1 was never live on that site at all.)
2. `deploy.yml` must upload it in a **separate explicit step**. The deploy action runs
   `put -r ./* <remote>` via sftp, and sftp's glob does not match leading dots — so `./*`
   silently skips every dotfile. Both DreamHost workflows now have a dedicated
   "Deploy .htaccess" step. **Do not delete it as redundant; it is the only thing that
   uploads the file.**

Verify after deploying with `curl -sI <url>/css/styles.css | grep -i cache-control` — expect
`no-cache, no-store, must-revalidate`. An empty result or a `max-age` means `.htaccess` is not
on the server.

## What Reaches the Public Web Server

Both DreamHost workflows have a **"Stage deployable files"** step that rsyncs the repo into
`_deploy/` minus internal-only paths (`.github`, `.gitignore`, `CLAUDE.md`, and for Majors
`data-archive`/`archive-scripts`, for BBRC `REQUIREMENTS.md` and PDFs). Both upload steps then
read from `_deploy/`. Without this, the action's `put -r ./*` published everything tracked —
`/CLAUDE.md` was live on both domains.

It is an **exclude list, not an allow list, on purpose**: a new site asset that nobody adds to
the workflow still deploys. Forgetting to exclude a doc is untidy; forgetting to include a
stylesheet breaks the live site. When adding a genuinely internal file, add an `--exclude` for it.

**Entrant PII must never be committed.** The Majors repo is public *and* deploys to a public
webroot, so a committed file is published twice over. `data-archive/**/picks.csv`,
`data-archive/*picks_raw*.json` and `Picks/` hold real emails and phone numbers and are
gitignored; a `PreToolUse` hook (`.claude/hooks/check-staged-pii.py`) scans staged blobs and
blocks any commit containing contact details as a backstop.

**Layer 2 — Query string version on CSS/JS links (HTML-side):**
Every `<link rel="stylesheet">` and `<script src>` tag that references a local file must include a `?v=YYYYMMDD` query string (e.g. `css/styles.css?v=20260522`). **Update the version whenever you make changes to the CSS or JS files.** This breaks any CDN or ISP-level caching that ignores server headers.

**Same-day collision rule:** If the version string already shows today's date, append or increment a letter suffix rather than leaving it unchanged: `20260618` → `20260618b` → `20260618c`. A collision means users keep the old cached file even after a deploy. Before editing any JS or CSS file, grep for its current `?v=` value in the HTML and check whether it already equals today's date.

Example:
```html
<link rel="stylesheet" href="css/styles.css?v=20260522" />
<script src="js/app.js?v=20260522"></script>
```

**Never put `?v=` on a shared ES module that holds state.** A query string is part of a
module's identity, so `import './firebase-config.js?v=1'` and `import './firebase-config.js'`
are two *separate instances* with separate module-level variables. When `index.html` initialises
one instance and `standings.js` reads from the other, `getDb()` returns null and every Firestore
call fails — this took the Majors site down on U.S. Open launch day. The rule:

- **Shared/stateful modules** (`firebase-config.js`, `scoring.js`) — imported by both HTML and
  other modules: **never versioned**, anywhere. `.htaccess` keeps them fresh.
- **Entry-point modules and CSS** (`standings.js`, `admin.js`, `styles.css`) — referenced only
  from HTML: version normally per the rules above.

Keep one file's version identical across **every** page that references it. Majors once had
`styles.css` at three different versions across `index`/`admin`/`picks`, so two of the three
pages served stale CSS indefinitely. Grep the whole project, not just one file:
`grep -rn "styles.css?v=" *.html`.

These layers together ensure users — especially on Safari mobile — always see the latest version without having to clear their cache.

## Git Setup

There are **six separate git repositories** in this workspace. Always check which one you
are in before committing — `git -C "<project>" status` rather than assuming the outer repo.

| Repo root | Remote | Covers |
|---|---|---|
| `Majors Golf Pool/` | `bova4389/the-majors-golf` | that directory only |
| `Basic Bros Ryder Cup/` | `bova4389/basic-bros-ryder-cup` | that directory only |
| `Poker/` | `bova4389/poker-learning-site` (private) | that directory only |
| `NFL Pickems/` | none yet — local only (see its CLAUDE.md GitHub Setup) | that directory only |
| `Draft Assistant 2026/` | `bova4389/bovas-draft-assistant` | that directory only |
| workspace root | `bova4389/the-other-league` | Sleeper FF + root files |

- Commit and push the five project repos **from inside their own directory**.
- All Sleeper FF / The Other League files live under `Sleeper FF/The Other League/` — the repo root `index.html` is only a redirect stub.

**Never `git add` a nested repo from the outer repo** — not `Majors Golf Pool/`, not
`Basic Bros Ryder Cup/`, not `Poker/`, not `NFL Pickems/`, not `Draft Assistant 2026/`. Git records them as a gitlink (submodule
stub) and their files are not tracked. They correctly show as untracked `??` entries in outer-repo
`git status`; that is expected, not a problem to fix.

**Not under version control at all:** `Travel Map/`. Planned as its own repo — see the GitHub
Setup section in its CLAUDE.md. Once created, never `git add` it from the outer repo either.

**`Basic Bros Ryder Cup/` drifts — always `git fetch` before editing it.** Work on this repo
also happens in cloud sessions that push directly to `main` (and leave `claude/*` branches
behind), so the local checkout is often several commits stale. Editing `index.html` from a
stale copy risks a painful conflict, since that single file is the entire site. See
`feedback_verify_deploy_state` in memory for the mirror-image failure (a fix written locally
but never pushed, leaving the bug live for days).

## Project State — Where To Look

**Do not restate per-project state in this file.** Detailed status (which tournaments are
hardcoded, which features are built, what's next) belongs in each project's own CLAUDE.md,
which is the single source of truth. This file previously duplicated that detail and drifted
three months out of date, so every session started from false facts. Keep the notes below to
one orientation line each; if you need to correct project status, edit the project's CLAUDE.md.

- **Majors Golf Pool** — Seasonal. The 2026 season is closed out: all four majors for both
  2025 and 2026 are hardcoded in `standings.js`. Nothing is due until Masters 2027. Status
  detail and the live-tournament runbook are in its CLAUDE.md.
- **Sleeper FF / The Other League** — The active development project. Everything lives under
  `Sleeper FF/The Other League/` (large single-file `index.html`, plus `ktc-values.json`,
  `stats-history.json`, `scripts/`). Its CLAUDE.md holds the full function reference and the
  phased Dev Roadmap that new work should be picked from.
- **Basic Bros Ryder Cup** — Seasonal, single-file site. Read its CLAUDE.md *and*
  `REQUIREMENTS.md`, and `git fetch` first (see Git Setup).
- **Poker** — Personal build, not hosted anywhere; open the HTML directly. V0.1 complete
  (calculator + learn page); V0.2 playable game not started. Own private repo.
- **Bova's Picks** (folder: `NFL Pickems/` — renamed from "NFL Pickem Analyzer" 2026-08-11, folder
  kept as-is; repo slug will be `bovas-picks`) — Active. Schedule, Grid, Pick Sheet, Odds and
  Recommend tabs are functional; Lookback and the Survivor *planning* panel are the two still
  stubbed. Own repo (`bova4389/bovas-picks`), pushed since
  2026-08-11 and live on GitHub Pages at https://bova4389.github.io/bovas-picks/. Status detail is
  in its CLAUDE.md.
- **Draft Assistant 2026** — Single-page fantasy draft board for the "2 Mitchs 1 Cup" Sleeper
  league, built 2026-08-14 for a draft two days later. Blends three ranking sources, uses
  FantasyPros' per-position tiers, and syncs picks live from the Sleeper API. Deliberately
  applies **no** scoring adjustment — see its README for why. Details in its README.
- **Travel Map** — Scaffolding only, no features built yet.
