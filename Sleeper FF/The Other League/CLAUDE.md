# CLAUDE.md — The Other League Dynasty Dashboard

## WHAT THIS PROJECT IS

A personal fantasy football dashboard for "The Other League" — a 12-team dynasty league on the Sleeper platform. The site pulls live data from the Sleeper public API to display rosters, league history, draft picks, scoring rules, rivalries, and a trade evaluator with live KTC values.

**Commissioner:** Matt Bova. Built for personal use, shared with league mates via GitHub Pages.

---

## PROJECT STRUCTURE

This is a **static HTML/JavaScript project** — no framework, no build step, no package manager. All files are plain `.html` with embedded CSS and JavaScript.

```
the-other-league/                      ← outer repo root
├── index.html                         ← redirect stub to GitHub Pages site (do NOT edit for features)
├── .github/workflows/                 ← GitHub Actions (deploy-pages, update-ktc, tuesday-update)
└── Sleeper FF/The Other League/       ← THE actual project folder (edit everything here)
    ├── index.html                     ← THE working file (5000+ lines, all logic embedded)
    ├── CLAUDE.md                      ← you are here
    ├── TOL Large Logo.png             ← hero image (home panel + sticky header)
    ├── TOL Small Logo.png             ← available if needed
    ├── TOL Abbreviated Icon.png       ← favicon + iOS add-to-homescreen icon
    ├── TOL iPhone background image.png ← iOS splash screen
    ├── img/profiles/                  ← 12 manager headshots, 600x750 JPEG (~50 KB each, 660 KB)
    │                                    Source photos + cropping script live in `League Pics/`
    │                                    (untracked); only the web-sized JPEGs are committed.
    ├── ktc-values.json                ← KTC dynasty values (updated weekly by GitHub Action)
    ├── projections-<year>.json        ← all 17 weeks of Sleeper projections, trimmed (updated DAILY by GitHub Action)
    ├── stats-history.json             ← historical player stats cache (2023-2025; the live season
    │                                    is absent until it has played weeks — see generate_stats.py)
    ├── replacement-levels.json        ← Phase 12 weekly points-over-replacement baselines per position
    ├── trade-roi.json                 ← Phase 12 scored trades + rookie picks + pick curve
    ├── generate_stats.py              ← builds stats-history.json. NOT a one-off any more: the player
    │                                    universe is every player ever rostered, drafted OR traded here,
    │                                    so re-run it after trades and after each rookie draft
    ├── roster-grades-<period-id>.json  ← Phase 6 frozen grading period, e.g. roster-grades-2026-preseason.json
    │                                     (exists as of 2026-08-20). One file per grading run; hand-committed from the
    │                                     Export panel in Rosters > Grades & Outlook with ?admin=1 on the URL
    ├── matchup-commentary-<year>.json  ← Phase 8 Scores-tab PER-MATCHUP write-ups, keyed "week|matchup_id".
    │                                     2025 complete; 2026 scaffolded empty 2026-08-21, written live each week.
    ├── weekly-recaps-<year>.json       ← Phase 10 WHOLE-LEAGUE weekly recap, keyed by week number.
    │                                     Sits at the TOP of the Scores tab. 2026 scaffolded empty 2026-08-21.
    ├── season-recaps.json              ← Phase 9 Careers year-tab season write-ups, keyed by year.
    │                                     2023/2024/2025 written 2026-08-21.
    └── scripts/
        ├── tuesday_update.py          ← weekly H2H records updater
        ├── fetch_ktc.py               ← KTC values scraper (top-500 + per-player deep lookup)
        ├── fetch_projections.py       ← daily Sleeper projections pull → projections-<year>.json
        ├── build_matchup_facts.py     ← Phase 8 offline fact sheet; writes to a temp dir, never committed
        ├── build_season_facts.py      ← Phase 9 season-level fact sheet; same deal, never committed
        ├── build_replacement_levels.py ← Phase 12; writes replacement-levels.json (committed)
        ├── build_trade_roi.py         ← Phase 12; writes trade-roi.json (committed).
        │                                --report prints the distributions the thresholds came from
        ├── measure_starter_mix.py     ← Phase 12; measures the real positional starter mix that
        │                                sets REPLACEMENT_RANKS. Prints only, writes nothing
        └── bot_state.json             ← tracks which weeks have been applied
```

**Housekeeping (2026-08-20):** deleted `h2h_calc.py` (a one-off with 2023-25 scores pasted inline that only printed to stdout — `scripts/tuesday_update.py` supersedes it, pulling from the API and maintaining `h2h-records.md`) and `scripts/check_js.py` / `check_js2.py` (bracket-balance debuggers hardcoded to `Desktop/Claude Code/index.html`, a path that has only held the redirect stub since the project moved into this folder — they were broken *and* unreferenced). Together with the dead-code removal in `index.html`, that is ~36 KB gone.

**Current state:** `Sleeper FF/The Other League/index.html` is the **only** file to edit for features. It contains all HTML, CSS, and JavaScript in one file. The logo PNGs, `ktc-values.json`, and `stats-history.json` are in the same folder.

**Deployment:** GitHub Pages (static hosting). The `deploy-pages.yml` Action serves from `Sleeper FF/The Other League/`. Push to `main` → site updates automatically. Live at `https://bova4389.github.io/the-other-league/`

---

## EXTERNAL APIS

### Sleeper API (no auth required)
- Base: `https://api.sleeper.app/v1`
- League ID: `1316225642072662016`
- Key endpoints:
  - `/league/{lid}` → league info
  - `/league/{lid}/rosters` → all 12 rosters
  - `/league/{lid}/traded_picks` → pick trade log
  - `/league/{lid}/matchups/{week}` → matchup scores for a given week
  - `/league/{lid}/transactions/{week}` → transactions for a given week
  - `/league/{lid}/drafts` → drafts list
  - `/draft/{draft_id}/picks` → picks for a draft
  - `/players/nfl` → full player database (~5MB, slow)
  - `/stats/nfl/regular/{year}/{week}` → actual player stats for a completed week
  - `/state/nfl` → current season + week; drives "is this the live season/week" decisions instead of hardcoded years
  - `/projections/nfl/regular/{year}/{week}` → projected player **stat lines** (NOT points — the `pts_ppr`/`pts_std`/`pts_half_ppr` fields it also returns are Sleeper's generic scoring and know nothing about this league; never display them. Score the raw line through `calcPts()`/`SDATA` instead). ~590 KB per week for all ~9,400 players, which is why the committed `projections-<year>.json` exists. **Corrected 2026-08-19** — this note previously said "no regular in path," which was wrong (or the API changed): that URL returns HTTP 200 with an empty `{}` for every player, always, silently. Confirmed live against multiple real players and multiple weeks, including a completed 2025 week, that `regular` in the path (matching the stats endpoint's format) is required to get real data.
- CORS note: Direct browser fetch may fail. Fallback proxies in order: `corsproxy.io`, `api.allorigins.win`

### Anthropic API
- The "Ask Claude" tab was removed from the UI (panel and icon tab are gone)
- `getTradeAI()` was also removed in the June 2026 Trade Evaluator overhaul
- **All of it was removed 2026-08-20.** `sendAI()`, `addMsg()`, `clearChat()`, `quickPrompt()`, `aiMessages`, `LEAGUE_CONTEXT`, `QUICK_PROMPTS`, the `.ai-*` CSS block and its four theme variables are gone. Verified first that `getTradeAI` had **zero** occurrences left, so the old "do not remove — `getTradeAI()` calls them" caveat was already false. No AI markup had existed for a while either; this was an orphaned browser-side Anthropic API caller with no UI and no key. Nothing calls into it — don't reintroduce it.

---

## NAVIGATION STRUCTURE

**Consolidated to five tabs on 2026-08-21**, ahead of sharing the site with the league. It had
grown to nine tabs plus Refresh, which wrapped to two sticky rows on a phone, and three of the
labels ("Careers" for a page titled LEAGUE HISTORY, "Txns", three R-words in a row) did not
survive an outsider reading them. Nothing was deleted except the Rules panel; the rest was
merged into sub-views using the `setRosterView` self-contained-divs pattern.

### Sticky Shell
`<div class="sticky-shell">` uses `position: sticky; top: 0; z-index: 100`. It contains:
1. `<header>` -> banner wordmark (home link) + "Open in Sleeper" pill + **Refresh** + dark mode toggle
2. `<nav class="icon-nav">` -> 5 icon tabs

The header logo (`<div class="hdr-logo-link">`) calls `showTab('home')` on click - it IS the home button.

**The header is the banner and the controls, nothing else (2026-08-21).** `TOL Banner Logo.jpg`
replaced the shield, and the `.hdr-identity` block beside it - league name, "Dynasty Football",
"Established 2023 | NFL Kickoff" - was removed with it (Matt's call): the banner IS the wordmark,
so the league name was being said twice side by side. `.hdr-identity` / `.hdr-league-name` /
`.hdr-sub1` / `.hdr-sub2` and their two theme layers are gone; don't reintroduce a text block
next to a banner that already reads "THE OTHER LEAGUE". The kickoff date still lives on the home
countdown, which is the only place it was load-bearing.

**Refresh moved out of the nav and into the header on 2026-08-21** (`.hdr-refresh-btn`, still
`id="nav-refresh-btn"`, still calls `refreshData()`). It was never a destination, and the slot it
held is the one the fifth tab needed. Its label hides under 680px; the arrow stays.

### Icon Nav
Each tab is `<div class="icon-tab" onclick="showTab('id',this)" data-tab="id">` with an emoji icon and text label. The active tab gets `class="active"` and a teal bottom border. Emoji are hidden (`.itab-icon{display:none}`) - the nav is type-only.

**Five tabs at `width:20%` is exactly one mobile row, and that is the budget.** A sixth tab puts
the second row back and undoes the whole consolidation - the merges were done to buy that row.
Add a sub-view, not a tab. The `@media(max-width:680px)` rule is now `flex-wrap: nowrap`.
Verified 280-1280px, both themes: zero page overflow on every tab, nav never wraps.

### Tabs and Panels

| # | Tab Label | `showTab` ID | Panel ID | Sub-views |
|---|-----------|--------------|----------|-----------|
| <- | (logo click) | `home` | `panel-home` | - |
| 1 | **History** | `careers` | `panel-careers` | **Managers** (default) - Seasons - All Time - Hall of Fame - Rivalries |
| 2 | **Teams** | `rosters` | `panel-rosters` | **Outlook** (default) - Rosters - Player Stats |
| 3 | Scores | `scores` | `panel-scores` | year + week pills (unchanged) |
| 4 | **Moves** | `draft` | `panel-draft` | **Draft** (default) - Trades & Waivers - Who Won That Trade? - Draft ROI |
| 5 | Trade | `trade` | `panel-trade` | - |

**Panel and `showTab` ids were deliberately NOT renamed** - `rosters`, `draft`, `careers` still
name tabs now labeled Teams, Moves and History. Renaming them would have touched several hundred
call sites for a cosmetic gain. Read the table above rather than trusting an id to describe its
tab.

**Nav order is Matt's, set 2026-08-21** (History, Teams, Scores, Moves, Trade) - it replaced a
first pass ordered by expected frequency. Don't "fix" it back toward a usage argument; it is a
deliberate call. Cheap to change if he asks again - it is the order of five divs in `<nav>`, and
nothing else reads the order.

**Merged away 2026-08-21:** `panel-stats` -> Teams / Player Stats. `panel-rivalries` -> History /
Rivalries. `panel-transactions` -> Moves / Trades & Waivers. The four Careers year sub-tabs ->
one Seasons view with a year selector (`setSeasonYear`), so that row stops growing every September.

**Deleted 2026-08-21:** `panel-league` (the Rules tab), plus `buildScoring()` and `SLABELS`, whose
only consumer was its `#score-grid`. Format, lineup slots, waivers and the scoring table all
restated what Sleeper itself shows, and "Open in Sleeper" is in the header. **`SDATA` and
`applyLeagueScoring()` stay** - `SDATA` feeds `calcPts()` and therefore every point figure on the
site; only the display grid went. The one card that existed nowhere else - the voted-in 2027
`1 WRRB_FLEX -> WR/RB/TE FLEX` change - was moved to the home panel (`.home-rule-card`). Put any
future voted-in rule change there.

**Removed earlier:** "Ask Claude" (`ai` / `panel-ai`), UI 2026-08-20, JS and CSS same day.

### The Commissioner (`panel-commissioner`) — admin, no nav tab

**A sixth panel, deliberately not a sixth tab.** The nav budget is five and this does not spend
it: `panel-commissioner` has no `.icon-tab` at all. `showTab()` already tolerated that — its
`if(el)` guard means a tab with no button simply activates no button — so routing it cost one
entry in `VALID_TABS` and nothing else. Verified live: `.icon-tab` count stays 5 and
`.icon-tab.active` is empty while the panel is open.

**Reached three ways, all discreet:** a small muted `🔒 The Commissioner` button at the foot of
the Home panel (`.home-commish-link`), and the `#commissioner` / `#commish` / `#admin` hashes.
There is no link anywhere else, and nothing in the nav or header advertises it.

**The gate is a doorknob lock, not security, and the code says so.** This repo is public and
deploys to a public Pages site, so every byte of `index.html` is readable by anyone. What the
hash buys is that the *password itself* never appears in public source — which matters because
people reuse passwords — not that the panel is protected. Anyone who opens devtools is in.
**Never put a secret behind it.** In particular an Anthropic API key must never be committed;
see the Claude Assist note below.

- `COMMISH_HASH` — SHA-256 hex of the password. **The password itself is deliberately not
  recorded here or anywhere else in the repo** — writing it into a tracked file would publish it
  and defeat the only thing hashing buys. Matt holds it. To change it, run the one-liner in the
  comment above that constant in any browser console and paste the new hex in.
- **A short all-numeric password voids the hash's one benefit.** The digest is public, so it can
  be brute-forced offline; a 7-digit number is ten million candidates and falls in seconds. That
  does not weaken the panel (which was never protected anyway) but it does mean the password
  should be treated as public, and never reused anywhere that matters. If a memorable number is
  wanted, move the gate to PBKDF2 with a salt and a high iteration count.
- `commishUnlock()` / `commishLock()` / `commishUnlocked()` — the gate. Unlock is
  **sessionStorage** (`tol_commish_ok`), so closing the browser re-locks.
- **`isGradesAdmin()` now returns true for an unlocked Commissioner session as well as
  `?admin=1`.** One gate for everything administrative — the roster-grade metric cards, the
  unmatched-KTC report and the snapshot exporter all light up once you are in. `?admin=1` still
  works standalone and is unchanged.

**Two views**, switched by `setCommishView('monitor'|'claude')`:

**Data Monitor.** Every value the site displays — 31 of them — in one table, grouped by what
actually keeps it current: live Sleeper API (15), bot-fed committed file (6), hand-written (4),
hardcoded in this file (6). Each row carries where it lives, its expected cadence, its real
last-updated time and a health chip.

- `COMMISH_ROWS` is the registry and **the only place to add a value.** Each row is
  `{g, m, n, w, c, p}` — group, mode, name, where, cadence, and a `p(ctx)` probe returning
  `{ts, d, s?, h?}`. A row-supplied `s` (state) always beats the age calculation, because a
  coverage gap is not an age question.
- `commishGather()` fetches every data file **with `Date.now()` as the cache-buster, not the
  site's hourly one**. A monitor that reads an hour-old copy of the file it is monitoring is a
  liar. This is the one place that deliberately departs from the hourly-buster convention.
- Timestamps are read from what each file actually carries: `generated` (a bare date) on the
  three Phase 12 files, `ts` (ms epoch) on `ktc-values.json` and `projections-2026.json`,
  `generatedAt` (ISO) on the grade snapshot. `cmDateTs()` parses a bare `YYYY-MM-DD` as **local**
  midnight — parsed as UTC it reports a same-day build as hours old depending on the reader's zone.
- **The hand-written files have no stamp and are scored on coverage instead**, which is the truer
  signal: "week 3 recap owed, latest written is week 2" beats any file mtime.
- **A row with no timestamp renders "no stamp", never a fake age.** The first build showed
  `_commishCheckedAt` for per-load values, which read as "fetched 0s ago" and was just restating
  the clock. `cmPerLoad()` exists for that case, and `cmFromMatchups()` for the seven rows derived
  from cached matchups — when nothing has loaded them it says so and names the tab that will.
- `commishStartTimer()` / `commishStopTimer()` — re-probes every 60s and ticks the "checked Xs ago"
  label every second. **`showTab` stops the timer on leaving any other tab; do not remove that.**
  A leaked interval re-fetches every data file in this list forever in the background.

**Claude Assist — a shell, wired to nothing, on purpose.** Three modes (Team Outlook,
Start/Sit, Trade Decision) with the data each would read named on its card, plus a live context
payload preview built from what the page has already loaded. It is not connected because there
is a decision to make first: **a key written into this file would be published twice over**, on
the live site and in public GitHub source. The only safe wiring is a key pasted in once and held
in that browser's localStorage on that device, never committed. Decide that before building it out.

CSS lives in the appended `THE COMMISSIONER` layer (`.cm-*` / `.home-commish-link`), per the
redesign convention, with its light-mode overrides. **Gold needed one:** `#FFD25A` reads fine on
near-black and washes out on white, and the site has no documented light-mode gold, so the aging
state gets `#8A6300` under `[data-theme="light"]` rather than borrowing a hue that already means
something else.

**Verified in-browser, not assumed:** unlock and re-lock both work and a wrong password sets no
session; the seven matchup-derived rows flip from n/a to fresh the moment the Scores tab caches
matchups (which is what proves the probes are live rather than decorative); the poll timer starts
on entry and is null after leaving; `isGradesAdmin()` follows the session in both directions;
zero page overflow at 375px with the table scrolling inside its own `.dtblwrap`; light mode
resolves `#0E9C92` / `#D6258F` / `#8A6300`; no console errors on a clean load.

### URL Hash Routing
`showTab(tab, el)` calls `history.replaceState(null,'','#'+tab)`. On boot, `routeFromHash()` reads `location.hash`. `hashchange` is also wired. Valid tab IDs are in `VALID_TABS`.

**`TAB_ALIASES` keeps every retired hash working.** Links to this site get texted around the
league and saved in people's notes, so a hash that used to be a tab has to land somewhere real.
Each alias names the tab its content moved into and, where it became a sub-view, an `open()` that
switches to it - run BEFORE `showTab`, so the "build the default view on entry" hooks do not build
a page about to be hidden. `showTab` then rewrites the URL to the new canonical hash.

| Retired hash | Lands on |
|---|---|
| `#stats` | Teams / Player Stats |
| `#rivalries` | History / Rivalries |
| `#transactions`, `#txns`, `#trades` | Moves / Trades & Waivers |
| `#league`, `#rules` | Home (where the 2027 rule card now lives) |
| `#teams`, `#outlook`, `#history`, `#managers`, `#seasons`, `#moves` | the natural new names |

**Add an alias whenever a hash stops being a tab.** All 19 hashes were verified to resolve to a
live panel after the consolidation.

### `body.is-home` CSS Class
`document.body.classList.toggle('is-home', tab==='home')` - set in HTML on `<body class="is-home">` at load, toggled in `showTab()`. CSS rules under `body.is-home` hide the cache bar and utility strips, and give the home panel edge-to-edge layout.

### Home Panel (`panel-home`)
- `TOL Large Logo.png` hero with neon glow (`.home-hero-logo`)
- NFL countdown to **Sep 9, 2026 8:20 PM ET** - `startCountdown()`; IDs `cd-days`/`cd-hours`/`cd-mins`/`cd-secs`
- 2025 Champion card: Jake Blackwell / "Nacua Matata" / Pick 1.12
- **2027 Rule Change card** (`.home-rule-card` / `.hrc-kicker` / `.hrc-rule` / `.hrc-note`) - rescued from the deleted Rules panel, 2026-08-21
- League meta pills: Commissioner - Matt Bova, Est. - 2023, Dynasty - 12 Teams

**Removed from home panel:** Consolation winner card (Nick Merkel), Quick-nav grid.

### Teams Panel (`panel-rosters`)
Three views via `setRosterView('grades'|'teams'|'stats', el)`, each with its own title and
subtitle from `ROSTER_VIEW_META` - a fixed "LEAGUE ROSTERS" header described none of the other two.

0. `#roster-view-grades` (**"Outlook"**) - **the default view as of 2026-08-21** (Matt's call: it
   is the page the league actually opens this tab for). `#roster-grades-container`, Phase 6.
1. `#roster-view-teams` (**"Rosters"**) - the 12 roster cards, position legend, team chips.
2. `#roster-view-stats` (**"Player Stats"**) - moved in from the old `panel-stats`, lazy-built.

**Making Outlook the default broke three things that only mattered once it opened on tab entry**,
all fixed the same day - do not undo them:
- `buildRosterGrades()` used to bail with *"give it a second and reopen this view"* when
  `cachedRosters` was still loading. That never fired when you had to click into it; as the default
  it fires on any cold phone. It now awaits `_rosterReady` (the same race guard used at the profile
  overlay), capped at 8s, and falls back to a real message rather than a dead end.
- It rebuilt everything on every switch (KTC fetch + picks map + every snapshot). Guarded now by
  `_gradesBuilt` / `_gradesBuilding`; `refreshData()` clears the flag and rebuilds in place if the
  Outlook view is the one on screen.
- `setRosterView` used an unscoped `.roster-view-toggle .yr-btn` selector, which also matched the
  grade-period tabs `renderRosterGrades()` emits *inside* the Outlook view - so switching views
  cleared the active period tab. Invisible only because of the rebuild above. **Both selectors are
  now scoped to their own toggle id** (`#teams-view-toggle`, `#history-view-toggle`); keep them that way.

`setRosterView` returns the build promise so `showPlayerStats()` can await it before scrolling to a row.

### History Panel (`panel-careers`)
Five views via `setCareersView('profiles'|'seasons'|'records'|'hof'|'rivalries', el)`, per-view
titles from `HISTORY_VIEW_META`. **Five is the ceiling** - the row is already at its width.

0. `#careers-view-profiles` (**"Managers"**) -> `#profile-grid`, the default. `buildProfileGrid()`.
1. `#careers-view-seasons` (**"Seasons"**) -> the year selector `#season-yr-toggle` plus one
   `#careers-view-<year>` div per season in `CAREER_YEARS`, switched by `setSeasonYear(year, el)`
   and lazy-built by `buildSeasonYear(year)`. **This replaced four top-level year sub-tabs on
   2026-08-21** - that row grew by one every September and had crowded out room for Rivalries.
2. `#careers-view-records` (**"All Time"**) -> `#careers-container`: career table + record book.
3. `#careers-view-hof` (**"Hall of Fame"**) -> `#hof-container`, lazy-built by `buildHallOfFame()`.
4. `#careers-view-rivalries` (**"Rivalries"**) -> the 6 rivalry cards, the H2H explorer and the
   nemesis board, moved from `panel-rivalries`. They were the only head-to-head history living
   outside this tab. `buildRivalries()` still runs at boot and on every switch to this view.

**Adding a season** = one button in `#season-yr-toggle` + one empty `#careers-view-<year>` div
inside `#careers-view-seasons`, a new entry at the front of `CAREER_YEARS`, plus the
`SEASON_HISTORY` / `PLAYOFF_BRACKET_INFO` entries a finished season needs anyway. A year with no
`SEASON_HISTORY` entry renders as the live season automatically.

**The 7-pill `.career-status-bar` is gone.** Those stats are the first cards of the Hall of Fame grid, so a superlative lives in exactly one place.

### Moves Panel (`panel-draft`)
Four views via `setMovesView('draft'|'txn'|'roi'|'drafteval', el)`, titles from `MOVES_VIEW_META`. Draft is
the default. `#moves-view-draft` holds the rookie-draft year toggle, team chips and list/board
views; `#moves-view-txn` holds the transaction log moved from `panel-transactions`;
`#moves-view-roi` is **Who Won That Trade?** (Phase 12), added 2026-09-04. Both `txn` and `roi`
lazy-load on first switch via their container's `dataset.loaded` flag, set in `setMovesView`.

`#moves-view-drafteval` is **Draft ROI** (Phase 12 item 4), added 2026-09-04 — same
`trade-roi.json`, different question. Four sub-views is within budget; History runs five.

`#whowon`/`#traderoi` (trade view) and `#draftroi`/`#bestdrafter` (Draft ROI) are `TAB_ALIASES`
deep links — not retired hashes,
but so the page can be texted round the league and land on itself rather than the Moves default.

---


## REMOVED / HIDDEN ELEMENTS

- **Sidebar** (`.sidebar`) — **fully removed 2026-08-20.** Markup, `buildSidebar()`, `scrollToTeam()`, the boot call and the `.sidebar`/`.sb-label`/`.t-item`/`.t-av`/`.t-info`/`.ti-n`/`.ti-o` CSS are all gone. It had been `display:none` while still running a DOM-building pass on every page load, and `scrollToTeam` targeted `.tab[onclick*="rosters"]` — a selector the icon-nav rewrite had already broken.
- **Cache bar** (`.cache-bar`) — `display: none !important` inline style — the "Cached data · Last fetched Xm ago · Refresh" row is hidden. The DOM elements and IDs (`cache-dot`, `cache-status-txt`, `refresh-btn`) still exist in the HTML so `setCacheBar()` and `refreshData()` work correctly.
- **Sleeper bar** (`.sleeper-bar`) — removed from HTML. "Open in Sleeper" link moved to the header.

---

## KEY ELEMENT IDs

### Header
- `hdr-logo` - the banner wordmark img; `hdr-logo-link` - its wrapper, the home button
- `t-icon`, `t-lbl` — theme toggle icon and label
- `cache-dot` — colored dot (live vs cached) — inside hidden `.cache-bar`
- `cache-status-txt` — cache status message — inside hidden `.cache-bar`
- `refresh-btn` — original refresh button — inside hidden `.cache-bar`; `refreshData()` still uses it programmatically

### Perpetual Stats (inside `panel-careers`) — **REMOVED 2026-08-20**
The `stat-champs` / `stat-earn-*` / `stat-wins-*` / `stat-cons-*` / `stat-picks-*` / `stat-trades-*` / `stat-worst-*` IDs no longer exist. Every one of those stats survives as a card in the Hall of Fame & Shame grid — look for its label in `buildHallOfFame()`, not for an ID.

### Scores Panel
- `scores-container` — main scores area

### Rosters Panel
- `rosters-container` — roster grid (12 `r-card` divs)
- `roster-card-{uid}` — individual roster card per team
- `roster-team-chips` — multi-select team filter chip bar (built by `buildTeamFilterChips`)
- `teams-title` / `teams-sub` — the panel heading, rewritten per view from `ROSTER_VIEW_META`
- `teams-view-toggle` — the three view buttons. **Selectors targeting them must be scoped to this id** — see NAVIGATION STRUCTURE / Teams Panel for the bug an unscoped `.roster-view-toggle` selector caused.
- `roster-view-grades` / `roster-view-teams` / `roster-view-stats` — the three views, toggled by `setRosterView('grades'|'teams'|'stats', el)`. **`grades` ("Outlook") is the default** as of 2026-08-21.
- `rview-grades-btn` / `rview-teams-btn` / `rview-stats-btn` — the view buttons
- `roster-grades-container` — Phase 6 output; built by `buildRosterGrades()` on tab entry, guarded by `_gradesBuilt`
- `grade-period-tabs` — grading-period tab bar; rendered only when more than one period is available to the viewer
- `gr-row-{uid}` — one team's grade row; gets `.open` when expanded (`toggleGradeRow`)
- `grade-card-{uid}` — per-team raw-metric card, **admin only** (`?admin=1`), rendered by `renderGradeAdminCard`. Still reuses `.r-card`/`.rch`/`.rcb`/`.pg`.

### Rivalries (now History > Rivalries, `#careers-view-rivalries`)
- `rivalry-grid` — the 6 official rivalry cards
- `h2h-picker-grid` — Phase 2 clickable 12x12 all-time matchup grid (`buildH2HPicker`)
- `h2h-detail` — Phase 2 selected-pair detail card + game log (`renderH2HDetail`)
- `nemesis-board` — Phase 2 per-manager worst-opponent table (`buildNemesisBoard`)

### Draft Panel
- `draft-view-past` — visible by default; all years including 2026 render here via `buildDraftHistory()`
- `draft-view-2026` — hidden by default (`display:none`); reserved for future use; `d26-tbody` is unpopulated
- `d26-list-view`, `d26-board-view`, `d26-tbody` — inside the hidden 2026 view
- `draft-history-container` — inside `draft-view-past`; holds rendered picks
- `draft-team-chips` — multi-select team filter chip bar above the year toggle

### Player Stats (now Teams > Player Stats, `#roster-view-stats`)
- `stats-yr-toggle`, `stats-pos-filter`, `stats-wk-filter`, `stats-container`
- `sg-pass`, `sg-rush`, `sg-rec` — stat group toggle buttons (Passing / Rushing / Receiving); toggling rebuilds the table
- `stats-team-chips` — multi-select team filter chip bar (includes "All Teams" + "Free Agents" + one chip per team); built once by `buildStatsTeamChips()`; filters rows via `applyStatsFilters()` show/hide (no re-fetch)

### Who Won That Trade? (Moves > `#moves-view-roi`, Phase 12)
- `mview-roi-btn` — the third Moves view button
- `roi-filter-bar` — All Trades / Graded / Too Early / Lopsided (`setROIFilter`)
- `roi-team-chips` — manager multi-select, keyed on **user_id** (`toggleROITeam`)
- `roi-container` — the card grid, rendered by `renderROICards()`
- `roi-how` — the collapsible "How is this scored?" explainer (`toggleROIHow`)

### Draft ROI (Moves > `#moves-view-drafteval`, Phase 12 item 4)
- `mview-drafteval-btn` — the fourth Moves view button
- `drafteval-container` — everything, rendered in one pass by `renderDraftEval()`
- `de-basis` — the class-adjusted / raw expectation toggle (`setDraftEvalBasis`)

### Transactions (now Moves > Trades & Waivers, `#moves-view-txn`)
- `moves-title` / `moves-sub` — the Moves panel heading, rewritten per view from `MOVES_VIEW_META`
- `moves-view-draft` / `moves-view-txn`, `mview-draft-btn` / `mview-txn-btn` — the two Moves views and their buttons
- `txn-container`, `txn-yr-toggle`, `txn-filter-bar`, `txn-player-search`, `txn-player-results`
- `txn-team-chips` — multi-select team filter chip bar (replaced the old `txn-team-filter` dropdown)

### History Panel (`panel-careers`)
- `history-title` / `history-sub` — the panel heading, rewritten per view from `HISTORY_VIEW_META`
- `history-view-toggle` — the five view buttons; **scope selectors to this id** so the year buttons inside Seasons are never cleared by a view switch
- `careers-view-profiles` / `-seasons` / `-records` / `-hof` / `-rivalries` — the five views, toggled by `setCareersView(view, el)`
- `cview-profiles-btn` / `-seasons-btn` / `-records-btn` / `-hof-btn` / `-rivalries-btn` — the view buttons
- `season-yr-toggle`, `syr-<year>-btn`, `careers-view-<year>` — the year selector and year divs **inside** the Seasons view, switched by `setSeasonYear(year, el)`
- `careers-container` — career table + record book (**All Time** view)
- `record-book` — All-Time Record Book card grid, rendered by `buildRecordBook()`
- `hof-container` — Hall of Fame & Shame card grid, rendered by `buildHallOfFame()`
- `standings-tbody-<year>` / `standings-thead-<year>` — that season's standings table, now inside its year view
- `season-recap-<year>` — the recap block under the split; filled asynchronously by `renderSeasonRecap(year)`
- `.ss-standings` / `.ss-payouts` / `.ss-recap` — the three blocks of a year view (no ids; there is one of each per view)

### Trade Evaluator Panel (`panel-trade`)
- `ktc-badge` — green = live/cached KTC values; yellow = snapshot fallback
- `ktc-updated` — "Cached Xh ago" or "Updated just now"
- `pick-scaler` — range input (-50 to +25); 0 = Balanced = 80% of KTC raw pick value
- `pick-scaler-val` — badge label for current slider position
- `trade-give-team`, `trade-receive-team` — team select dropdowns
- `trade-give-content`, `trade-receive-content` — player+pick checkbox lists
- `trade-results` — result box (hidden until Evaluate Trade clicked)
- `ktc-table-section` — collapsible Player Values section (hidden by default)
- `ktc-toggle-btn` — Show/Hide toggle for `ktc-table-section`
- `ktc-search` — player name search input
- `ktc-pos-chips` — position filter pills (All/QB/RB/WR/TE/Picks) using `f-pill pos-*` classes
- `ktc-team-chips` — team filter pills (All Teams + 12 owners + Free Agents) using `f-pill`
- `ktc-table-container` — rendered `.ktc-tbl` table

### Countdown (Home Panel)
- `countdown-display`, `cd-days`, `cd-hours`, `cd-mins`, `cd-secs`

---

## JAVASCRIPT FUNCTIONS

### Theme
- `toggleTheme()` — toggles `data-theme` on `<html>`, saves to `localStorage`
- `applyTheme()` — restores saved theme on page load

### Cache
- `saveCache(rosters)` — writes roster data + timestamp to `localStorage[tol_cache_v2]`
- `loadCache()` — returns `null` if missing or older than 6h
- `clearCache()` — removes `tol_cache_v2`
- `savePerm(key, data)` / `loadPerm(key)` — permanent localStorage (no TTL, for historical data)
- `setCacheBar(fromCache, ts)` — updates cache dot, text, refresh button (still called even though bar is hidden)
- `refreshData()` — clears cache, resets state, re-runs `init()`

### Sleeper API
- `api(path)` — fetches from Sleeper with CORS fallback chain (direct → corsproxy.io → allorigins.win)
- `findLeagueIds()` — walks `previous_league_id` chain to discover past season IDs; caches in `tol_lids`

### Matchups / H2H
- `fetchAllMatchups(leagueId, year)` — fetches all 17 weeks; caches in `tol_matchups_{year}`
- `buildH2HMap()` — all-time H2H record map from all cached seasons; returns `h2h[ridA][ridB] = {w, l}`
- `buildH2HForYear(year)` — same but single season

### All-Time Stats Engine (Phase 1 — built 2026-08-20)
`buildLeaderStats()` **no longer exists** — it was renamed `buildHallOfFame()`, and the recomputation behind it moved into a shared engine. It used to rebuild the entire H2H and median maps from scratch on every one of its ~6 call sites.

- `buildAllTimeStats()` — **the entry point.** One walk over every cached `tol_matchups_{year}` (2023–2026, regular-season weeks 1–14 only) returning `{hasData, games, seasons, per, rec}`. `per[uid]` carries gp / pf / pa / ppg / papg / scores / stdev / h2hW-L / medW-L / winPct / luckyW / unluckyL / weekHigh / weekLow / avgMov / seasonPF / streaks; `rec` carries the single-game and single-season extremes. Memoized in `_allTimeCache`.
- `invalidateAllTimeStats()` — **must be called by anything that writes `tol_matchups_*`.** `fetchAllMatchups()` already does. Without it the cards freeze at whatever was cached on the first pass, because the boot prefetch lands 2023/2024/2025 one season at a time.
- `weekWasPlayed(weekData)` — **the guard that fixed a real, live bug.** An unplayed Sleeper week returns 12 rows with a real `matchup_id` and `points: 0.0` (verified against the live 2026 payload — all 17 weeks are paired months before kickoff). The median math evaluated `0 > 0` as false for all twelve teams and booked everyone a median **loss** for every unplayed week, so merely opening the Scores tab in the preseason silently added 14 phantom losses per owner per cached future season. Confirmed by loading the pre-change file side by side: Matt Bova's median record read 10-46 (56 games) instead of 10-32 (42), and his career Total W-L read 25-73 instead of 25-59. The guard now sits in `buildAllTimeStats`, `buildMedianMap`, `buildH2HMap`, `buildH2HForYear` and `buildSeasonStandingsData` — **don't drop it from any of them.**
- **Two week-bound bugs found in the 2026-08-20 regular-season audit** (the Phase 1 code was already correct; these were pre-existing):
  1. `buildH2HForYear(year, maxWeek)` defaulted to **17**. Every caller happened to pass an explicit 14, so it was never exercised — but it was a trap for the next caller. Default is now `REG_WEEKS`. Verified: the default now returns 84 games for 2025 (14 × 6) where an explicit 17 returns 98, i.e. the bracket would have added 14 games of noise per season.
  2. The **live-season standings** derived `maxWeek` by scanning all 17 weeks for the latest played one and handing that straight to `buildSeasonStandingsData`. From Week 15 of a live season onward it would have folded playoff and consolation results into the regular-season W/L, PF and PA, and captioned itself "Through Week 17". Now capped at `REG_WEEKS`. Verified by injecting a completed 17-week season as 2026 data: the table holds at 28 games per team (14 H2H + 14 median) and the caption reads "Through Week 14".
- `computePlayoffAppearances()` — playoff berths per owner, **derived** from `PLAYOFF_BRACKET_INFO` rather than hardcoded a second time: the union of everyone appearing in a "Winners Bracket" game in a year is exactly the six-team field (the two first-round byes turn up in the semifinal row). Verified to sum to 18 = 6 × 3 seasons. Keys there are owner *names*, so it maps back through `TEAMS`.
- `computePickCounts()` / `computeTradeCounts()` / `computeAddCounts()` — per-owner draft picks, trades, and waiver + free-agent adds. Each returns **`null` if any completed season is still unfetched**, so the card renders "Visit the X tab to load" instead of crowning a leader computed from half the data.
- `computeCareerLedger()` — earnings, per-season placement and average finish from static `SEASON_HISTORY`.
- `leaderBody(map, dir, fmt, gate)` — turns a `uid → value` map into a card body: the leader (**all** of them when tied) plus the next two placings. `dir` -1 = highest value wins, 1 = lowest wins.
- `hofCard(cfg)` — renders one `.hof-card`. `tone:'bad'` adds `.shame` (magenta); `wide:true` spans two grid columns.

### Careers
- `CAREER_YEARS` — `[2026, 2025, 2024, 2023]`, newest first. Must match the buttons and `#careers-view-<year>` divs in the markup.
- `setCareersView(view, el)` — History sub-tab switcher (`profiles`/`seasons`/`records`/`hof`/`rivalries`); sets the per-view title from `HISTORY_VIEW_META` and lazy-calls `buildProfileGrid()` / `buildHallOfFame()` / `buildRivalries()` / `setSeasonYear()`
- `setSeasonYear(year, el)` — year selector inside the Seasons view; what the four top-level year sub-tabs became on 2026-08-21. Shows one `#careers-view-<year>` and lazy-builds it. `currentSeasonYear` holds the selection.
- `setMovesView(view, el)` — Moves sub-tab switcher (`draft`/`txn`); sets the title from `MOVES_VIEW_META` and carries the transactions lazy-load flag that used to live in the `showTab` hook
- `buildCareers()` — All Time view: career earnings/placement table, then `buildRecordBook()`, then `rebuildSeasonYears()`
- `buildSeasonStandings(container)` — **gone (2026-08-21).** It stacked 2026 + 2025 + 2024 + 2023 under the Records view; the per-year pieces are now `seasonStandingsRows()` / `seasonStandingsTable()` / `buildSeasonYear()`.
- `buildRecordBook()` — 12 record cards: highest/lowest single week, biggest blowout, closest finish, highest/lowest-scoring matchup, longest win/losing streak, most/fewest points in a season, most championships, most playoff berths. **Streaks deliberately run across season boundaries.** Single-season point records only count *complete* 14-week seasons, so a live or half-cached year can't walk away with "fewest points ever".
- `seasonStandingsRows(year)` — one season's rows. **A season is "complete" iff `SEASON_HISTORY[year]` exists** — that is the only place final placements live, so it is the honest test, and it means a new live season needs no code edit. Completed years order by playoff result, a live one by total wins with PF as tiebreaker. Returns `null` only when a *completed* year has no cached matchup data, which is the "visit the Scores tab" case. The `REG_WEEKS` cap on the live-season week scan is carried over verbatim from the old `buildSeasonStandings` — see the two week-bound bugs above; don't drop it.
- `seasonStandingsTable(year)` — `{caption, html}` for that table, and registers the rows with `standingsRowData` so `sortStandingsByCol` keeps working.
- `buildSeasonYear(year)` — one year sub-tab: title, caption, then `.season-split` holding the standings and that season's payout card, with `.ss-recap` under both. Idempotent, so `rebuildSeasonYears()` can re-run it.
- `payoutCardHtml(year)` — one season's payout card from `SEASON_PAYOUTS`. Reuses the `.ic` / `.ir-row` / `.ik` / `.iv` classes the League panel already had rather than inventing a surface, so it inherits both themes for free. Returns `''` for a year with no entry, and `buildSeasonYear` then omits the column entirely.
- `rebuildSeasonYears()` — re-renders every year view already built (`dataset.loaded`). Called from `buildCareers()`, which itself re-runs when the boot matchup prefetch lands — exactly when a year tab opened early is still showing an empty table.
- **`renderStandingsTbody` gained a `pending` row flag** — a live season with no games played carries a place only for stable ordering, so it renders `—` instead of handing the alphabetically-first owner a 🏆 in August.
- `buildHallOfFame()` — 19 award cards: the 7 former pills (Past Champions, Career Earnings, Career Wins, Consistent Finisher, Draft Picks, Trades, Worst Finish) plus Best All-Time Win %, Best/Worst Scoring Average, Most Weekly Crowns/Duds, Luckiest/Unluckiest Manager (measured against the weekly median), Mr. Reliable / Boom or Bust (score std dev), Punching Bag, Most Lopsided Wins, and Waiver Wire Warrior.

### Scores Tab
State variables: `currentScoresYear` (default 2026), `currentScoresWeek` (default 1)

- `buildScores()` — fetches matchups for `currentScoresYear` via `findLeagueIds()` + `fetchAllMatchups()`, then calls `renderHistoricalScores()`
- `renderHistoricalScores(container, matchups, week, projTotals)` — renders matchup cards; shows a projected score + `PROJ` chip for any team that hasn't scored yet and has a projection; applies bracket chips from `PLAYOFF_BRACKET_INFO`; applies rivalry banner from `RIVALRY_WEEKS`.
  **2026-08-20 fix:** this used to read `entry.projected_points` from the matchups payload. **Sleeper's matchup endpoint has no such field** — verified live, it returns `roster_id`/`points`/`matchup_id`/`starters`/`players`/`players_points`/`starters_points` and nothing else — so the value was always `null` and every 2026 matchup rendered `—` forever. The two helpers written to fix this (`fetchWeekProjections`, `calcTeamProjected`) were never wired to a caller, and `fetchWeekProjections` used the dead URL form on top of that. All three are gone; projections now come from `computeWeekProjections()`.
- `setScoresYear(year, el)` — switches year tab, resets to W1, calls `updateRivalryPills(year)`, rebuilds scores
- `setScoresWeek(week, el)` — switches week pill, rebuilds scores
- `goToScoresWeek(year, week)` — navigates from Rivalries tab: switches to scores tab, sets year+week, calls `updateRivalryPills(year)`, rebuilds scores
- `updateRivalryPills(year)` — toggles `.rivalry` class on W4/W13 pills based on `RIVALRY_WEEKS[year]`; called whenever year changes

### Matchup Commentary (Phase 8 — built 2026-08-21)
Hand-written write-ups under each matchup on the Scores tab, collapsed behind a click-to-open strip. See DEVELOPMENT ROADMAP Phase 8 for scope and the writing rules.

- `loadCommentary(year)` — fetches `matchup-commentary-<year>.json` (same no-CORS + hourly cache-buster pattern as `loadProjectionsFile`), memoized per year in `_commentaryPromise`. Returns `null` for any year with no file, which is the normal case for 2023/2024/2026 — a missing file must never break the scoreboard.
- `renderCommentaryBlock(commentary, week, matchupId)` — returns `''` when there's no entry for `week|matchup_id`, so consolation games and unwritten seasons render **no toggle at all**. An empty toggle is worse than none.
- `toggleMatchupCommentary(key, el)` — pure show/hide on `#mc-body-<week>-<matchupId>`, plus `.open` on the strip (rotates the chevron). No re-render, no refetch.
- **The collapsed strip reads "Matchup Recap"** (Matt, 2026-08-21), not the headline. It used to preview the headline, which gave the punchline away before the click.
- `esc(s)` — HTML-escape helper. **There was no escape helper in this file before Phase 8**; commentary is our own prose but it goes through `innerHTML` and is full of apostrophes and ampersands, so it is escaped rather than trusted. Reuse it for any new string-into-`innerHTML` work.
- CSS lives in the appended `SCORES TAB — MATCHUP COMMENTARY` layer (`.mc-*`), per the redesign convention.

### Season Recaps (Phase 9 — built 2026-08-21)
The prose beside each Careers year tab. See DEVELOPMENT ROADMAP Phase 9 for scope and the writing rules.

- `loadSeasonRecaps()` — fetches `season-recaps.json` (same no-CORS + hourly cache-buster pattern as `loadCommentary`), memoized in `_recapsPromise`. **One file for every season**, unlike matchup commentary's per-year files — there are only ~350 words a year, so a fetch per tab click would be silly.
- `renderSeasonRecap(year)` — fills `#season-recap-<year>`. **Re-queries the element after the await** — `buildSeasonYear` can re-render the view out from under an in-flight fetch. A missing file, or a year with no entry, renders a one-line note and never breaks the standings table beside it.
- Shape per year: `{headline, facts: [{k, v}], paragraphs: []}`. `facts` are the season-at-a-glance chips (champion, runner-up, reg-season #1, top score, the 1.13); `paragraphs` is the write-up.
- CSS in the appended `CAREERS TAB — SEASON YEAR TABS` layer (`.season-split` / `.ss-*` / `.sr-*` / `.pay-*`). **`.season-split` is a wrapping flexbox on purpose** — the table hugs its content, the payout card takes the rest, and when there is no longer 300px left for it it drops underneath on its own. No breakpoint decides that, so it behaves inside a narrow *container*, not just a narrow viewport.
- **The recap is a block under the split, not a third column.** At ~350 words a third column would either squeeze the standings or run to unreadable line lengths; `.ss-recap` is capped at 900px as a measure limit, not a layout constraint.

### Survivor Pool + Weekly League Recap (Phase 10 — built 2026-08-21)
Two things that share the top of a Scores week: the whole-league write-up, and the survivor
tracker underneath it. See DEVELOPMENT ROADMAP Phase 10 for scope and the weekly workflow.

**The survivor pool is COMPUTED, never hand-recorded.** `computeSurvivor(year, matchups)` derives
the whole elimination chain from the same matchup payload the grid below it renders from, so the
tracker cannot drift from the scores sitting six inches under it. Do not add a hardcoded
elimination list; that is the one thing this design exists to prevent.

- `SURVIVOR` — config per year: `{pot, firstWeek, finalWeek, showThrough}`. 2026 is
  `{35, 1, 11, 12}`. **The pool settles after Week 11, not Week 12.** Matt's original note said
  week 12, but 12 teams minus one a week from Week 1 leaves the last man standing after Week 11 —
  he confirmed that cadence on 2026-08-21. `showThrough: 12` is why Week 12 still renders the
  block: it holds the settled result rather than vanishing the moment it is decided.
- `computeSurvivor(year, matchups)` — walks `firstWeek..finalWeek`. Each played week, the alive
  team with the LOWEST score is out (win or loss is irrelevant). Returns
  `{cfg, year, weeks, champion, alive}`; each week is
  `{week, played, aliveBefore, aliveAfter, scores, eliminated, elimPoints, tied, crowned}`.
  Returns `null` for any year with no `SURVIVOR` entry, which is 2023–2025.
  - **The `stalled` latch matters.** Once one week is unplayed, every later week is marked
    unresolved regardless of what data it holds — otherwise a Week 5 that somehow had scores could
    eliminate someone while Week 4 sat unplayed.
  - **Ties are broken on fewest season points to date**, not a coin flip, and `tied` is set so the
    UI says out loud that a tiebreak was needed. Scores carry two decimals, so this should never
    fire; it exists so that if it does, nobody thinks the site picked at random.
- `survivorBlockHtml(sv, week)` — the tracker. Renders for **every** week `1..showThrough`,
  including unplayed ones: a manager opening Week 6 in September should still be told the pool
  exists and who is in it. Five states — not played / eliminated + who's left / crowned /
  settled (week 12) / no elimination.
- `loadWeeklyRecaps(year)` — fetches `weekly-recaps-<year>.json`, memoized per year in
  `_weeklyRecapsPromise`. Same no-CORS + hourly cache-buster pattern as `loadCommentary()`.
- `renderWeekTopBlock(recaps, sv, week)` — the top block. **Either half can be missing.** With no
  write-up but a live pool it emits `.wr-bare` — the tracker alone, card chrome collapsed, rather
  than an empty recap card dragging it along. With neither, it returns `''`.
- Wired in `buildScores()` (loads recaps alongside commentary in one `Promise.all`, computes
  survivor from `matchups`) and `renderHistoricalScores()`, which gained two params. **The top
  block is built before the no-pairs early return and prepended on that path too** — a week with
  no matchup data yet still needs to show the pool is running.
- CSS in the appended `SCORES TAB — WEEKLY LEAGUE RECAP + SURVIVOR POOL TRACKER` layer
  (`.wr-*` / `.sv-*`). Deliberately echoes the Careers `.sr-card` recap — same kicker, italic
  Saira head, fact strip, DM Sans body — so the site's two prose surfaces read as one thing in
  two places. It is a **separate class set** because this one carries the survivor block and
  `.sr-card` must never grow one.

**Verified 2026-08-21** by replaying the engine over the completed 2025 season: 11 clean
eliminations, one a week, ending on a single champion after W11, no ties. Reconciles by
construction. (Jake Blackwell, who won the 2025 title, would have been the first team out.)

### The Median Game on the Scores tab (2026-08-21)
This league plays **two games a week** — the opponent, and the league median. The Scores card now shows both.

- `weekMedianOf(weekData)` — the median of every scored entry in a week. **Extracted so `buildMedianMap()` and the Scores tab share one implementation** and can never disagree about what the median was; `buildMedianMap()` was refactored onto it. Verified unchanged after the refactor: every owner still at exactly 42 median games, 252 median wins across 252 games, Matt Bova still 10-32 (the known-correct post-`weekWasPlayed` value).
- `weekHasMedian(week, weekData)` — `week <= REG_WEEKS && weekWasPlayed(weekData)`. **There is no median game in weeks 15-17** — those are the brackets, only 8 of 12 teams play, and a "median" of that field is meaningless. Verified: W13/W14 render it, W15/W16/W17 render nothing at all.
- **`.wk-rec` chip** on each side of the card: the team's whole week as `2-0` / `1-1` / `0-2` (teal / muted / magenta), with a `title` spelling out the median comparison. This is the single clearest answer to "did they get the extra win" — it folds the H2H and median results into one token.
- **`.match-med` strip** under the scores carries the median score itself.
- Both are suppressed for **projected** scores (`aIsProj`), so a team that hasn't played can't be shown banking a 2-0 it hasn't earned. Verified: 2026 shows 12 PROJ chips and zero median UI.
- Works retroactively for 2023/2024 as well as 2025.
- CSS in the appended `SCORES TAB — MEDIAN GAME` layer.

**`.match-grid` overflow fix (2026-08-21).** `repeat(auto-fill,minmax(290px,1fr))` → `minmax(min(290px,100%),1fr)`. Below a 290px container the card could not shrink and pushed 23px past the viewport at 280px wide. **Pre-existing, not caused by the commentary block** — verified by removing the `.mc-*` elements from the DOM and re-measuring (card stayed 290px in a 252px grid). Exactly the same bug, and the same fix, as `.roster-grid` on 2026-08-20.

### Projections Data Layer
Everything projected on the site funnels through here, so "projected points" always means *scored under this league's rules* (`calcPts`/`SDATA`), never Sleeper's generic `pts_ppr`.

- `getNflState()` — cached `/state/nfl`. Used instead of hardcoded years so Scores/Stats keep working in 2027 without an edit.
- `getLiveProjectionWeek(year)` — which week is worth spending a live API request on. Returns `1` during preseason (Sleeper reports `season_type: 'pre'` with its own week numbering, unrelated to the fantasy week).
- `loadProjectionsFile(year)` — fetches the committed `projections-<year>.json` (same no-CORS pattern as `ktc-values.json`); `null` if absent.
- `fetchWeekProjectionsLive(year, week)` — one week straight from Sleeper, memoized in `_projCache`.
- `getWeekProjections(year, week)` — **the entry point.** Live API for the current week (so mid-week injury news isn't stale), committed file for everything else, live as the fallback if the file is missing. Returns raw stat lines.
- `getWeekProjectedPoints(year, week)` — the above run through `calcPts()`, keyed by player_id.
- `projectTeamWeek(entry, roster, pointsByPid, rosterPositions)` — one team's projected total from the manager's **actual** starters. Unset slots (`"0"`) are **not** scored as zero — at least one team in this league leaves half its lineup blank in preseason (roster 9, 5 of 11 empty, confirmed live), and reading that as "this team will score 60" is simply wrong. Empty slots get filled with the best eligible player left on the roster, most-restrictive slot first, and the count comes back as `autoFilled` so the UI can mark the card with a `●`.
- `computeWeekProjections(year, week, weekEntries)` — `roster_id → {total, autoFilled}` for a whole week.

**Why a committed file at all:** pulling all 17 weeks live is ~10 MB, which is what the Stats tab did on every single visit. `scripts/fetch_projections.py` trims the same data to skill players and the ~30 keys this league scores — 1.4 MB raw, **~176 KB gzipped** — and a daily Action commits it. The live fallback means nothing breaks if the bot stops running.

**The trim is verified lossless, not assumed** (2026-08-20). Three things it could have dropped, each checked against live data:
1. *Positions.* It keeps QB/RB/WR/TE only. The league has no K/DEF slots, and a sweep of all 12 rosters found **0** non-skill players out of 361 — nothing to lose.
2. *Stat keys.* Every key the UI renders or `calcPts()` scores is in `STAT_KEYS`, and none is kept unnecessarily — diffed mechanically against every `stats.<key>` read in `index.html`.
3. *Which players survive the filter.* Then the decisive test: projected points recomputed for every rostered player for all 17 weeks, from the trimmed file vs. straight from the live API. **6,137 player-weeks, 0 mismatches, worst season-level delta 0.00.**

**Do not filter players on `pts_ppr`.** The first version of the script did, and it's the wrong yardstick — that's Sleeper's *generic* scoring, which weighs things differently than this league (flat PPR, no distance buckets, no return yards), so it lets Sleeper decide who matters to us. It would drop e.g. a pure return specialist who scores here via `kr_yd`/`pr_yd` at 0.04/yd but rounds to nothing under generic PPR. The gate is now "has at least one stat this league scores" (any key other than `gp`), which recovered 5 player-weeks the `pts_ppr` gate had silently dropped, at identical file size.

**The endpoint needs `regular` in the PATH:** `/projections/nfl/regular/{season}/{week}` returns real data; `/projections/nfl/{season}/{week}?season_type=regular` returns **HTTP 200 with an empty `{}` for every player**, silently. Confirmed again 2026-08-20: the working form returns 953 players with a populated `pts_ppr` for 2026 W1, the dead form returns 7,623 entries and **zero** with any points.

### Team Filter Chips (shared — Rosters, Draft, Transactions)
State variables: `currentTxnTeams`, `currentRosterTeams`, `currentDraftTeams` — each a `Set` of `roster_id` numbers; empty = all teams.

- `buildTeamFilterChips(containerId, teamSet, onToggle)` — builds "All Teams" + one chip per team into the container div; guarded by `dataset.built` so it only runs once per container
- `syncTeamChips(containerId, teamSet)` — updates active state on chips to match the current Set
- `uidToRid(uid)` — converts a `user_id` string to its numeric `roster_id`
- `applyRosterFilter()` — shows/hides `r-card` elements in `#rosters-container` based on `currentRosterTeams`
- `applyDraftFilter()` — re-renders `renderDraftPicks` and (if board was built) `renderDraftBoard` using `_draftPicks` and `currentDraftTeams`

### Rosters
- `buildRosters(rostersData, playersData)` — renders 12 roster cards with position-colored player chips; calls `buildTeamFilterChips` and `applyRosterFilter` after rendering

### Rivalries
- `buildRivalries()` — renders 6 rivalry cards; re-renders on every tab visit; always shows a "2026: TBD · W4 W13" placeholder row for each rivalry until live matchup data is available. Also calls the three Phase 2 builders below, every visit.
- `buildH2HForYear(year, maxWeek)` — builds H2H map from cached matchup data for a single year (up to `maxWeek`; default 17)
- `findRivalWeeks(year, ridA, ridB, maxWeek)` — returns sorted list of week numbers where two roster IDs faced each other (default `maxWeek=14`)

### Head-to-Head Explorer + Nemesis Board (Phase 2 — built 2026-08-21)
Deliberately a **different question** from the 6 `RIVALS` cards above: "any two managers, ever," not just the 6 pairs the league formally calls rivals. So it does **not** inherit the "2025+ only" scoping those cards use (see KEY DESIGN DECISIONS) — it walks every cached season back to 2023, same guards as `buildH2HMap` (`weekWasPlayed`, `REG_WEEKS`-capped), so it can never disagree with the all-time totals shown elsewhere on the site. Verified against synthetic matchup data covering a win, a loss, a tie, an unplayed week (all-zero points) and a week 15 game — the unplayed week and the post-`REG_WEEKS` week are both correctly excluded, and win/loss/tie/margin/chronological-sort all came back exact.

- `buildAllTimePairs()` — one walk over `tol_matchups_{year}` for 2023–2026, grouping every regular-season matchup by roster-id pair (keyed `lo|hi`, lower roster_id first) into a `games[]` array. Not memoized — recomputed on every `buildRivalries()` call, same as `buildH2HMap`; cheap at this data volume (4 seasons × 14 weeks × 6 games).
- `pairView(pairs, ridX, ridY)` — orients one pair's games to `ridX`'s point of view: `{w, l, tie, gp, pf, pa, avgMargin, games[]}`, sorted chronologically. Returns `null` when the two have never played a regular-season game against each other — a normal state (most of the 66 possible pairs have only 1–2 meetings across 4 seasons, some none at all), not an error condition; callers render a plain sentence for it rather than an empty table.
- `computeNemesisMap(minGames)` — thin wrapper over `buildH2HMap()`: per manager, the opponent with the worst win% among opponents played at least `minGames` times (Nemesis Board uses 2), tie-broken toward more losses. Gating on a minimum sample means one loss to someone played only once can't crown a "nemesis."
- `buildH2HPicker()` — renders the 12×12 clickable grid into `#h2h-picker-grid`. Cell color: `.lead`/`.trail`/(default) via `--accent`/`--accent3`, matching the fav/dog-style axis used elsewhere on the site. Clicking a cell calls `selectH2HPair`.
- `selectH2HPair(ridX, ridY)` / `renderH2HDetail()` — `_h2hSelected` is a module-level var that persists across re-renders (a Rivalries tab revisit doesn't lose the pair you had open). Detail card reuses `.riv-card`/`.riv-at-row`/`.riv-history` wholesale from the existing rivalry cards, plus a `.dtbl` game log table with a `goToScoresWeek` link per game, same pattern as the official rivalry cards' week links.
- `buildNemesisBoard()` — renders `#nemesis-board` as a 12-row `.dtbl`, one row per manager sorted by name, reusing `.hof-sub` for the record text. "Not enough data yet" for anyone with no opponent meeting the 2-game minimum.

### Player Stats
State variables: `currentStatsYear` (default 2026), `currentStatsPos` (default `'all'`), `currentStatsWeek` (default `'season'`), `statsShowPass`, `statsShowRush`, `statsShowRec` (all default `true` — control column group visibility), `currentStatsTeams` (Set — roster_ids; `0` = free agents; empty = all teams).

- `fetchPlayerStats(year)` / `fetchWeekStats(year, week)` — fetches and caches stat data for 2023–2025 (permanent localStorage)
- `fetch2026SeasonStats()` — fetches all 17 weeks of actuals (`/stats/nfl/regular/2026/{week}`), identifies completed weeks by `gp >= 1`, then pulls projections **only for the weeks not yet played** via `getWeekProjections()` (see Projections Data Layer). Aggregates actuals and projections separately; caches in session-only `_stats2026Cache` (cleared on Refresh, not localStorage).
- `fetch2026WeekStats(week)` — actuals first; falls back to `getWeekProjections()` if no `gp >= 1` data.
- `SEASON_STAT_KEYS` / `rosteredPlayerIds()` — shared by both fetchers so the key list can't drift between them. `pass_int_td` is in the list.
- `calcPts(stats, pos)` — fantasy points from a raw stat line using `SDATA`. Works identically on actual and projected lines (they share field names for everything this league scores). **Never** substitute Sleeper's `pts_ppr`/`pts_std`/`pts_half_ppr` as a fallback — those are Sleeper's generic scoring, not this league's, and a `build2026Stats` fallback that did exactly that was removed 2026-08-20. **2026-08-20:** added the missing `pass_int_td` term (pick-six, −1); it was in `SDATA` and in Sleeper's stat lines but not in the function, which overstated QB scores. With that plus the `rec: 0` fix, `calcPts` reproduces Sleeper's own weekly team totals exactly.
- `build2026Stats(c, pos)` — 2026 renderer; season view shows dual "Act. Pts" / "Proj Pts" columns; week view shows actuals or projected with PROJ chip; uses unified column builder (same as `buildPlayerStats`). **2026-08-20:** in the season view the *stat* columns (Gms/Att/Pass Yds/Rush/Rec/…) now render **actual + projected combined** via the row's `disp` object, instead of actuals only — before this the whole preseason season view was a wall of `—` with a single lonely Proj Pts number. `r.stats` is the display object; `r.actualStats`/`r.projStats` keep the two sources separately for the points columns.
- `buildPlayerStats(year, posFilter)` — renders stats table for all years; routes to `build2026Stats` if year is 2026; uses unified column builder (no position-specific if/else)
- `toggleStatGroup(group, el)` — toggles `statsShowPass`/`statsShowRush`/`statsShowRec`, calls `buildPlayerStats`
- `setStatsYear()`, `setStatsWeek()`, `setStatsPos()` — filter handlers
- `buildStatsTeamChips()` — builds "All Teams" + "Free Agents" + per-team chips into `#stats-team-chips`; guarded by `dataset.built` so it only runs once. Free Agents = `rid 0` (players in stats but not on any roster). Called at end of both `build2026Stats` and `buildPlayerStats`.
- `applyStatsFilters()` — shows/hides `tr[data-pid]` rows using `data-rid` attribute; AND-combines team filter (`currentStatsTeams`) with player search/selection filter. Each `<tr>` in the stats table has `data-rid="{roster_id}"` (0 for free agents).

**Unified column builder** (used in both `build2026Stats` and `buildPlayerStats`): Passing columns shown only for QB + All/Rookie views; Rushing for QB/RB/WR + All/Rookie; Receiving for RB/WR/TE + All/Rookie. TE Prem column added when `pos==='TE'` and Receiving is enabled. Non-applicable cells render `—`. NFL Team column only shown on All/Rookie views.

**Rookie tag:** `isRookieInYear(pid, year)` uses Sleeper `years_exp` field (`years_exp === 0` = 2026 rookie, `1` = 2025 rookie, etc.). `[RK]` tag rendered via `.rk-tag` span inside the player chip. A legend note appears below the scoring note when any player in the filtered view has `[RK]`.

### Transactions
- `fetchTransactions(leagueId, year)` — fetches and permanently caches past transactions
- `buildTransactions(filter, year)` — renders filtered list; calls `buildTeamFilterChips` on first run; filters by `currentTxnTeams` (multi-select Set — matches any transaction touching any selected team)
- `runPlayerSearch(query)` — searches all seasons + draft history for a player

### Draft
- `buildDraft2026()` — **deleted 2026-08-20** (was never called). The hidden `draft-view-2026` markup and its `setDraft26View()` toggle still exist and are still wired to each other, so that cluster was left alone — it is inert but not cleanly separable. Remove it as a unit if you ever touch the Draft tab.
- `buildDraftHistory(year)` — fetches and renders past draft results for ALL years (including 2026); calls `buildTeamFilterChips` after rendering
- `renderDraftPicks(container, picks, year)` — filters picks by `currentDraftTeams` before rendering
- `renderDraftBoard(picks, year)` — filters picks by `currentDraftTeams` before rendering (shows only selected teams' columns on board view)

### Tab Navigation
- `showTab(tab, el)` — activates tab + panel; triggers lazy-load on first visit; toggles `body.is-home`; updates URL hash

### Trade Evaluator
- `initTradeEval()` — lazy-init: populates team dropdowns, builds pos/team chips, calls `fetchKTCValues()`, then builds player list and renders table; calls `buildFuturePicksMap()` after
- `fetchKTCValues()` — fetches `https://keeptradecut.com/dynasty-rankings?format=1&tep=1` HTML, parses `var playersArray = [...]` via bracket-counting, extracts `superflexValues.tep.value` per player; tries direct then two CORS proxies; falls back to `KTC_SNAPSHOT` if all fail. 24h localStorage cache under `tol_ktc_v4`. Also populates `_ktcUnresolved` from the file's `unresolved` array (the CORS-proxy fallback leaves it empty on purpose — that path only sees the top-500 array and cannot tell "untracked by KTC" from "below the cut").
- `loadKTCCache()` — checks `tol_ktc_v4` for a valid 24h cache; sets `_ktcValues`, `_ktcSource` and `_ktcUnresolved`
- `getKTCEntry(name)` — exact-name lookup in `_ktcValues` or `KTC_SNAPSHOT`; returns `{value, position, nflTeam, age, rank, trend}` or null
- `getKTCEntryFuzzy(name)` — alias table → exact match → normalized match → suffix-stripped match (Jr./Sr./II/III/IV, either side) → null; used for Sleeper→KTC name mapping. **2026-08-18 fix:** step 3 (suffix-stripped) used to be skipped whenever the *query* name had no suffix, so a Sleeper name like "Kenneth Walker" never matched a KTC key like "Kenneth Walker III" — silently failed for every Jr./III player where only the KTC side carries the suffix. Now always runs step 3.
- `KTC_NAME_ALIASES` — Hand-maintained map of known nickname/display-name mismatches that no punctuation/suffix normalization can bridge — Sleeper stores a preferred/short name, KTC uses the legal name. Checked first, before exact/normalized/suffix matching, inside `getKTCEntryFuzzy`. Grow it from the aggregate report below whenever a real player is found hiding behind a bad match — do not add an entry for a genuine KTC coverage gap. Two entries so far: `'chig okonkwo':'Chigoziem Okonkwo'` (2026-08-19) and `'kenny gainwell':'Kenneth Gainwell'` (2026-08-19 — found while investigating why Gainwell was the only unmatched **starter** league-wide, on Matt's own team; confirmed via `Object.keys(_ktcValues).filter(k=>k.includes('Gainwell'))` → `["Kenneth Gainwell"]`, value 2963. Fixed Matt's team total from 73,423 → 76,386 KTC.)
- `normalizeName(n)` — strips apostrophes (ASCII **and** curly/backtick variants — the ASCII `'` was missing until 2026-08-18, which broke matches like Sleeper's "Tre' Harris" against a KTC key spelled "Tre Harris"), periods; lowercases; collapses spaces; used for fuzzy name matching
- `getDynastyValue(pid)` — resolves a Sleeper player_id → KTC value via name lookup + last-name fallback; returns 0 if not found. Used by the Trade Evaluator, where a 0 for an obscure/no-value player is an acceptable simplification. **Do not reuse this for anything that needs to tell "no data" apart from "genuinely worthless"** — use `resolveRosterPlayerValue(pid)` (Phase 6, below) for that.
- `buildKTCPlayerList()` — builds `_ktcAllPlayers` array: Phase 1 iterates Sleeper rosters (ownership guaranteed, uses `getKTCEntryFuzzy`); Phase 2 appends unrostered KTC entries + future picks (2027+, 2026 excluded). Sorted by rank.
- `buildKTCPosChips()` — builds All/QB/RB/WR/TE/Picks filter pills using `f-pill pos-*` classes; guarded by `dataset.built`
- `buildKTCTeamChips()` — builds All Teams + 12 owners + Free Agents filter pills using `f-pill`; guarded by `dataset.built`
- `setKTCPos(pos, el)` — sets `_ktcFilterPos`, updates active chip, re-renders table
- `toggleKTCTeam(rid, el)` — toggles `rid` in `_ktcFilterTeams` Set; "all" clears the Set
- `renderKTCTable()` — renders `.ktc-tbl` from `_ktcAllPlayers` applying current pos/team/search filters and sort; TOL Owner column uses pink (`var(--accent3)`)
- `ktcSortBy(col)` — toggles sort direction on rank/name/position/age/value columns
- `toggleKTCTable()` — shows/hides `#ktc-table-section`; updates `#ktc-toggle-btn` label
- `getPickMultiplier()` — returns `0.8 + _pickSlider × 0.008` (slider 0 = 80% of KTC; slider +25 = 100%)
- `getAdjustedPickValue(rawVal)` — applies pick multiplier to a raw KTC pick value
- `getKTCPickValue(year, round, slot)` — maps slot→tier (Early/Mid/Late), looks up "2027 Mid 1st" style name in KTC data
- `getPickValue(year, round, slot)` — `getAdjustedPickValue(getKTCPickValue(...))`
- `updatePickScaler(val)` — updates `_pickSlider`, refreshes trade panels and table
- `loadTradeTeam(side)` — renders player+pick checkbox list for a team; 2027/2028 picks only (2026 draft complete)
- `getTradeAssets(side)` — collects checked players/picks from a side
- `evaluateTrade()` — sums values, computes delta/pct, renders verdict card (Even/Slight/Clear/Strong Win/Loss)

### Roster Grades & Outlook (Phase 6 — built 2026-08-18, shipped league-facing 2026-08-20)
Lives inside the Rosters panel as a sub-tab (`setRosterView`), not a new top-level tab — see Rosters Panel IDs above. **The league-facing view is a ranked row list with per-team write-ups plus a rubric explainer (`.gr-*` CSS block); the raw per-team metrics live behind `?admin=1`.** See DEVELOPMENT ROADMAP Phase 6 for spec, decisions made, and what's still open.

- `setRosterView(view, el)` — toggles the three Teams views; sets the per-view title from `ROSTER_VIEW_META`, and **returns the build promise** so a caller like `showPlayerStats()` can await a populated view instead of guessing at a timeout
- `AGE_CURVES` — per-position prime/decline-start/cliff ages (QB/RB/WR/TE only), confirmed by Matt 2026-08-18
- `ageTimelineScore(pos, age)` — 0–1 "runway" score from a player's age vs. their position's curve; returns `null` for positions with no curve (K/DEF/RDP) — callers must skip nulls, not treat them as 0
- `resolveRosterPlayerValue(pid)` — like `getDynastyValue()` but returns `{value, matched, reason, position, age, name}` and **never** collapses a no-match to 0. This is the function to use anywhere Phase 6-style "don't silently zero a real player" behavior is needed. **2026-08-20:** gained a third outcome. A name in `_ktcUnresolved` (written by the scraper as `unresolved`, meaning it checked KTC's whole pool and the player genuinely isn't in it) now returns `{value: 0, matched: true, reason: 'ktc-untracked'}` instead of `matched: false`. That is the fix that closed the reconciliation gap: an unmatched starter/bench player is *excluded from his team's roster entirely*, so before this a manager could hide a washed veteran from the Bench Dead Weight count simply by rostering someone KTC had stopped tracking. Untracked veterans now count as the zero-value roster spot they are, and `flagged` is reserved for genuine unknowns.
- `ROSTER_GRADE_FLOOR_SLOTS` / `ROSTER_GRADE_FLOOR_VALUE` — taxi/IR are the only slots allowed a nominal floor value (200) on no-match; starters/bench always get flagged instead, never floored
- `NEAR_ZERO_KTC_THRESHOLD` (500) — **2026-08-19 addition.** Confirmed-matched players at or below this KTC value are excluded entirely from the timeline score (not just down-weighted), so a roster full of scrubs can't quietly skew the average. Distinct from `flagged`: these players DO have a real KTC match, it's just negligible. As of 2026-08-19, this excludes **0 players across all 12 real rosters** — the KTC pool this league draws from doesn't currently have confirmed matches that low, so the exclusion is correct but not yet binding; keep it, it protects against future roster churn (e.g. a team hoarding waiver-wire scrubs).
- `SPECULATIVE_VALUE_THRESHOLD` (2000) — **2026-08-19 addition.** Higher than `NEAR_ZERO_KTC_THRESHOLD` on purpose — this catches "real bench stash, unproven," not only "basically zero." Used only for `speculativeCount`/`speculativePlayers`, never the timeline score.
- `isUnproven(pid)` — `years_exp <= 1` (rookie or 2nd-year). Still computed (`unprovenValue`/`unprovenPct` on `computeTeamRosterData`, informational only) and still used by `getTopAssets()`'s `unprovenNoPayoff` flag — but **no longer drives the team-wide risk flag or grade cap** (see `isDeadWeight` below, same-day replacement).
- `isDeadWeight(pid, value)` — **2026-08-19, replaces the flat "% unproven" trigger.** Matt found the old `unprovenPct>=25%` trigger flagged 10 of 12 teams and correctly diagnosed why: any healthy dynasty roster carries real value in recent rookie-draft picks, so a flat percentage mostly measures normal roster construction, not risk. This flips the question to the *other* end of the roster: a veteran (`years_exp>=2`) with a confirmed-but-low KTC value (`<=SPECULATIVE_VALUE_THRESHOLD`, reusing that same 2000 bar — deliberately the same "real value, but modest" line applied to old players instead of young ones) is a genuinely wasted bench spot, not upside. Tested against real data: a flat ≤500 threshold found **zero** veterans league-wide (KTC's ranked pool is already pre-curated to ~500 "relevant" players, so a truly worthless veteran isn't in the pool at all — not a low score in it); the 2000 bar produces a real, discriminating 2–9 count per team. Collected per-team as `deadWeightPlayers`/`deadWeightCount` on `computeTeamRosterData`.
- `READINESS_INACTIVE_STATUSES` / `READINESS_OUT_INJURY_STATUSES` / `isStarterSlotShaky(pid)` — **Repurposed 2026-08-19.** No longer drives team-wide Current-Year Readiness (see below) — Matt correctly flagged that "who's in the manager's `starters` array" conflates a genuinely unproductive lineup with a manager who just hasn't touched their lineup since the draft (i LOVE mendoza had 5 of 11 slots sitting empty, not because those players were bad, but because the slots were never filled). Now used only by `getTopAssets()`'s `unprovenNoPayoff` flag, checking a *specific asset's* current role.
- **Current-Year Readiness (2026-08-19 full rebuild)** — replaced the shaky-starter-slot approach entirely with a projected-points optimal-lineup ranking, per Matt's direction: "factor in projected points... by hypothetically starting their best 11 players... to see where the team would place." Pieces:
  - `getSeasonPointsByPid()` — season-long projected points per rostered player, scored through this league's own rules (`calcPts`/`SDATA`), blending confirmed actual production with rest-of-season projections via `fetch2026SeasonStats()`. Cached in `_seasonPointsByPid`.
  - `getLeagueRosterPositions()` — lazy-fetches `roster_positions` from `/league/{LID}` if `cachedLeague` isn't already set (the 6h roster cache doesn't include it). Confirmed live: `["QB","RB","RB","WR","WR","TE","FLEX","WRRB_FLEX","WRRB_FLEX","WRRB_FLEX","SUPER_FLEX","BN"×14]` — 11 starting slots, no K/DEF.
  - `LINEUP_SLOT_ELIGIBILITY` — flex-slot position eligibility map (`FLEX`→RB/WR/TE, `WRRB_FLEX`→RB/WR only, `SUPER_FLEX`→QB/RB/WR/TE).
  - `computeOptimalLineup(roster, pointsByPid, rosterPositions)` — greedy solve: fills slots most-restrictive-first (ascending eligible-position count) so a scarce single-position starter never loses their spot to a flex slot filled out of order. Excludes taxi/IR. Returns `{total, assignments, slotsTotal, slotsFilled}` — `slotsFilled<slotsTotal` means a slot has literally no eligible rostered player at all (a real gap, distinct from the old "manager didn't set a lineup" false positive).
  - `computeReadinessRankings(allTeamsData)` — computes every team's optimal lineup, ranks 1–12 by total projected points, tiers by thirds (top4 Strong / mid4 Average / bottom4 Weak, same convention as the Value axis). Must run after `computeTeamRosterData()` for all 12 teams (needs every team's total to rank) and before `gradeRoster()`. Called from `buildRosterGrades()`.
  - Verified against real data: i LOVE mendoza (the team with 5 empty manager-set slots) now correctly resolves to a full 11/11 optimal lineup, Average readiness, rank #8 of 12 — the false "half my lineup is empty" reading is gone, replaced by an honest "this roster doesn't project as well for 2026 as its dynasty value suggests" reading.
- `computeTeamRosterData(uid, picksMap)` — per-team totals. `picksMap` (from `buildFuturePicksMap()`, fetched once in `buildRosterGrades()`) is optional; when passed, future draft-pick value is folded into `total` **before** `unprovenPct` is computed, so that percentage's denominator stays consistent with the final displayed total. Returns: `total` (KTC sum: confirmed players + `pickValue`, excludes unmatched starter/bench players), `pickValue`/`picks` (2026-08-19 addition — see below), `flagged` (unmatched starter/bench players needing manual check), `byPos` (starter/bench value+count per QB/RB/WR/TE — picks are NOT positional, so they never enter this), `timelineScore` (KTC-value-weighted `ageTimelineScore`, confirmed-matched players above `NEAR_ZERO_KTC_THRESHOLD` only, across the whole roster — **not starters-only; still flagged as an assumption for Matt to revisit**), `nearZeroExcludedCount` (audit counter), `speculativeCount`/`speculativePlayers`, `deadWeightCount`/`deadWeightPlayers` (2026-08-19), `unprovenValue`/`unprovenPct` (informational only now). **`readiness` is NOT set here** — it's attached in a later pass by `computeReadinessRankings()` since it needs all 12 teams' totals to rank. **`deadWeightRank`/`highDeadWeightRisk` are NOT set here either** — attached by `classifyRosters()`, same reason.
- **Draft pick value (2026-08-19 addition).** `total` previously counted rostered players only — Matt caught this ("are you factoring in draft picks as total value?? because those have value too"). Now folds in future picks via the existing `buildFuturePicksMap()` (fetched once in `buildRosterGrades()`, already accounts for trades) and `getKTCPickValue(year, round, null)` — the `null` slot defaults to "Mid" tier, same simplification the Trade Evaluator itself uses when draft slot isn't knowable this far out. **Uses the raw KTC pick value, NOT `getPickValue()`'s slider-adjusted value** — that slider is a Trade Evaluator negotiation control (`_pickSlider`), not a true asset value, and would make roster grades depend on whatever position the Trade Evaluator's UI slider happened to be left in. Verified against real data: pick value is material, roughly 15–25% of total for most teams (range ~16,000–31,600 across the 12 teams, 6–10 picks each) — this was a real gap, not a rounding difference, and shifted Value Rank for several teams once added.
- `computeDepthFlags(allTeamsData)` — flags a team+position as "thin" when bench value at that position is under 40% of the league median bench value there, but only if the team actually starts that position
- `classifyRosters(allTeamsData)` — value axis = thirds by total KTC rank (top4/mid4/bottom4, now includes pick value — see above); timeline axis = median split of `timelineScore` (young/old). The 4 named quadrants (Stacked Contender / Win-Now-Aging Window / Genuine Rebuild / Bad & No Future Currency) come from crossing top/bottom value × young/old. **The middle value third isn't one of the 4 named quadrants** — it currently gets "Building" (young) or "Treading Water" (old), an assumption not in the original spec; confirm with Matt. **2026-08-19**: also ranks all 12 by `deadWeightCount` (worst third = `highDeadWeightRisk`, same thirds convention as Value) and sets `teamData.quadrantLabel` = `quadrant` + `' — High Bench Dead Weight'` when applicable — **use `quadrantLabel` for display, `quadrant` for logic/string-matching** (e.g. inside `gradeRoster`) so the two never get confused.
- `gradeRoster(teamData)` — Base score from value rank + quadrant + depth flags + unresolved-match count, plus ±0.4/-0.8 for Strong/Weak readiness. Then a hard CAP (not a modifier, applied last): `highDeadWeightRisk && readiness.tier!=='Strong'` clamps the score to 3.4, just under the A- cutoff — so that combination can reach at most a B+, regardless of raw dynasty value rank. Elite value + Strong readiness + a clean bench is still fully eligible for an A. **2026-08-19**: cap trigger switched from the old `highUnprovenRisk` (flat %, over-triggering) to `highDeadWeightRisk` (Bench Dead Weight rank, see `isDeadWeight` above). **2026-08-20**: returns `capBound` — whether the cap actually LOWERED the score, not merely whether its condition held. Joshin Around met the condition (11 dead-weight spots, Average readiness) but scored 0.9, nowhere near the 3.4 ceiling, and still read "grade capped," crediting the cap for a D it had nothing to do with. Same class of bug as the 2026-08-19 rationale fix, one step further in. Rationale text only; grades unaffected. No AI/free text; thresholds are a v1 guess, tune once seen against real data across a season.
- `buildGradeRationale(teamData)` — template sentence assembled from the same computed values as the grade (no AI). Includes the readiness tier/rank and pick-value breakdown. **The "grade capped" text must exactly mirror `gradeRoster()`'s cap condition** (`highDeadWeightRisk && readiness.tier!=='Strong'`), not just `highDeadWeightRisk` alone — a 2026-08-19 verification pass caught exactly this bug: a team with `highDeadWeightRisk=true` but Strong readiness (which exempts the cap) was showing "— grade capped" in its rationale despite grading a clean A. Fixed to branch on the full condition; the non-capped case now reads "...heaviest in the league, but Strong readiness exempts the cap" instead.
- `getTopAssets(uid, n)` — top-N matched players by KTC value for a roster; each asset carries `unprovenNoPayoff` = `isUnproven(pid) && isStarterSlotShaky(pid)` — a rookie/2nd-year asset with no confirmed 2026 role, propping up the team's headline value without a current-year payoff. Rendered as a ⚠ on the card's asset chip.
- `buildUnmatchedReport(allTeamsData)` / `buildUnmatchedReportHtml(rows)` — Aggregate, cross-team rollup of every starter/bench player still unmatched after alias + fuzzy matching (the same per-card flags, consolidated). `buildRosterGrades()` both `console.table`s this and renders it as a table at the top of the Grades & Outlook view, above the team cards. This is the intended ongoing discovery process for growing `KTC_NAME_ALIASES`. **2026-08-20 — the 2026-08-19 conclusion below was WRONG and is corrected:** it recorded 7 players (Zach Ertz, Kareem Hunt, Joe Mixon, Brady Cook, Chris Oladokun, Tyler Lockett, Austin Ekeler) as "genuine KTC coverage gaps." Five of them were not gaps at all. The check was run against `_ktcValues`, which holds **exactly 500 players** — that is a hard cap on what KTC's `dynasty-rankings` page embeds, not the size of KTC's pool. Ertz was rank 475 on the TEP scale, Mixon 552, Hunt 562, Lockett 569, Ekeler 761; all five have live KTC player pages and real values. `scripts/fetch_ktc.py` now does a second deep-lookup pass for them (see Automation below). **The lesson: "not in `_ktcValues`" never meant "not on KTC."** Only Brady Cook and Chris Oladokun (plus taxi rookies Carson Steele, Kurtis Rourke, Matt Hibner, Will Kacmarek) are genuinely untracked — confirmed by absence from `sitemap-dynasty.xml`, which is the slug source and does list all five of the recovered veterans. As of 2026-08-20 the aggregate report is **empty: 0 unmatched starter/bench players league-wide.**
- **Grading periods (2026-08-20).** `GRADE_PERIODS` is the list of committed grading runs (`{id, label, season}`, newest first); each maps to a `roster-grades-<id>.json` at the repo root. `GRADE_LIVE_PERIOD` is a live-recompute pseudo-period shown to admins, or to everyone when nothing has been committed yet so the view is never empty. `gradeTabs()` builds the tab bar (hidden when there's only one), `setGradePeriod(id, el)` switches, `_gradePeriodId`/`_gradeState` hold selection + computed data. Adding a period is data-only: commit the JSON, add a row to `GRADE_PERIODS`, add write-ups to `GRADE_WRITEUPS`. **The point is the diff** — a Genuine Rebuild that becomes a Stacked Contender by December is only visible if December didn't overwrite August.
- `GRADE_WRITEUPS[periodId][uid]` — hand-written HTML write-up per team per period. Deliberately **not** generated: the mechanical `buildGradeRationale()` string still drives the grade and is still shown as the fallback on the Live tab, but a template can say "9 washed veteran bench spots" and cannot notice they're all the same guy's retired running backs. Written against that period's frozen numbers, so they never drift out of sync with the grade.
  **No raw figures in the prose (2026-08-20, Matt's call).** No KTC/KeepTradeCut values, no projected-point totals — league members have no scale to read "9,997" or "2,750 pts" against, so the numbers read as noise and invite arguments about the units instead of the roster. Write-ups talk in players, ranks and counts ("top-three asset", "eleven dead-weight bench spots", "seven quarterbacks"); the scales themselves are defined once, in words, in the "About the numbers behind all this" section of `buildGradeMethodologyHtml()`, and the actual per-team figures live in the admin view. Keep new write-ups to that rule.

  **No team names in the prose either (2026-08-21, Matt's call).** Two write-ups leaned on them and
  both broke within a day of the 2026 names being refreshed: one called an opponent "Titsburg", and
  Matt's punchline was built on his team being named "Show Me Your Penix" while the row directly
  above it already read "Tee Baggin Swift's Tate". Managers rename freely — especially in the
  preseason, before names are settled — and a frozen write-up cannot follow them. Refer to the
  **manager**, and hinge jokes on roster facts, which don't go stale. Both were rewritten rather
  than re-pointed at the new names, since the new names are no more permanent than the old ones.
  The `//` comment label above each write-up is now `Manager — Grade` for the same reason.
- `isGradesAdmin()` — `?admin=1` on the query string (NOT the hash — the hash is the tab router, so a `#admin` flag gets eaten by `routeFromHash`/clobbered by `showTab`). Gates the internal working views: raw per-team metric cards (`renderGradeAdminCard`, the old league-facing card), the unmatched-player report, and the snapshot exporter — all bundled by `buildGradeAdminHtml()`.
- `renderRosterGrades()` / `buildGradeRowHtml()` / `toggleGradeRow(uid)` — the league-facing view: period tabs, a date stamp, then twelve rows ordered by GRADE (via `GRADE_ORDER`, since a frozen period only stores the letter), each expanding to tags + core-asset chips + the write-up. `buildGradeMethodologyHtml()` renders the full rubric explainer below the list.
- `gradeView(period, teamData, snapshot)` — normalizes "what this period says about this team" from either the frozen file or live data. A frozen period reads **entirely** from its own file, including top assets and readiness, so an old tab can't quietly re-render itself with today's roster.
- `loadRosterGradeSnapshot(periodId)` — fetches `roster-grades-{periodId}.json` from the repo root (same no-CORS pattern as `ktc-values.json`); returns `null` if absent
- `buildSnapshotPayload(allTeamsData, year)` / `buildSnapshotExportHtml(...)` — builds the frozen-snapshot JSON and a copyable `<textarea>` in the UI. Payload freezes `readinessTier`/`deadWeightCount`/`highDeadWeightRisk`/`pickValue` alongside the grade, since they're now grade inputs — this is what the grade was based on at snapshot time; the live card always shows current (unfrozen) readiness/depth/assets regardless. **There is no automated write path** — this is a static GitHub Pages site with no server. Taking a snapshot is a manual step: open Grades & Outlook with `?admin=1`, switch to the Live tab, copy the textarea JSON, commit it as `roster-grades-<period-id>.json` at the repo root, then add the period to `GRADE_PERIODS` — same manual-commit pattern already used for `KTC_SNAPSHOT`. The payload also freezes `topAssets`, `readinessRank` and `readinessPts` (2026-08-20) so a past period renders entirely from its own file.
- `buildRosterGrades()` — main build; lazy-fetches KTC values + `buildFuturePicksMap()` if not already loaded, computes all 12 teams, loads every committed period file, stashes it in `_gradeState`, then calls `renderRosterGrades()`. (`renderGradeCard` was renamed `renderGradeAdminCard` on 2026-08-20 — it is no longer the league-facing renderer.)

### Manager Profiles (Phase 11 — built 2026-08-21)
Twelve cards on a new first Careers sub-tab, each opening a full career profile. **Every manager
name anywhere on the site is a link into it** — 936 of them as of build day.

- **`ownerAwardDefs(at,ledger)` is the single definition of every ranked award**, consumed by BOTH
  `buildHallOfFame()` and `buildOwnerProfile()`. The Hall of Fame was refactored onto it rather
  than leaving two lists to drift; verified byte-identical afterwards (all 19 cards and all 12
  record-book cards unchanged). **Add a new award here, never in `buildHallOfFame`.**
- `ownerRank(map,uid,dir,gate)` — where one manager sits in an award's field. Ties SHARE a rank,
  matching the convention `leaderBody` already uses when it prints two names on one card.
- `buildOwnerProfile(uid)` — pure data, no DOM, so it can be checked from the console. Returns
  identity, all-time record, per-owner record book, award standings, season-by-season and team
  names. Every figure comes from `buildAllTimeStats()`, so a profile **cannot** disagree with the
  Careers table, the record book or the standings. Verified: all 12 profiles reconcile against the
  rendered careers table for both record and earnings.
- `ownerLink(uid,text)` / `ridLink(rid,text)` — **the only sanctioned way to render a manager's
  name.** A `<button>` with its styling stripped back to `inherit`, so it drops into a table cell,
  a card header or a sentence without moving anything. **No underline** (Matt, 2026-08-21) — names
  inherit their surrounding color and reveal themselves on hover; `:focus-visible` still draws a
  ring so keyboard users keep an affordance. `ridLink` exists because most render sites carry a
  roster_id, not a uid. An unknown uid falls through to plain escaped text, which is what
  makes the Stats table's free-agent rows (rid 0) safe.
- `openProfile(uid,ev)` / `closeProfile(ev)` — **an overlay, deliberately not a route.** Clicking a
  name in a Week 8 matchup must not cost you your place on the Scores tab. Verified: tab stays
  active, scroll position holds, `location.hash` unchanged. Closes on the backdrop, the ✕, or Esc,
  and returns focus to the link that opened it. `openProfile` calls `stopPropagation`, which is why
  a link inside an already-clickable row (Stats, H2H grid) doesn't trigger the row's own handler.
- `ownerTeamNames(uid)` — collapses `TEAM_NAME_HISTORY` into display rows. **Merges on name AND
  holder**, not name alone: Andrew inherited "Joshin Around" from Chris Jacobs for the 2026
  preseason, and merging on name alone filed a year of Andrew's tenure under Chris's label.
- Per-owner record fields were added to `blankOwnerStats()` / `buildAllTimeStats()`: `hiWk`, `loWk`,
  `bestWin`, `worstLoss`, `closest`, `seasonHi`, `seasonLo`. Purely additive — the league-wide
  `rec` object and every existing consumer are untouched. Cross-checked: Matt Bova's personal
  closest finish (+0.65 over Chris Merkel) is the same game the league-wide card shows.
- CSS lives in the appended `MANAGER PROFILES` layer (`.pf-*` / `.own-link`), per the redesign
  convention, with its light-mode overrides. Verified 280/375/1280px in both themes: zero page
  overflow, the season table scrolls inside its own `.pf-tblwrap`.

### Boot
- `startCountdown()` — countdown timer to **Sep 9, 2026 8:20 PM ET**; ticks every 1s
- `routeFromHash()` — reads `location.hash` on boot and navigates to matching tab
- `init()` — boot sequence: loads/caches rosters, builds leader stats, prefetches historical data in background

### Automation (Tuesday Bot)
Weekly automation that runs every Tuesday at 9am ET (after Monday Night Football). It now does
**two** jobs: update `h2h-records.md` with the prior week's H2H results, and extend
`stats-history.json` with the live season's played weeks (Phase 12).

- **`scripts/tuesday_update.py`** — fetches `state/nfl` to detect current week, fetches matchups from Sleeper API, parses and rewrites `h2h-records.md`. Flags: `--week N`, `--dry-run`, `--force`. Tracks applied weeks in `scripts/bot_state.json`.
- **The Phase 12 data chain** — three steps, added 2026-09-03/04, all running **after** the H2H
  commit and each `continue-on-error`, so a data failure can never cost an H2H update that
  already succeeded. **The order is load-bearing and each step is gated on the previous one:**

  1. `generate_stats.py --live-only` → `stats-history.json`
  2. `scripts/build_replacement_levels.py --live-only` → `replacement-levels.json`
  3. `scripts/build_trade_roi.py` → `trade-roi.json`

  Each reads the one before it. Getting the order wrong is **not** a loud failure:
  `build_trade_roi.py` skips any week it has no replacement baseline for (`base is None ->
  continue`), so running it against stale baselines publishes a file in which the whole live
  season silently scored zero — every 2026 trade frozen at 0-0 all year while the page reports
  them as scored, with nothing anywhere to trace it back to. `coverage_gaps()` is the backstop:
  it refuses to build when `stats-history.json` holds a played week that `replacement-levels.json`
  cannot score. Verified by simulating a 2026 Week 1 stats update against stale baselines.

  All three skip the write entirely when the only thing that would change is the `generated`
  date (`unchanged_but_for_stamp()`), so the offseason does not produce a weekly commit whose
  entire content is a one-character date bump on a 1.3 MB file. **That helper must round-trip
  the payload through JSON before comparing** — an in-memory dict keyed by int
  (`pick_curve.by_pick`) sorts numerically while the same data read back from disk sorts
  lexicographically (`"1","10","11",..,"2"`), so without the round-trip the compare reports a
  change on every run and the skip never fires. That bug was live for one build.

  A final `always()` step prints each link's outcome and raises a `::warning::` if any failed,
  so a broken chain is visible rather than hidden behind a green tick.
- **`.github/workflows/tuesday-update.yml`** — GitHub Actions cron (Tuesday 1pm UTC); also has manual trigger with week/dry-run/force inputs. Commits `h2h-records.md` + `bot_state.json`, then the three Phase 12 data files together, each only if changed.

**This workflow had never run once before 2026-09-03 — the file was not valid YAML.** The commit
message's `WEEK=$(python -c "` was a *multi-line* command whose body sat at column 0 inside a
`run: |` block. A block scalar ends at the first line indented less than the block, so YAML parsed
`import json, os` as a top-level key and rejected the whole file. Nothing failed loudly; the
workflow simply never appeared as runnable, and the only "H2H records update" string in the git
log is the commit that created the bot. It went unnoticed because the H2H script is a no-op out of
season anyway. Confirmed by parsing the committed file: invalid, while the KTC and projections
workflows parse fine and have many `chore(bot)` commits.

Two rules that follow from it:
1. **Never paste a multi-line script body into a `run: |` block.** The `WEEK=` extraction is now a
   single line. Anything longer belongs in a `.py` file called by the step.
2. **Parse every workflow file after editing it** — `python -c "import yaml,sys; yaml.safe_load(open(f))"`
   over `.github/workflows/*.yml`. All five parse as of 2026-09-03.

The same step also read `scripts/bot_state.json`, a path that does not exist from the repo root
(it is `Sleeper FF/The Other League/scripts/bot_state.json`), so every commit message would have
said "Week ?" even once the file parsed. Fixed at the same time.

**Every bot script forces UTF-8 on stdout, and must keep doing so (added 2026-09-04).**
A dress rehearsal of the whole chain on Windows ahead of the Sep 15 live run died immediately:
`UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`. The scripts print arrows,
em dashes and check marks; a Windows console — and any redirected output, which is exactly what
the Task Scheduler launcher does — defaults to cp1252 and cannot encode them. GitHub Actions runs
on Ubuntu under UTF-8 and was never affected, which is why this sat unnoticed through the whole of
Phase 12: the only path anyone had actually exercised was the one immune to it.

It would have taken the Windows scheduled task down on its very first live firing, silently,
into a log file nobody reads. All six scripts (`generate_stats.py`, `tuesday_update.py`,
`build_replacement_levels.py`, `build_trade_roi.py`, `fetch_ktc.py`, `fetch_projections.py`) now
carry a `sys.stdout.reconfigure(encoding='utf-8')` guard above their first `print()`, and
`run_tuesday_update.bat` sets `PYTHONIOENCODING=utf-8` as a second layer. **A new bot script needs
the same guard** — write one without it and it works in CI and only ever fails on the user's PC.

**The Windows scheduled task runs the H2H step ONLY — not the Phase 12 chain — and does not push.**
`run_tuesday_update.bat` calls `tuesday_update.py` and stops there. GitHub Actions is the real bot
and the only thing that rebuilds and commits the three data files. The local task is a leftover
belt-and-suspenders path whose one effect is to leave `h2h-records.md` modified in the working copy,
which will then conflict with whatever the Actions run pushed for the same week. If it fires at all
after Sep 9, expect that dirty file and discard it rather than committing it.

- **`scripts/run_tuesday_update.bat`** — Windows launcher called by Task Scheduler; logs to `scripts/tuesday_update.log`.
- **`scripts/setup_scheduled_task.ps1`** — one-time setup to register the Windows Task Scheduler task. Task is **dormant until Sep 9, 2026** (`StartBoundary`); fires on next boot if PC was off at 9am.
- **`.github/workflows/season-reminder.yml`** — GitHub Actions creates a GitHub Issue on Sep 2, 2026 as a reminder to activate the bot; GitHub emails the repo owner automatically.

### Automation (KTC Bot — deep lookup added 2026-08-20)
`scripts/fetch_ktc.py` runs in two passes:
1. **Top-500.** `keeptradecut.com/dynasty-rankings` embeds `var playersArray`, and it is **capped at exactly 500 players**. Verified: `?page=0/1/2` all return the same 500 (pagination is client-side), and the trade-calculator page's `playersArray`/`superflexPlayers` are capped the same way. There is no public JSON API — the page contains no fetch/ajax/`url:` reference at all.
2. **Deep lookup.** Fetches the league's own Sleeper rosters, finds any rostered non-K/DEF player with no match after alias/normalize/suffix (mirroring `getKTCEntryFuzzy` in Python), resolves a slug from `sitemap-dynasty.xml`, and reads `var player = {...}` off that player's own page for a real `superflexValues.tep` value. Entries are marked `"deep": true`. Anything with no slug is written to the file's `unresolved` array — which is what `_ktcUnresolved` and `resolveRosterPlayerValue` consume.

Two guardrails: `MAX_DEEP_LOOKUPS` (40) aborts rather than mass-requesting KTC if an upstream name-format change makes everyone look unmatched, and the whole deep pass is wrapped so a Sleeper hiccup or KTC layout change downgrades to "top-500 only" instead of losing the values already in hand.

**Slug matching needs a different normalizer than name matching.** `squash()` strips everything non-alphanumeric, because slugs flatten punctuation differently: De'Von Achane is `de-von-achane-1398`, which normalizes to "de von achane" while his name normalizes to "devon achane". Only squashing both to `devonachane` lines them up.

`ALIASES` in the script mirrors `KTC_NAME_ALIASES` in `index.html` — **keep the two in sync.**

### Automation (Projections Bot — added 2026-08-20)
- **`scripts/fetch_projections.py`** — pulls all 17 weeks of `/projections/nfl/regular/{year}/{week}`, keeps only QB/RB/WR/TE with a real projection and only the ~30 keys this league scores, writes `projections-<year>.json`. Flags: `--year N`, `--dry-run`. Aborts rather than overwriting a good file if a pull comes back gutted (<200 players in week 1).
- **`.github/workflows/update-projections.yml`** — daily cron at 11:00 UTC (7 AM ET); commits the file only when it changed.
- **Deploy chaining (important):** commits pushed by a job using the default `GITHUB_TOKEN` do **not** fire `push`-triggered workflows — GitHub blocks that to stop workflows recursing. So the projections and KTC bots would commit their data files and the live Pages site would never pick them up. `deploy-pages.yml` therefore also triggers on `workflow_run` for all three bot workflows (guarded by a `conclusion == 'success'` check). Don't remove that trigger thinking the `push` one already covers it — this was a latent gap for the KTC bot too.
  **"Tuesday Weekly H2H Update" joined that list 2026-09-03.** It was legitimately absent before:
  its only output was `h2h-records.md`, which the site never fetches (0 references in
  `index.html`). Now that the same workflow commits `stats-history.json`, which *is* fetched at
  runtime, it has to be chained or the bot would update the file every Tuesday and the live site
  would never serve it. **Any bot that starts writing a file the site fetches must be added here.**
- **`update-ktc.yml` runs on cron + dispatch, plus a narrow push trigger on `scripts/fetch_ktc.py` only (fixed 2026-08-20).** It previously used `paths-ignore`, which only skips a push whose files are *all* ignored — so every ordinary code push fired a full KTC scrape. The git log showed it plainly: four consecutive code pushes, four immediate `chore(bot)` commits, each of which also redeployed Pages through the `workflow_run` chain. `update-projections.yml` never had a push trigger and was always correct; this brings KTC in line.

---

## DATA OBJECTS

### `TEAMS` — static team registry
```javascript
// user_id → { name, team, you, tier, note?, co? }
```
`you: true` marks Matt Bova's team. `co` is for co-owned teams.

### `TEAM_NAME_HISTORY` — every team name each franchise has carried
Pulled from `/league/{lid}/users` across all four seasons and hardcoded (the site does not fetch
that endpoint at runtime). Two rules that are easy to get wrong:
1. **Keyed by the SITE's uid — the franchise, not the human.** Roster 11's 2023–25 names are Chris
   Jacobs'; they sit under Andrew Bova's uid so the franchise reads continuously, and a `who` field
   marks whose they actually were.
2. **A year can hold MORE than one entry.** Sleeper only ever reports the name as it stands *now*,
   so a rename is only detectable by diffing against what we last recorded. The doubled 2026 rows
   are exactly that: what the site had hardcoded through the August preseason, then what Sleeper
   returned on 2026-08-21.

**`TEAMS` team names were refreshed to live 2026 values on 2026-08-21** — five were stale (Matt,
Bogardus, Chris Merkel, Nick Merkel, Andrew). Known cosmetic side effect: the frozen 2026-Preseason
`GRADE_WRITEUPS` still name the old teams ("Show Me Your Penix", "Joshin Around"), including a joke
that depends on Matt's old team name. That prose is period-correct and was left alone; the snapshot
JSON stores no team name, so a frozen grade row renders today's name beside period prose.

### `RM` / `RMR` — roster → owner mapping
```javascript
const RM = { 1: '721908735856967680', ... };  // roster_id → user_id
const RMR = {};  // user_id → roster_id (computed at boot)
```

### `RIVALS` — 6 rivalry pairs (started 2025)
### `SEASON_HISTORY` — past season results (2023–2025)
Final placements plus **per-owner payout totals**. The totals are what the career-earnings column and the Highest Career Earnings award sum, so they must always agree with the itemized lines in `SEASON_PAYOUTS`.
### `SEASON_PAYOUTS` — itemized payout card per season (2023–2026)
Moved out of the League/Rules panel markup on 2026-08-21 and rendered on the Careers year tabs by `payoutCardHtml(year)`. Shape: `{status, note?, rows: [{k, v, tone?}], footnote?}`; `tone` is `'win'` / `'second'` / `'tbd'`, anything else takes the default teal. **Ported verbatim** — these lines are the commissioner's own record, not derived.

**The two objects must reconcile, and now they are shown on the same screen, so a disagreement is visible.** Adding a season means adding it to both. Current state:
- 2023 — itemized lines sum to the $600 pot exactly. ✅
- 2024 — sum to $1,200 exactly, **after a fix on 2026-08-21**: the card credited Duane Gillenwater $15 for Best QB (Lamar Jackson) and `SEASON_HISTORY` had no line for him at all, so his career earnings ran $15 light and the card summed to $1,185. Line added.
- 2025 — sum to $1,200 exactly, **after a fix in a parallel session (128dd39)**: the itemized lines accounted for only $1,175, and the missing $25 turned out to be money held back from the pot for the championship trophy rather than paid out as cash. It is now folded into Jake Blackwell's 1st-place line ($455 → $480, per-owner total $490 → $515). That commit also fixed a transposed figure in the Most Improved Points label (1,196 → 1,961).

- 2026 — **structure set 2026-08-21, before a snap was played** (Matt). Replaces the old
  "Pending / TBD" placeholder. Every line is final; only the names are open, so there is no
  `SEASON_HISTORY[2026]` to reconcile against yet — add one when the season closes out. The
  itemized lines sum to the $1,200 pot exactly: 465 + 200 + 100 + 170 + 30 + 25 + 25 + 25 + 25 +
  25 + 15 + 60 + 35. **If a future edit breaks that sum, the edit is wrong, not the pot.**
  Two lines carry rules that are not obvious from the label: High Points is `$10 × 17 weeks`
  (all 17 on purpose — a manager knocked out of the playoffs still has $10 a week to submit a
  lineup for), and the $35 Survivor Pool is the one payout the site computes rather than records
  (see Survivor Pool + Weekly League Recap above).

**All four seasons now reconcile to their pot exactly**, and the career-earnings column sums to $3,000 across 2023–2025. There is a `reconcile_payouts.py` shape worth rebuilding if a fourth season ever fails to add up: total each card's lines per owner and diff against `SEASON_HISTORY.payouts`, then against the pot.
### `SDATA` / `SLABELS` — scoring values and display names
### `DRAFT_ORDER_2026` — 2026 round 1 order (13 picks — includes consolation bonus pick 1.13)
### `KTC_SNAPSHOT` — hardcoded dynasty player values (Superflex + PPR + TE Premium, June 2026). ~80 players + all 2027/2028 pick tiers (Early/Mid/Late × 4 rounds). Used as fallback when live KTC fetch fails. Pick values represent the +25% slider position (full KTC). Format: `name → value (number)` for snapshot; `name → {value, position, nflTeam, age, rank, trend}` for live cached data.
### `RIVALRY_WEEKS` — rivalry week numbers per year: `{ 2025: [4, 13], 2026: [4, 13] }`. Controls pink pill styling on Scores tab and rivalry banner on matchup cards.
### `PLAYOFF_BRACKET_INFO` — playoff bracket labels for W15/W16/W17. Keyed `year → week → { "NameA|NameB" → { label, style } }`. Names are sorted alphabetically before joining with `|`. Covers 2023, 2024, 2025 fully. Add 2026 data here once playoff matchup pairings are known. Styles: `'gold'` (championship), `'bronze'` (3rd/5th place), `'silver'` (consolation final), omit for regular bracket rounds.

---

## LOCALSTORAGE KEYS

| Key | TTL | Contents |
|-----|-----|----------|
| `tol_cache_v2` | 6h | Current season rosters |
| `tol_ktc_v4` | 24h | Live KTC player values (Superflex+PPR+TEP) — `{values: {playerName: {value,position,nflTeam,age,rank,trend,deep?}}, unresolved: [names]}`. Bumped from `v3` on 2026-08-20 when `unresolved` was added; a stale v3 cache would have served an empty untracked-set for three days and silently resurrected the flagged-player report. |
| `tol_theme` | permanent | User theme preference |
| `tol_lids` | permanent | Past league IDs |
| `tol_matchups_{year}` | permanent for completed seasons; **1h TTL for the current season** (+ cleared on Refresh) | All 17 weeks of matchup data. The current season needs a TTL because `starters` changes whenever a manager sets a lineup, and the Scores tab projects off those starters — a permanent cache pinned the whole year to whatever lineups happened to be set on first load. |
| `tol_matchups_ts_{year}` | permanent | Fetch stamp for the TTL above. Kept in a *separate* key because eight other call sites read `tol_matchups_{year}` directly and expect the bare `{week: [...]}` shape. |
| `tol_scoring_v1` | permanent (refreshed each boot) | The league's live `scoring_settings`, overlaid onto `SDATA` at parse time |
| `tol_txn_{year}` | permanent (2023–2025); **cleared on Refresh for 2026** | All completed transactions |
| `tol_drafts_{year}` | permanent | All draft picks |
| `tol_stats_v2_{year}` | permanent | Season stats aggregated from 17 weeks (2023–2025 only) |
| `tol_stats_wk_v2_{year}_{week}` | permanent | Single-week stats (2023–2025 only) |
| `_stats2026Cache` | session (JS variable, not localStorage) | 2026 actual + projected stats; cleared on Refresh via `refreshData()` |
| `tol_commish_ok` | **sessionStorage**, cleared on browser close | The Commissioner unlock flag. Also read by `isGradesAdmin()`. Deliberately session-scoped, not permanent — an admin panel that stays unlocked forever on a shared phone is worse than retyping a password. |

**The `_v2_` on the two stats keys is load-bearing.** `savePerm`/`loadPerm` carry no version and
no TTL, so before 2026-09-03 a returning visitor kept serving whatever `stats-history.json`
looked like on their first ever visit — regenerating the file reached new visitors only. That
went unnoticed because the file had not changed since May. **Any future change to
`stats-history.json`'s contents must bump these keys again**, and `purgeLegacyStatsCache()` in
`init()` sweeps the orphans (it removes any `tol_stats_*` key not carrying the current prefix —
widen its exclusion list when you bump to v3).

---

## VISUAL THEME — Arcade Neon (NFL Blitz)

Aesthetic: late-90s NFL Blitz / arcade-neon sports broadcast — glossy electric-teal + hot-magenta + neon-purple on near-black, pulled directly from the TOL logo. Premium / "legit" (ESPN/Sleeper-grade), **mobile-first**. Dark is the default theme; light mode is fully supported.

**HOW THE REDESIGN IS STRUCTURED — read this before editing styles:**
- The redesign is a stack of **appended CSS layers at the very END of `<style>`**, each opened by a banner comment: `ARCADE NEON REDESIGN`, then one block per tab (`CAREERS TAB — Arcade Neon polish`, `SCORES TAB…`, `RIVALRIES…`, `TRADE EVALUATOR…`, `DRAFT · STATS · TRANSACTIONS · LEAGUE…`, `HOME TAB…`, `LIGHT MODE…`), then the Phase 6 `.gr-*` block and the Phase 1 `CAREERS TAB · RECORD BOOK + HALL OF FAME & SHAME` block. They cascade over the original CSS above them — do not delete them.
- The Phase 1 layer styles `.hof-card` as an extension of the existing `.fun-card` (which had been defined but unused), with `.shame` recoloring to `--accent3`. Verified at 280 / 375 / 1280px in both themes: 1 / 2 / 5 columns, zero page or card overflow, and no hardcoded hex — light mode picks up `#0E9C92` / `#D6258F` automatically.
- Styling is **by class name and CSS variable**, never by editing individual elements. New content rendered by the existing JS inherits the look automatically **as long as it reuses the existing class names**.
- **To keep the design when adding things:** (1) reuse existing classes (`.r-card`, `.chip`, `.cp`, `.f-pill`, `.match-card`, `.dtbl`/`.career-tbl`, `.s-pill`, `.ic`, `.note`, …); (2) use the palette **variables**, never hardcode hex; (3) put any NEW css at the very bottom; (4) keep the banner-commented blocks.

### Color Palette — Dark (default)

| Role | Variable | Value |
|------|----------|-------|
| Primary accent (teal) | `--accent` | `#21F5E4` |
| Secondary accent (purple) | `--accent2` | `#9A55FF` |
| Tertiary accent (magenta) | `--accent3` | `#FF3DBE` |
| Background | `--bg` | `#06060C` (body uses a purple radial-glow gradient) |
| Panel surface | `--surface` | `#0B0918` |
| Card background | `--card` | `#100C22` (cards use a `#120D26 → #0C0920` gradient) |
| Borders | `--border` | `#27194E` (card borders often `#2A1C54`) |
| Body text | `--text` | `#FFFFFF` |
| Secondary text | `--text2` | `#D9D2F2` |
| Muted text | `--muted` | `#928AB8` |
| Position QB / RB / WR / TE | `--pos-*` | `#B98CFF` / `#3DF0A6` / `#5BB8FF` / `#FFB24A` |

### Color Palette — Light (toggle)
`--accent #0E9C92` · `--accent2 #7A33E0` · `--accent3 #D6258F` · `--bg #EEF0F5` · `--surface`/`--card #FFFFFF` · `--border #D6DAE6` · `--text #11151F` · `--text2 #3A4252` · `--muted #6A7384`. Light-mode surface fixes live in the `LIGHT MODE` block — any new **dark-only** rule (a `rgba(255,255,255,…)` background/border, or a hardcoded dark hex) must be paired with a `[data-theme="light"]` override there so the toggle stays clean.

### Typography System
Three-font system (Google Fonts):

| Use | Font | Notes |
|-----|------|-------|
| Display — titles, team names, stat values, countdown | **Saira Condensed** | Athletic condensed; **italic** on the marquee bits (`.sec-title`, `.rch-team`, `.champ-name`, `.cd-num`, `.hdr-league-name`) for the Blitz slant + teal neon glow in dark. **Replaced Bebas Neue everywhere.** |
| Body — chips, table cells, buttons, pills, labels | **DM Sans** | Clean, legible. Player-name chips are DM Sans (not mono). |
| Technical — timestamps, KTC raw values | **DM Mono** | Sparingly; never for primary content. |

### Nav (type-only)
The icon nav is **type-only** — emoji icons are hidden via `.itab-icon{display:none}` (markup untouched; the refresh ↺ still shows). The active tab gets a glowing teal underline (`.icon-tab.active::after`) + glowing label. Mobile: wraps to 2 rows of 5, 46px touch targets, clean per-cell teal underline.

### Accent usage
- **Teal** — active nav, primary buttons, winner rails, leading scores, links, key numbers.
- **Magenta/pink** — table headers, section subtitles, position-group labels (`.pl`), rivalry cards/totals, KTC owner column, H2H strips.
- **Purple** — countdown separators, secondary borders, the `is-you` roster card.
- **Gold** (`#FFD25A`) — champion card frame + trophy, "CHAMP" badges.

### Glow System
Neon glows are scoped to `[data-theme="dark"]` inside the appended blocks. Pattern: `text-shadow` / `box-shadow: 0 0 Xpx rgba(R,G,B,.Y)`. Keep subtle.

### Mobile-first
Phones are the primary target. Wide tables (`.career-tbl` / `.dtbl` / `.ktc-tbl`) scroll **inside their own container** with a sticky owner column so the page + nav stay put; card grids collapse to one column; stat strips are swipeable; the body background drops `fixed` attachment on mobile (iOS-safe). Each tab block ends with a `@media(max-width:680px)` section — keep new mobile rules there.

### Team-name shorthand
**`shortName()` does not exist — use `abbrev(name)`.** This entry described a
`shortName()` "defined next to `abbrev()`" for years; there are **zero** occurrences of it
in `index.html`, and calling it threw a live `ReferenceError` the first time Phase 12's chip
bar trusted this line. `abbrev(name)` is the real function and returns first-initial +
last name ("Matt Bova" → "M. Bova"). Team filter chips (Rosters, Draft, Transactions, Stats,
Trade Eval, Trade ROI) label with `abbrev(t(uid).name)` — the **real** name, not the Sleeper
display handle. Use it for any new team-filter UI, and fall back to the stored handle only
for a manager who has left the league and is no longer in `TEAMS`.

### Logo Files (wired in)
- **`TOL Banner Logo.jpg`** - the sticky header wordmark (84px tall; 56px mobile). 1998x648, ~3.08:1,
  500 KB. **It is a JPEG, not a PNG** - it arrived named `.png` and was renamed to match its actual
  bytes; browsers sniff content type either way, but the wrong extension is a trap for the next
  person. Being a JPEG it has **no alpha**: the black background is baked into the artwork.
- `TOL Large Logo.png` - home hero only now (max 420px; 260px mobile). Deliberately still the
  shield: a wide banner suits a header strip, a square mark suits a centered hero.
- `TOL Abbreviated Icon.png` - favicon + iOS add-to-homescreen icon
- `TOL Small Logo.png` - available if needed

**Glow treatment differs by mark shape, and that is the point.** The shield is a transparent PNG,
so `drop-shadow()` traces its silhouette. The banner is an opaque rectangle, so the same filters
trace its bounding box and read as a smeared rectangular halo. The `HEADER BANNER` CSS layer
therefore drops both `drop-shadow()` filters and the `.hdr-logo-link::before` radial glow, and
gives the banner rounded corners plus a single soft `box-shadow` in each theme. **If a
transparent-background banner ever replaces this file, revisit that layer** - `drop-shadow` would
be the right call again.

Banner size was left at 500 KB rather than downscaled: neither Pillow nor Node is installed on
this machine, and 500 KB is already 3-6x lighter than the three existing logo PNGs (1.5-3 MB
each). Worth revisiting if image tooling ever lands - it renders at 259px wide, so a 2000px source
is far more than it needs.

### PWA / Mobile meta
```html
<link rel="icon" type="image/png" href="TOL Abbreviated Icon.png">
<link rel="apple-touch-icon" href="TOL Abbreviated Icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="The Other League">
<meta name="theme-color" content="#06060C">
```

---

## KEY DESIGN DECISIONS (don't change without asking)

- **Distance-based PPR scoring** with TE premium (+0.5/rec). `SDATA` has **`rec: 0.0`** — corrected 2026-08-20, and this entry previously said the exact opposite ("has `rec: 1.0` (PPR). Do not set back to 0.0"), so don't trust a memory of the old rule. This IS a PPR league; it just pays for catches by *distance* (`rec_0_4` 0.5 / `rec_5_9` 0.75 / `rec_10_19` 1 / `rec_20_29` 1 / `rec_30_39` 1 / `rec_40p` 2) instead of a flat point each. Those buckets **are** the PPR — adding `rec: 1.0` on top pays for the same catch twice.
  **Evidence, so this doesn't get "fixed" back again:** Sleeper reports `rec: 0` for this league in all four seasons (2023, 2024, 2025, 2026 — checked via `previous_league_id` chain). Replaying 2025 Week 3 starters through `calcPts()` reproduces Sleeper's own team totals *exactly* at `rec: 0` (105.58 / 143.00 / 155.13 / 159.58) and overshoots by 23–40 points per team at `rec: 1.0`. The `1.0` was left over from an early KTC comparison, not a league rule. Effect of the fix: Puka Nacua's 2026 season projection went 467.5 → 346.8; every Est. Pts / Proj Pts figure on the site dropped accordingly.
- **`SDATA` is overlaid from the live league at runtime** — `applyLeagueScoring()` merges `/league/{LID}`'s `scoring_settings` over the hardcoded `SDATA`, cached in `localStorage['tol_scoring_v1']` and applied synchronously at parse time. The hardcoded block is now only an offline fallback, so a commissioner scoring change on Sleeper flows through without a code edit and `SDATA` can't silently drift again.
- **Trade Evaluator uses KTC Superflex + PPR + TE Premium** (`format=1&tep=1` → `superflexValues.tep.value`). Pick values are KTC raw at slider +25%; default 0% = 80% of KTC. 2026 picks excluded (draft complete). Player Values table builds from Sleeper rosters first for guaranteed ownership, then adds unrostered KTC entries.
- **Dark/light theme toggle** — persists via `localStorage['tol_theme']`
- **LocalStorage caching** — Sleeper roster data cached 6h; historical data permanent
- **CORS fallback chain** — direct → corsproxy.io → allorigins.win; never remove
- **Single-file architecture** — all HTML, CSS, JS in `index.html` inside `Sleeper FF/The Other League/` (the outer repo root has only a redirect stub)
- **Roster chips colored by position** — QB=purple, RB=green, WR=blue, TE=orange, K=gray, DEF=red. Color legend shown at top of Rosters panel using actual `.chip` elements. Number in parentheses after player name = age.
- **Position badge (`.cp`)** — the position label inside each `.chip` is styled as a small colored badge: DM Sans 600, 10px, `padding: 1px 4px`, `border-radius: 2px`, background from `--pos-XX-bg` CSS variables (semi-transparent, defined for both dark and light themes). Replaced Bebas Neue — do not revert.
- **Avg Age badges (`.bdg`)** — use DM Sans 600 at 10px. The override block near the end of `<style>` sets `font-family: 'DM Sans'` — this overrides the base `.bdg` rule. Replaced Bebas Neue — do not revert.
- **Rivalries from 2025 forward only** — pre-2025 matchups excluded from rivalry records. Rivalry weeks: W4 and W13 (both 2025 and 2026). W14 is NOT a rivalry week — a prior mistake that was corrected.
- **2026 draft is linear, not snake** — rounds 2–4 follow the same order as round 1
- **Sidebar is gone entirely** — removed 2026-08-20, markup and JS and CSS. Do not add it back without explicit request.
- **Cache bar is permanently hidden** — hidden via inline `style="display:none"` on the div. The underlying elements still exist and `refreshData()` / `setCacheBar()` still work correctly — do not remove the DOM elements.
- **Every aggregate stat is regular season only — weeks 1–14.** Confirmed by Matt 2026-08-20 and it is a data-quality rule, not a presentation preference: weeks 15–17 are the playoff *and* consolation brackets, and roughly half those games are consolation matchups with nothing at stake, where managers routinely leave a stale or empty lineup. Averaging those in makes a manager look worse (or a blowout look bigger) for a game nobody was trying to win. `REG_WEEKS = 14` is the single constant; `buildAllTimeStats`, `buildH2HMap`, `buildMedianMap`, `buildH2HForYear` (default), `buildSeasonStandingsData` (default) and the live-standings week scan all honor it. **Any new code that walks `tol_matchups_*` must cap at `REG_WEEKS`.** The Scores tab is the deliberate exception — it is a browsable scoreboard, not an aggregate, and should keep showing W15–W17.
  If playoff stats are ever wanted they belong in a **separate** set, and they must be filtered to the *winners* bracket via `PLAYOFF_BRACKET_INFO` — an all-weeks-15-to-17 aggregate is exactly the noise this rule exists to keep out.
- **The nav is five tabs and that is a budget, not a snapshot.** Five at `width:20%` is exactly one mobile row; a sixth wraps it to two and undoes the 2026-08-21 consolidation. New surfaces become a **sub-view** of an existing tab. Every tab merge since has followed the same self-contained-divs pattern (`setRosterView` / `setCareersView` / `setMovesView`), and every retired hash got a `TAB_ALIASES` entry — do both.
- **Careers is All Time + Hall of Fame & Shame + one tab per season, and superlatives live in exactly one place.** All Time holds the career table and the All-Time Record Book; Hall of Fame & Shame holds the award grid; each year tab holds that season's standings and recap. The old `.career-status-bar` pill strip is gone; its 7 stats are cards in the grid now. Don't reintroduce a second surface for "league leader"-type stats — that split is exactly what this consolidated. Season standings were stacked under All Time until 2026-08-21; four tables in one scroll was a wall, and none of them had anywhere to put a write-up. **The payout cards moved to the same year tabs on the same day** — a season's money belongs next to that season's table, not on a separate tab, and putting them together is what surfaced the missing $15 (see `SEASON_PAYOUTS`).
- **The survivor pool is computed from the scoreboard, never hand-recorded.** The rule is
  deterministic and the scores are already on the page, so a hardcoded elimination list could only
  ever drift from the grid rendered directly beneath it. Same reasoning as the median game having
  one implementation shared by the Scores tab and the all-time engine. If a week's elimination
  ever looks wrong, the fix is in the *scores*, not in a manual override. See Phase 10.
- **A week's Scores page has two recap scopes and they stay separate** — one whole-league
  week-in-review at the top (`weekly-recaps-<year>.json`), and one write-up per game at the foot
  of its card (`matchup-commentary-<year>.json`). Different files, different lengths, different
  jobs. Don't collapse them into one.
- **Year standings default to Place ascending; the All Time career table defaults to Career Earnings descending.** Confirmed by Matt 2026-08-21. Both are sticky per table once a header is clicked — that is deliberate, don't reset them on tab switch.
- **Matchup commentary: 2025 is hybrid, 2026 forward is hand-written only** (Matt, 2026-08-21). Placement games (3rd, 5th) and the Consolation Final are in scope because they carry a reward; the rest of the consolation bracket gets nothing and renders no toggle. See Phase 8.
- **A manager's name is rendered through `ownerLink()`/`ridLink()`, never as bare text.** That is
  what makes every name on the site open a profile, and it is the thing a new render site will
  forget. If you add a surface that shows a manager's name, route it through the helper.
- **The profile is an overlay, not a route.** It opens over whatever you were reading and closes
  back to it, with the tab, scroll position and URL hash untouched. Don't convert it to a tab or a
  hash route — losing your place on the Scores tab is the exact failure it exists to avoid.
- **Award definitions live in `ownerAwardDefs()` only.** The Hall of Fame grid and the profile
  award standings both read it. Two lists is how the two surfaces drift.
- **\* Andrew Bova inherited roster 11 from Chris Jacobs in 2026.** Verified against the API: roster
  11's `owner_id` is `728293730280427520` ("CCJ") for 2023/24/25 and `467166827215056896` (Andrew)
  from 2026. `RM` maps roster 11 to Andrew for *every* season, so all of Chris's results already
  flowed into Andrew's totals before this was noticed. **That attribution was deliberately kept**
  (Matt's call, 2026-08-21) so the franchise history stays continuous — the star and the footnote
  on his profile are what make it honest. Do not silently re-split it; changing it would move
  career earnings, playoff berths and Hall of Fame standings. The marker is a plain `*` in
  `var(--muted)` at 60% opacity (Matt, 2026-08-21) — it appears beside his name in ~90 places, so
  anything louder read as decoration rather than a footnote.
- **Home panel has no quick-nav grid** — navigation is entirely via the icon nav and the logo home link
- **"Ask Claude" is fully gone** — panel, icon tab, JS and CSS all removed (the last of it 2026-08-20). The old note here claimed the JS "must remain because `getTradeAI()` calls them"; `getTradeAI()` had itself been removed in the June 2026 overhaul, so that was stale and kept ~20 KB of dead code alive for two months.

---

## LEAGUE CONTEXT SUMMARY

- 12 teams, dynasty format, Year 4 (2026 season — post-draft)
- Commissioner: Matt Bova — team "Show Me Your Penix"
- 2025 Champion: Jake Blackwell ("Nacua Matata") — had pick 1.12 in 2026 draft
- 2025 Consolation: Nick Merkel ("Breeces Peanut ButterCups") — had pick 1.13 in 2026 draft
- 2026 Rookie Draft: **Complete** — results pulled live from Sleeper API on Draft tab
- Contenders: Chris Bova ("Titsburg Feelers"), Jake Bogardus ("BoKnows723")
- Active traders: Chris Merkel, Nick Merkel
- 2027 rule change voted in: 1 WRRB_FLEX → WR/RB/TE FLEX (increases TE value)
- Full context in: `the-other-league-context.md`

---

## DEVELOPMENT ROADMAP

### Phase 1 — All-Time Records & Career Stats — **shipped 2026-08-20**
**Goal:** all-time per-owner records and superlatives. Built as **two sub-tabs inside Careers**, not a new top-level tab (the nav was already 10 wide; it is 5 now) — see "Careers Panel" under NAVIGATION STRUCTURE and "All-Time Stats Engine" under JAVASCRIPT FUNCTIONS.

- ✅ All-time W/L record per owner — `buildCareers()` career table + per-opponent history in `buildRivalries()`
- ✅ Most championships, most playoff berths — `buildRecordBook()`; berths derived from `PLAYOFF_BRACKET_INFO`
- ✅ Highest / lowest single-week score — `buildRecordBook()`
- ✅ Biggest blowout, closest finish, highest / lowest-scoring matchup — `buildRecordBook()`
- ✅ Longest win / losing streak — `buildRecordBook()`, running across season boundaries
- ✅ Most / fewest points in a season — `buildRecordBook()`, complete 14-week seasons only
- ✅ 12 new superlatives beyond the original 7 pills — `buildHallOfFame()`

**Verified against live cached data, not assumed:** 252 games (3 seasons × 14 weeks × 6), every owner at exactly 42 games with H2H and median each summing to 42, playoff berths summing to 18. 2026 correctly contributes nothing — see the `weekWasPlayed` note below.

**One real bug fixed on the way in.** Unplayed Sleeper weeks come back as scored-zero rows, and the all-time median math was counting every one of them as a loss for all twelve owners. This was already live and visible in the career table. Full detail under `weekWasPlayed()` in JAVASCRIPT FUNCTIONS.

**Layout decisions (Matt, 2026-08-20):** two sub-tabs rather than three (season standings stay stacked under the Records view); the second tab is named **"Hall of Fame & Shame"** because roughly half the awards are roasts; and the original 7 pills were **folded into** the card grid rather than kept as a separate strip above it, so there is one surface for superlatives instead of two.

**Scope confirmed by Matt 2026-08-20: regular season only, weeks 1–14** — see the standing rule under KEY DESIGN DECISIONS for the reasoning and the audit it triggered. All four Careers captions now state the week range on screen so nobody has to guess what "Total W-L" covers.

**Possible follow-ups (not built):** a **separate** playoff record set — which must be winners-bracket only via `PLAYOFF_BRACKET_INFO`, not a blanket weeks 15–17 aggregate; a per-season record book (currently all-time only); a "current streak" alongside the all-time longest; and clicking a record through to that week on the Scores tab.

---

### Phase 2 — Head-to-Head Rivalry History — **shipped 2026-08-21**
**Goal:** Expand the existing Rivalries tab with full all-time H2H detail. See "Head-to-Head Explorer + Nemesis Board" under JAVASCRIPT FUNCTIONS for the full mechanics.

- ✅ All-time H2H record between any two managers (clickable matchup grid) — `buildH2HPicker()`, a 12×12 grid covering all 66 possible pairs, not just the 6 official rivalries
- ✅ Full game log per rivalry (date, scores, winner) — `renderH2HDetail()`, with a `goToScoresWeek` link per game
- ✅ Average margin of victory per matchup — `pairView().avgMargin`, shown on the detail card
- ✅ "Nemesis" stat — `computeNemesisMap()` + `buildNemesisBoard()`, gated on a 2-game minimum sample

**Scoping decision:** unlike the 6 `RIVALS` cards (2025+ only — see KEY DESIGN DECISIONS), this covers every meeting back to 2023. "Any two managers" is a genuinely different, broader question than "the 6 pairs the league calls rivals," so it gets the real history rather than inheriting the rivalry-era cutoff.

**Data source:** the same cached `tol_matchups_{year}` and guards (`weekWasPlayed`, `REG_WEEKS`) as `buildH2HMap()` — no new fetch, so it costs nothing extra to load. **Complexity was Low-medium as scoped**, and stayed there: the whole feature is 214 lines, purely additive, no existing function's behavior changed.

---

### Phase 3 — Draft History + Draft Grade / ROI
**Goal:** Expand Draft tab with historical class view and value grading.
- Draft class by year (2023, 2024, 2025) — who drafted whom
- Current KTC value of each pick (value at time of draft vs. today)
- ROI grade per pick: bust / average / hit / home run (KTC delta + games started)
- Best/worst draft class per manager all-time

**Data source:** Sleeper draft API (partially built in `buildDraftHistory()`) + KTC values. **Complexity: Medium.**

---

### Phase 4 — Dynasty Prospect Tracker
**Goal:** Tab or section showing all rostered rookies/young players with KTC trend.
- Player name, age, position, team
- KTC dynasty value + trend (up/down/flat)
- Which TOL manager owns them
- "Rising star" badge for players under 24 with climbing KTC value

**Data source:** Sleeper rosters + KTC values (same as Phase 3). Build back-to-back with Phase 3. **Complexity: Medium.**

---

### Phase 5 — "Wrapped" Season Recaps
**Goal:** One shareable recap card per season per manager.
- Best week, worst week, luckiest win (won despite lower score via median system)
- Most points left on bench, biggest over/underperformance vs. projections
- "Your 2024 in one sentence" — AI-generated summary via `getTradeAI()` / Ask Claude layer

**Data source:** Weekly matchup data (requires all weekly data loaded first). **Complexity: Medium-high — finish data pull before building this.**

---

### Phase 6 — Roster Grades & Outlook — **shipped 2026-08-20**
**Goal:** Per-team roster card showing dynasty health and outlook, as a sub-tab inside the existing Rosters panel (not a new top-level tab — see "Roster Grades & Outlook" under JAVASCRIPT FUNCTIONS for the full function list, and "Rosters Panel" under KEY ELEMENT IDs).

**Confirmed methodology (final, not the original single-axis draft):**
- Two-axis classification: **Value** (KTC total, ranked 1–12, split top4/mid4/bottom4) × **Timeline** (age-curve-weighted runway score per `AGE_CURVES`, NOT raw avg age)
- 4 named quadrants from crossing top/bottom value × young/old: Stacked Contender, Win-Now/Aging Window, Genuine Rebuild, Bad & No Future Currency (deliberately distinct from Rebuild)
- Matching hardened: `getKTCEntryFuzzy`/`normalizeName` had two real bugs (suffix-direction, ASCII apostrophe) found and fixed while building this — see JS function notes. Unmatched starters/bench are flagged in the UI, never silently zeroed; only taxi/IR get a nominal floor value.
- Position depth flags: bench value vs. league median bench value at that position
- Grade + rationale: rule-based from value/quadrant/depth/match-confidence, no AI/free text
- Snapshot: frozen per grading period as a committed `roster-grades-<period-id>.json` (superseded the original once-a-year `roster-grades-snapshot-<year>.json` naming on 2026-08-20); Outlook (composition/depth) refreshes live and is shown separately from the frozen grade

**Built:** full data layer (value summation, timeline scoring, quadrant classification, depth flags, grading, snapshot read + export-to-commit) + working card UI for all 12 teams, verified against live Sleeper/KTC data in-browser.

**2026-08-20 — league-facing release.** Reconciliation, UI rewrite and the first frozen period all landed together:
- ✅ **Every unmatched player reconciled — the aggregate report is now empty.** Five of the seven "genuine KTC coverage gaps" recorded on 2026-08-19 were never gaps; see the corrected note under `buildUnmatchedReport` above. The scraper recovers them via per-player pages; the two genuinely-untracked bench QBs now count as confirmed zero-value spots instead of being dropped from the roster. This materially changed grade inputs: Bench Dead Weight counts moved (Joshin Around 9→11, and Ertz/Hunt/Mixon/Lockett/Ekeler now count against the teams holding them), which shifts `deadWeightRank` and therefore the cap.
- ✅ **The card grid is gone from the league view.** It was an internal working view — every manager could read every other manager's dead-weight tally, speculative-depth count and match-confidence warnings. Replaced by a ranked row list (team · owner · grade), each row expanding to a plain-English write-up, with the full rubric explainer and the grading date below. Raw metrics, the unmatched report and the snapshot exporter moved behind `?admin=1`.
- ✅ **Grading periods.** `roster-grades-<period-id>.json` + `GRADE_PERIODS` + tabs, built for midyear/end-of-year runs. `roster-grades-2026-preseason.json` is committed and is the first real frozen grade.
- ✅ **New CSS layer** (`.gr-*`, appended banner-commented block per the redesign convention), verified in both themes.
- ✅ **Fluid sizing, no horizontal scroll to reach a grade (2026-08-20).** Grade chip and team name are `clamp()`-sized rather than stepping at the 680px breakpoint — don't reintroduce fixed-px overrides for `.gr-head`/`.gr-team`/`.gr-grade` in the media query, they defeat it. The team name wraps to two lines instead of ellipsing, since hiding a team name to buy space is worse than one extra line. Verified 280–1607px: grade chip never leaves its row, no page overflow. Also fixed the **shared** `.roster-grid` (`minmax(320px,1fr)` → `minmax(min(320px,100%),1fr)`), which overflowed the page below a 320px container and pushed the grade badge on the admin metric cards off-screen — that bug affected the Team Rosters view too.

**Still open / TODO:**
- ⚠️ **The curve is bimodal and Matt has not signed off on it.** The 2026 Preseason run produced A, A, A, A-, B-, B-, C+, C, D, F, F, F — nothing in the B/B+ band at all, and four teams at D or F despite the worst roster being only ~33% behind the best. Bottom-2 value (base 0.7) plus Weak readiness (−0.8) is an automatic F with no possible offset, and the scale has no C-/D+ granularity to land in. Retuning is a data-only change: adjust `gradeRoster()`, re-export from the admin panel, recommit the period file.
- Middle-value-third quadrant labels ("Building"/"Treading Water") are an assumption, not in the original 4-quadrant spec — confirm with Matt
- Timeline score is weighted across the whole roster, not starters-only — confirm that's the intended scope
- Write-ups are hand-authored per period, so a new grading run needs 12 new ones written (by design — see `GRADE_WRITEUPS`)
- ✅ 2026-08-19: nickname/display-name mismatches now handled via `KTC_NAME_ALIASES` (checked before fuzzy matching) + `buildUnmatchedReport()` as the ongoing discovery process. ~~7 players remain unmatched league-wide … confirmed genuine KTC coverage gaps~~ — **superseded 2026-08-20, that conclusion was wrong**; five of the seven were simply below KTC's 500-row embed cap. See the corrected note under `buildUnmatchedReport` and the release entry above. Count is now 0.
- ✅ 2026-08-19: **Kenny Gainwell resolved — was a real matching bug, not a KTC gap.** KTC tracks him as "Kenneth Gainwell" (full first name); Sleeper uses "Kenny." Added to `KTC_NAME_ALIASES`. Matt's own team's total moved 73,423 → 76,386 KTC and is no longer showing an unverified-starter warning.
- ✅ 2026-08-19: timeline score now excludes confirmed-but-negligible-value players entirely (`NEAR_ZERO_KTC_THRESHOLD`), and a separate "Speculative Depth" (lottery-ticket) count is shown per team (`SPECULATIVE_VALUE_THRESHOLD`), not folded into the timeline score or grade. Near-zero exclusion currently affects 0 players league-wide; speculative counts range 0–5 across the 12 teams.
- ⚠️ 2026-08-19 (first pass, superseded same day): **Current-Year Readiness** was first built from `isStarterSlotShaky`/`computeTeamReadiness` (Strong/Average/Weak from how many of the manager's *actually-set* starter slots were shaky). Matt correctly flagged two flaws: it measures who's starting, not the *value* of those starters, and it falsely reads "Weak" for a manager who simply hasn't set a lineup (i LOVE mendoza showed 5 of 11 slots empty for exactly this reason, not because of bad players).
- ✅ 2026-08-19 (same day): **Current-Year Readiness rebuilt** around season-long projected points and an optimal-lineup solve — see "Current-Year Readiness (2026-08-19 full rebuild)" in JS function notes for the full mechanics (`getSeasonPointsByPid`, `getLeagueRosterPositions`, `computeOptimalLineup`, `computeReadinessRankings`). This also surfaced and fixed a real, previously-silent bug: the projections API URL was missing `regular` in the path and had been returning empty data for every player, always (see `fetch2026SeasonStats()` note above) — found while investigating why Sleeper's own projections weren't showing up, which Matt correctly pushed back on when told they weren't available. Verified against real data: i LOVE mendoza now resolves to a full 11/11 lineup, Average readiness, rank #8 of 12 — an honest "doesn't project as well as its dynasty value suggests" read instead of a false "half the lineup is empty" one.
- ✅ 2026-08-19: **Unproven Risk replaced with Bench Dead Weight.** Matt confirmed the recommended fix. The old flat "% of value in unproven players" trigger (10 of 12 teams flagged at 25%) is gone — replaced by `isDeadWeight` (veteran, years_exp≥2, confirmed KTC value ≤2000, same threshold `speculativeCount` uses on the young end) ranked across all 12 teams, worst third flagged as `highDeadWeightRisk`. Now driving both the quadrant "— High Bench Dead Weight" suffix and the grade cap. Verified: exactly 4 of 12 teams flagged (Titsburg 9, BoKnows723 8, SirWinsAlot 7, i LOVE mendoza 7), a real discriminating spread instead of nearly everyone.
- ✅ 2026-08-19: **grade formula blends Readiness in and applies Bench Dead Weight as a hard cap** — `highDeadWeightRisk && readiness.tier!=='Strong'` clamps the score so the team can reach at most a B+, never A-/A, regardless of raw value rank. `readiness.tier` comes from the projected-lineup ranking. See `gradeRoster()` in JS function notes for the exact mechanics, and the same section for a rationale-text bug this surfaced and fixed (a team with the cap condition only half-true was claiming "grade capped" when it wasn't actually capped).
- ✅ 2026-08-19: **Future draft-pick value now counted in Roster Value.** Matt caught that `total` was players-only. Now folds in 2027/2028 picks via the existing `buildFuturePicksMap()` + `getKTCPickValue()` (raw value, "Mid" tier default, not the Trade Evaluator's slider-adjusted value). Verified material: ~16,000–31,600 per team, roughly 15–25% of total value, genuinely shifted Value Rank for several teams once added — this wasn't a rounding-level fix.
- ~~Visual polish deferred~~ — done 2026-08-20 via the `.gr-*` CSS layer. The admin-only metric cards still reuse `.r-card` as-is, which is fine for a working view.

**Data source:** Sleeper rosters + KTC values (same as Phases 3–4). **Complexity: Medium — KTC integration was the key dependency; matching turned out to need two real fixes.**

---

### Phase 8 — Matchup Commentary — **2025 complete 2026-08-21; 2026 written live, week by week**
**Goal:** a write-up under every matchup that mattered, on the Scores tab. See "Matchup Commentary" under JAVASCRIPT FUNCTIONS for the functions.

**Which games get one.** All of weeks 1–14. In the brackets, driven mechanically off `PLAYOFF_BRACKET_INFO`: Winners Bracket, Championship, 3rd Place, **5th Place**, and the **Consolation Final · 13th Pick** — that last one is deliberate and confirmed by Matt, because it hands the winner the 1.13 rookie pick and is not a nothing game. A bare `Consolation` / `Consolation · Round 1` / `Consolation · Semifinal` gets nothing. For 2025 that is 84 + 8 = **92 write-ups**.

**How they're written.** 2025 is a **hybrid**: `build_matchup_facts.py` emits a fact sheet, routine games get a generated first draft, and the games that mattered are hand-written. **2026 forward is 100% hand-written** (Matt, 2026-08-21) — the script stays, but only as a fact sheet. Voice is Hall of Fame & Shame roast level; punch at the decision, not the person; nothing boring.

**`scripts/build_matchup_facts.py`** — offline, run by hand, output **never committed** (it is a writing source, not a site asset). Goes back to the live Sleeper payload for `players_points`/`starters_points`, which `fetchAllMatchups()` deliberately trims away. Per matchup it computes margin class, the median result for both sides (lucky win / unlucky loss), per-starter projected-vs-actual, the biggest over/underperformer, bench total, the best legal bench swap and whether it exceeded the margin, optimal-lineup points left on the table, position-group totals, records/streaks entering, and prior H2H.

- **Scoring is a verified port of `calcPts()`**, fed by the league's own live `scoring_settings` rather than a hardcoded table. Confirmed exact: replaying 2025 W3 reproduces Sleeper's own team totals to the cent (127.47 / 105.58 / 143.00 / 155.13), with 11/11 starter projection coverage.
- **Sleeper's projections are optimistic, and by a different amount every week** — 2025 ranged from **−29.6 in W1 to +7.4 in W5** league-wide. So a raw "underperformed by 25" is meaningless; in Week 1 that was simply average. Every proj-vs-actual claim must use **`proj_delta_adj`**, which nets out `week_proj_bias` (the median of all twelve teams' deltas that week). Do not quote `proj_delta` in prose.
- Records follow the site's own convention — **H2H plus median**, weeks 1–14 only, matching the career table's "Total W-L". Verified against the 2025 final standings.
- Historical projections are available: `/projections/nfl/regular/2025/{week}` returns real stat lines including the distance buckets (`rec_0_4` … `rec_40p`), so `calcPts()` scores them correctly under this league's rules.

**Writing traps found in the test slice.** Both were caught by checking, and both would have shipped as false claims:
1. **"Lowest score of the season" was wrong.** Jake Bogardus' 62.60 in the W17 3rd-place game is the *second* lowest — Erin Jacobs posted **4.85** in a W16 *consolation* game with an abandoned lineup, which is exactly the noise the weeks-1–14 rule exists to exclude. Phrase such claims as "in a game anyone was trying to win."
2. Anything the prose asserts beyond the facts file (a player being inactive, a retired QB starting) needs a direct check against `/stats/nfl/regular/{year}/{week}`. Lamar Jackson's 0.00 in that same game is real — he has *no stat line at all* for 2025 W17.

**Status: 2025 is COMPLETE — all 92 write-ups shipped 2026-08-21.** Length and tone signed off by Matt: headline + 3-4 sentences, Hall of Fame & Shame roast level. Don't re-litigate the voice; match what is there. Real point figures (bench totals, points left on the table) are deliberately kept in the prose, unlike the Phase 6 rule that strips raw KTC values — points are a scale everyone reads natively, KTC is not.

**Verified before shipping, mechanically not by eye:**
- 92/92 coverage, zero consolation leakage, per-week counts 6×14 + 2 + 3 + 3. Confirmed in-browser week by week: W1-14 render 6 cards / 6 recaps, W15 4/2, W16 6/3, W17 4/3.
- **All 617 quoted decimal figures checked against the facts file** by script, with a ±0.06 rounding tolerance. The 14 that didn't match a single field are deliberate cross-week callbacks (Mark Andrews' 1.75 / 1.40 / 29.35 run, Bowers' 47.05 the week before) or sums, each verified separately.
- Tags checked against the facts predicates. Two false `NAILBITER` tags were caught and removed (7|5 at 9.07 and 13|2 at 6.79 — the tag means margin under 5, and a chip that lies is worse than no chip).
- Only non-ASCII character in the file is U+2014; every apostrophe is ASCII.

**Four false superlatives were caught and corrected during writing** — worth reading before adding a season-wide claim, because the pattern repeats:
- "Best week against par all season" was claimed for Erin's +65.8 (W8), then Bogardus' +56.7 (W6), then Matt's +54.8 (W9). The real answer is **Andrew Bova +67.6 in W14**, with Jake Blackwell +67.0 second. Week 14 outscored everything and was written last.
- "Tidiest lineup of the year" was claimed twice off `left_on_table`. The real minimum is **0.43 (Andrew Bova, W14)**; Chris Bova's W8 3.30 is the lowest *bench total*, which is a different statistic.

**Rule for the 2026 pass: rank the metric across the whole season before writing any superlative, not from the week in front of you.** Every "best/worst/lowest/highest ever" needs a sort, and the sort must cover all 17 weeks.

---

### Phase 9 — Careers Year Tabs + Season Recaps — **shipped 2026-08-21**
**Goal:** give every season its own home. The Records sub-tab became **All Time** (career table + record book), the four stacked standings tables moved into **one sub-tab per season**, and each year got a written season recap beside its standings. See "Season Recaps" and "Careers" under JAVASCRIPT FUNCTIONS for the functions, and "Careers Panel" for the markup contract.

**Layout.** `.season-split` is a wrapping flexbox — standings left, recap right on a wide screen, recap underneath on a narrow one, decided by available width rather than a viewport breakpoint. Verified at 1280px (side by side, table 683px / recap 508px, zero page overflow) and 375px (stacked, table scrolling inside its own container, zero page overflow), both themes.

**The recaps.** Hand-written, one per completed season, in `season-recaps.json`. Voice matches Phase 8 — Hall of Fame & Shame roast level, punch at the decision not the person. Length ~350 words each, roughly 4× a weekly matchup write-up, which is what fills the column beside a 12-row table without running past it.

**`scripts/build_season_facts.py`** — the season-level companion to `build_matchup_facts.py`, written for this phase. Per season it produces: full standings (H2H / median / total / PF / PA / ppg / high / low / stdev / weekly crowns and duds / lucky wins / unlucky losses / longest streaks / full game log), week-by-week high-low-median, ranked season extremes (highest and lowest weeks, biggest blowouts, closest games, highest and lowest-scoring matchups), bracket results, per-roster and league-wide top starters, best single-player weeks, every trade with players and picks, per-manager transaction counts, and the rookie draft. Output is a writing source, never committed.

- **It resolves `roster_id → owner` from that year's own API payload**, not from `RM`. The mapping happened to be identical in all three seasons, but assuming that would have silently mis-attributed an entire recap if it ever changed.
- Ports `weekWasPlayed` and the weeks-1–14 rule, so nothing here can disagree with the site.

**Every figure was checked mechanically, not by eye.** A sweep over all 46 quoted decimals across the three recaps matched them against the fact sheets at ±0.06; the only two that didn't were "1.13" (a draft pick, not a score) and James Cook's 8.20 in the 2025 final, which is a *bracket* week and therefore outside the facts file — confirmed separately against the live W17 payload. Every `W-L` string in the prose was matched against a real record in that season's standings (23/23). A further 47 non-numeric claims — crown and dud counts, PF ranks, draft slots, opening streaks, trade counts, "league's number one scorer" — were asserted in a script and passed.

**Two traps worth remembering, both the Phase 8 pattern repeating:**
1. **Rank the metric across the whole season before writing a superlative.** "Erin finished with the fifth-fewest points in 2024" was wrong — she was eleventh of twelve. Caught by sorting, not by memory.
2. **A season's team names are not today's team names.** Sleeper stores per-league user metadata, so 2023 comes back as ChubbLess / Blackwell #2 / Brady's Kids, none of which exist now. The recaps use owner names for that reason, with the period team name only where it is the joke (Chris Merkel's "Do the TANKy Leg" in 2024).

**One pre-existing bug fixed on the way in.** The live-season standings handed the alphabetically-first owner "🏆 1st" before a single game had been played. It was there before this phase, but a 2026 tab makes it a headline rather than a footnote; `renderStandingsTbody` now renders `—` for `pending` rows.

**Second pass, same day (Matt's follow-ups):**
- ✅ **Payouts moved from the League panel to the Careers year tabs**, beside the standings, with the recap dropped underneath. The hardcoded four-card `info-grid` became the `SEASON_PAYOUTS` data object rendered by `payoutCardHtml()`; 2026 carries the existing "Pending" placeholder (pot $1,200, everything else TBD) unchanged.
- ✅ **Tab 9 relabeled "League" → "Rules".** Label only — ids, hash and `VALID_TABS` untouched. What's left on that panel is rule updates, format and scoring, which is what the name now says.
- ✅ **Sort defaults confirmed, not changed:** year tables lead with Place ascending, the All Time career table with Career Earnings descending. Both were already correct.
- 🐛 **Found by putting the two payout records side by side: `SEASON_HISTORY[2024]` was missing Duane Gillenwater's $15** (Best QB, Lamar Jackson). The itemized card had it, this object didn't, so his career earnings read $200 instead of $215 and the 2024 card summed to $1,185 against a $1,200 pot. Fixed. This is exactly the class of error the move was always going to surface — the two numbers now render six inches apart.
- ✅ **2025's $25 gap was closed in a parallel session** (commit 128dd39) while this work was in flight: the money was held back for the championship trophy, so it belongs in Jake Blackwell's 1st-place total. Merged in here — see `SEASON_PAYOUTS` for the reconciled state of all three seasons.

**Merge note (2026-08-21).** This branch deleted the League-panel payout markup at the same time as 128dd39 was editing two lines inside it, so `index.html` conflicted in two places: the deleted payout block (took the deletion, carried both of their corrections into `SEASON_PAYOUTS` by hand) and the end of `<style>`, where both sides had appended a new banner-commented CSS layer (kept both). **That second conflict is structural, not bad luck** — the redesign convention says new CSS goes at the very bottom of `<style>`, so any two branches that add a layer will collide there. Expect it, and resolve by keeping both blocks rather than picking a side.

**Not built:** 2026 has no recap (it hasn't happened); write one after the season. Per-season *record books* are still all-time only — see the Phase 1 follow-ups.

---

### Phase 10 — Weekly League Recap + Survivor Pool — **machinery shipped 2026-08-21; content written weekly**
Asked for by Matt on 2026-08-21, ahead of the 2026 season. Three things landed together: the 2026
payout structure, a whole-league weekly recap above the match grid, and a survivor-pool tracker.
Implementation detail is in **Survivor Pool + Weekly League Recap** under JAVASCRIPT FUNCTIONS.

**What the Scores tab now stacks, top to bottom:** whole-league recap → survivor tracker →
rivalry / projection banners → the match grid, each card with its own per-matchup recap at the
foot. The league recap and the matchup recaps are **different files and different scopes** — one
week-in-review for the league, twelve write-ups for the individual games. Don't merge them.

**THE WEEKLY WORKFLOW (2026, weeks 1–17).** Every week is a two-file edit, both hand-written:
1. `scripts/build_matchup_facts.py` for that week — **every number in both files comes from here.**
   Never write a figure from memory or from the API by eye.
2. `weekly-recaps-<year>.json` — one entry keyed by week number:
   `{headline, facts: [{k,v}], paragraphs: []}`. 2–3 paragraphs / ~200–250 words: longer than a
   matchup write-up, shorter than a season recap. 3–5 `facts` reads best; past 6 the strip wraps
   badly on mobile.
3. `matchup-commentary-<year>.json` — one entry per game keyed `"week|matchup_id"`, unchanged
   Phase 8 shape and voice.
4. **Do NOT write survivor eliminations into either file.** The tracker computes them. The only
   thing to check is that the week's scores are final on Sleeper before pointing anyone at it.

**Voice:** matches Phase 8/9 — Hall of Fame & Shame roast level, punch at the decision not the
person. Real point figures stay in the prose.

**Survivor decisions, both confirmed by Matt 2026-08-21:**
- **The pool settles after Week 11, not Week 12.** His note said "lowest scoring team eliminated
  each week until highest scorer of last 2 teams is determined week 12", but 12 teams minus one a
  week from Week 1 leaves one team standing after Week 11 — the arithmetic doesn't reach 12. He
  chose to keep straight one-per-week elimination and crown at W11. Week 12 still renders the
  block holding the settled result, so the "weeks 1–12" framing in his note still reads true.
- **Lowest score of the week goes, win or lose.** The head-to-head result is irrelevant to it.

**Built:** ✅ `SEASON_PAYOUTS[2026]` (15 lines, reconciles to $1,200) · ✅ `computeSurvivor()` +
`survivorBlockHtml()` · ✅ `loadWeeklyRecaps()` + `renderWeekTopBlock()` · ✅ `.wr-*` / `.sv-*` CSS
layer · ✅ `weekly-recaps-2026.json` and `matchup-commentary-2026.json` scaffolded empty (the
second also clears a 404 the Scores tab had been throwing on every 2026 load).

**Verified before commit:** engine replayed over the finished 2025 season — 11 eliminations, one a
week, single champion after W11, no ties. All five render states checked (unplayed / eliminated /
crowned / settled / week 13+ renders nothing), payout card reconciled in the DOM, and zero
horizontal overflow at 375px in both themes.

**Not built:** no per-week *automation*. `scripts/tuesday_update.py` still only maintains
`h2h-records.md`; it does not draft recaps or touch either JSON. Worth considering: extend
`build_matchup_facts.py` to emit a week's fact sheet for both files in one run.

---

### Phase 11 — Manager Profiles — **shipped 2026-08-21**
**Goal:** a per-manager career profile, reachable from every occurrence of that manager's name
anywhere on the site. Asked for by Matt on 2026-08-21. See "Manager Profiles" under JAVASCRIPT
FUNCTIONS for the mechanics.

- ✅ Twelve cards on a new **Managers** sub-tab (the first, and now the default Careers view),
  small with a headline stat, expanding to a full profile on click
- ✅ Profile carries: all-time record, H2H/median split, points for and against, earnings, titles,
  playoff berths, the personal record book (highest/lowest week, biggest blowout, worst defeat,
  closest finish, win/losing streaks, most/fewest points in a season), a standing in all 18 Hall of
  Fame & Shame awards, season-by-season placements and payouts, and every team name used
- ✅ **936 manager names across the site made clickable** — Careers, Scores, Rivalries (both the
  six rivalry cards and the H2H explorer), Rosters, Roster Grades, Draft, Transactions, Stats and
  the Trade Evaluator verdict. Deliberately NOT linked: `<option>` elements in the trade dropdowns
  (an option cannot contain markup), the pick checkboxes in the Trade Evaluator (a button inside a
  `<label>` would toggle the checkbox) and the team filter chips (they already own their click).
  **The six rivalry cards were missed on the first pass** and caught by Matt — they build in
  `buildRivalries()` from `p.a`/`p.b`, separate code from the H2H explorer underneath them.
- ✅ Team-name history for all 12 franchises, 2023–2026, including mid-2026 renames
- ✅ `*` on Andrew Bova with the Chris Jacobs footnote

**Placement decision (Matt, 2026-08-21):** a Careers sub-tab rather than an 11th nav tab, because
every stat on a profile is already a Careers stat and an 11th tab breaks the mobile nav grid. (The nav was cut to five on 2026-08-21; the reasoning held and then some.)

**Verified before shipping, mechanically:**
- Hall of Fame and Record Book output **byte-identical** after refactoring both onto
  `ownerAwardDefs()` — 19 and 12 cards, diffed string by string against a pre-change capture.
  (First diff attempt compared a stale cached page against itself and falsely passed; the second
  compared against the real new build. Watch for that — python http.server 304s aggressively.)
- All 12 profiles reconcile against the rendered Careers table for record and earnings; H2H and
  median ledgers both balance 252/252.
- Click-through from Scores preserves the active tab, scroll position and hash.
- 280/375/1280px, dark and light: zero page overflow, no offenders.

**Not built:** photos are committed as static JPEGs, so a new member needs a file added to
`img/profiles/` and a `photo:` key in `TEAMS`; there is no upload path and shouldn't be.

---

### Phase 7 — Trade Evaluator Enhancements *(substantially complete as of June 2026)*
The June 2026 overhaul completed the core feature set:
- ✅ Live KTC values (HTML parse, CORS proxy chain, 24h cache)
- ✅ Player Values table (sortable/filterable by position + team multi-select)
- ✅ Pick value scaler (-50% to +25%)
- ✅ 2027/2028 future picks only; 2026 picks excluded
- ✅ Clean value totals + verdict output

**Remaining enhancements (optional):**
- Draft ROI view (cross-reference with Phase 3)
- Trade history log (show past trades and what they were worth at the time)
- Roster grade context in trade verdict (win-now vs. rebuild framing)

---

### Phase 12 — Trade ROI + Rookie Draft ROI — **step 1 (data layer) shipped 2026-09-03**

**Goal:** Two new sub-views under the Moves panel: **"Who Won That Trade?"** (a scored card per
trade, every trade in league history) and **"Rookie Draft ROI"** (best-drafter leaderboard +
a hot-spot board showing which draft slots over-deliver).

Both are sub-views of `panel-draft` (Moves), joining Draft and Trades & Waivers. **Not a new
top-level tab** — see the nav-budget rule in WHAT NOT TO DO.

---

#### Feasibility — verified against live Sleeper data 2026-09-03

**Pick → player tracing is exact, not fuzzy.** This was the open question and it is closed.
Each trade's `draft_picks[]` entry carries `roster_id` = the pick's **original** owner (plus
`previous_owner_id` and `owner_id` for the hop). Each draft object carries `slot_to_roster_id`
mapping draft slot → original owner. So:

> `(season, round, original_owner_roster_id)` → the unique pick in that season's draft where
> `round` matches and `slot_to_roster_id[draft_slot] == original_owner` → its `player_id`.

`(round, draft_slot)` was confirmed unique in every draft. Measured result across all 4 seasons:

```
52 trades   (2023: 10 · 2024: 26 · 2025: 9 · 2026: 7)
74 traded pick assets
   58 → resolved to the actual drafted player
   16 → genuine future picks (2027/2028), priced from KTC
    0 → unresolved
```

Do **not** reach for name matching or `pick_no` arithmetic here. `pick_no` is
`(round-1)*12 + draft_slot`, which is *not* contiguous — each season has a lone round-5
consolation bonus pick (2024 pick_no 51 · 2025 pick_no 53 · 2026 pick_no 52), so every draft
has 49 picks with pick numbers running past 48.

**2023 is excluded from rookie ROI because it was not a rookie draft.** It was the 29-round
startup **auction** (348 picks, `metadata.amount` present). 2024/2025/2026 are 4-round linear
rookie drafts, 49 picks each. Rookie ROI universe = 147 picks, of which 98 have played a down.

**Roster 11 changed managers.** CCJ managed it 2023–2025; Andrew Bova took it over in 2026.
Every leaderboard must attribute a move to the **manager at the time of the move**, not the
current roster owner. All other 11 rosters are continuous across all four seasons.

**League chain** (`previous_league_id`): 2026 `1316225642072662016` · 2025 `1196516179326291968`
· 2024 `1048702761132478464` · 2023 `959292811319287808`.

**Trades live in `/transactions/{week}` for weeks 1–18.** Week 0 is empty in all four seasons —
do not bother fetching it. Offseason trades land in week 1 of the upcoming season's league.
Filter on `type == 'trade'` **and** `status == 'complete'`.

---

#### Known data gaps — fix these BEFORE building either page

**1. `stats-history.json` is structurally incomplete for this feature.**
`generate_stats.py` seeds its player list from `/league/{lid}/rosters` — i.e. only players
rostered *at the moment the script ran*. Anyone traded, busted and dropped is missing. Of the
208 players in the trade + rookie-draft universe, 74 have no 2025 season line, and **14 of
those have real 2025 stats on Sleeper**. Those 14 are exactly the population these pages exist
to expose: the busts. Scoring them as 0 would silently flatter whoever traded them away.

The fix: seed the universe from the **union** of (a) every `adds` key in every trade,
(b) every `player_id` in every draft's picks, and (c) every season's rosters — then fetch. Keep
the atomic-write discipline (temp file + `os.replace`, never `open(path,'w')` on a 1.2 MB file).

**2. There is no historical KTC and there never will be.** We only ever snapshot *current*
values, so "what was this worth on trade day" is unrecoverable for past trades. This is why the
score is performance-based rather than value-delta based. Do not try to reconstruct it.

**3. 2026 has zero games played** (season opens 2026-09-09). All 7 of the 2026 trades score
0–0 until real weeks land, and `scripts/tuesday_update.py` does **not** currently extend
`stats-history.json`. Adding 2026 weekly accrual to the Tuesday bot is part of this phase.

---

#### Scoring model — decisions locked 2026-09-03

**Metric: points over replacement (PoR).** Fantasy points via `calcPts()`/`SDATA`, minus what a
replacement-level player at that position produced over the same span. Raw points were rejected
because in a superflex league whoever receives the QB always "wins" — a QB-for-RB trade can read
412 vs 289 on raw points and flip the moment replacement level is applied.

**Replacement ranks are measured, not assumed.** Derived from the actual positional distribution
of started players across 42 real league-weeks (2023–2025, weeks 1–14, `/matchups/{week}`
`starters`), against `roster_positions` = 1 QB / 2 RB / 2 WR / 1 TE / 1 FLEX / 3 WRRB_FLEX /
1 SUPER_FLEX (11 starters, 12 teams):

| Pos | Avg started per league-week | Replacement |
|-----|-----------------------------|-------------|
| WR  | 55.6 | **WR57** |
| RB  | 37.0 | **RB38** |
| QB  | 22.2 | **QB23** |
| TE  | 17.0 | **TE18** |

Compute replacement **per position per week**, not per season — that is what absorbs bye weeks
and injury weeks correctly. Baselines must be computed over the **full NFL player pool** from
`/stats/nfl/regular/{y}/{w}`, not over `stats-history.json` (which only holds league-relevant
players and would put replacement level far too high). Bake the result into a small
`replacement-levels.json` keyed `year → week → position → points`.

**Credit rule (v1): points credit to the trade forever.** All points a player scores after the
trade date count toward that trade, whether or not the acquirer kept him. This is the pure "who
got the better asset" reading and the math is unarguable. Two richer rules were considered and
deferred: *realized value* (stop the clock when the acquirer gives him up — needs week-by-week
roster reconstruction from the transaction log) and *chaining* (B's return becomes whatever B
later got for the player, recursively). Chaining is the most interesting version of this page;
build it as Phase 12b on top of a working v1, not instead of one.

**Window.** Start = trade `created` (ms epoch) mapped to (season, week); offseason trades start
at week 1 of the coming season. End = today, recomputed on every page load — that is what makes
the page "continually update" for free, with no stored scores to go stale.

**Score shape: margin + verdict chip.** Each side's PoR total, the margin, and a verdict:
`DEAD EVEN` / `EDGE` / `CLEAR WIN` / `ROBBERY`. Thresholds should combine an absolute PoR floor
with a relative gap so a tiny two-bench-player swap can never earn `ROBBERY`. No 0–100 score
(the normalization would be arbitrary and would move the argument onto the formula) and no
letter grades (they hide the margin — a blowout and a squeaker both read as A/C).

**Maturity gate.** Cumulative PoR is the honest answer to "who won," but a 2024 trade has two
seasons of payout and an August 2026 trade has none. Every card carries a maturity meter (weeks
elapsed + games played by its assets), and a trade under the threshold gets a **TOO EARLY TO
CALL** stamp *instead of* a verdict — never a verdict computed off three games. Any trade still
holding an undrafted 2027/2028 pick is automatically unsettled.

**Picks, and the units problem.** KTC values are in the thousands; PoR is in the hundreds. They
cannot be summed. Resolve it with an **empirical pick curve built from this league's own
history**: for each rookie draft slot, the average PoR its selection has produced (2024 + 2025
classes). An unresolved future pick converts to expected PoR through that curve, rendered in a
visually distinct "projected" treatment so nobody reads it as earned points. Use KTC only to
*rank* an unresolved pick's likely slot, never as a score term directly. This curve is shared
with the Rookie Draft ROI view, which keeps the two pages consistent by construction.

**FAAB.** Only 2 of 52 trades moved waiver budget. Display it on the card; do not attempt to
score it. There is no defensible FAAB→points conversion at this sample size.

---

#### Rookie Draft ROI view

Scored off the same PoR engine and the same pick curve.

- **Best drafter** = Σ (actual PoR − expected PoR for that slot) across every pick a manager
  made, attributed to the manager at the time of the pick. Show per-class and all-time.
- **Hot spots** = a round × slot board heat-mapped by average PoR-over-expected, answering
  "where in this draft does value actually hide."
- **Draft capital board** — what a pick at each band actually buys: hit rate, median
  PoR, `usage_pct`, and crucially `avg PoR given a role`. See "Draft capital,
  opportunity and class strength" below; this is a required part of the view, not a
  nice-to-have. Reporting a late pick's PoR without its opportunity invites the wrong
  conclusion in both directions.
- **Show pooled AND class-adjusted** over/under-expectation per manager.
- **Sample-size honesty is mandatory on this view.** Only 2 classes (98 picks) have played:
  2024 has two seasons, 2025 has one, 2026 has none. With a sample this thin, fit a smooth
  decay curve across all picks rather than using raw per-slot averages — a raw slot average over
  two observations is noise. Say so on the page; do not present a 2-pick cell as a finding.

---

#### Build order

1. ~~**Data layer.**~~ **Done 2026-09-03.** See "Step 1 as built" below.
2. ~~**`scripts/build_trade_roi.py` → `trade-roi.json`.**~~ **Done 2026-09-04.**
   See "Step 2 as built" below.
3. ~~**Moves > Who Won That Trade?**~~ **Done 2026-09-04.** See "Step 3 as built" below.
4. ~~**Moves > Rookie Draft ROI** + hot-spot board.~~ **Done 2026-09-04.** See "Step 4 as built".
5. ~~**Tuesday bot extension**~~ **Done 2026-09-03** — pulled forward ahead of items 2-4 because
   the season opens 2026-09-09. See "Step 5 as built" below.

**Complexity: High.** The data layer is the majority of the work and the only part that is hard
to get right; both views are rendering once it exists.

---

#### Step 1 as built (2026-09-03)

`stats-history.json` regenerated, `replacement-levels.json` created, both committed.

**Universe widened, verified against the old file.** 2023 346→391 players, 2024 342→423,
2025 340→441; file 1.21→1.32 MB. **Zero regressions** — every player and every stat value in
the previous file is present and identical in the new one. 10 players were recovered into 2025
alone (Sterling Shepard, Khalil Herbert, Isaac Guerendo, Malachi Corley, Cade Stover, Tyler
Conklin, Jamari Thrash, Mason Rudolph, Jarrett Stidham, Mecole Hardman).

A further 6 traded/drafted players stay absent **and that is correct**: Sleeper returns only
`gms_active` and `pos_rank_*` for them, with no production of any kind. There is no stat line
to score, and absence already reads as zero. Do not "fix" this by inventing rows for them.

**`pass_int_td` was added to `STAT_KEYS`.** `calcPts()` has always read it (pick-six thrown,
−1) but the generator never wrote it, so the site could not score it. Now collected.

**The live season is omitted from the file entirely, on purpose.** `fetchWeekStats()` treats
the mere *presence* of a week key as data — it does not check whether the object is empty — and
then `savePerm()`s the result forever. A written-out `"2026":{"weeks":{"1":{}}}` would have
pinned every player to zero for the whole live season, permanently, per visitor. `generate_stats.py`
now omits empty weeks and omits a year with no played weeks. Keep it that way.

**Replacement baselines.** `replacement-levels.json` (2.6 KB) holds year → week → position →
points, from a 5-player band centered on the replacement rank rather than a single rank, because
one boom game by the exact Nth player would otherwise swing every PoR figure that week. Season
means came out QB 10.2–11.1 · TE 9.0–9.5 · RB 5.9–6.8 · WR 6.3–6.4 — stable across all three
seasons, TE above RB/WR as the 0.5/catch TE premium and a 12-team TE pool imply.

Baselines are computed over the **whole NFL pool** from `/stats/nfl/regular/{y}/{w}`, never over
`stats-history.json` — that file is already filtered to league-relevant players and ranking
inside it would set replacement far too high.

**Scoring parity is verified, not assumed.** `calc_pts()` in `build_replacement_levels.py` was
checked field-by-field against `calcPts()` and `SDATA` in `index.html`, *and* against the live
`scoring_settings` from the league API: 27 keys, zero differences, no field read by one and not
the other. If you touch either scorer, re-run that check.

**PoR does what it was chosen to do.** 2025 raw-points top 12 contains 5 QBs with Josh Allen
2nd; the PoR top 12 contains 1 QB with Allen 7th, led by McCaffrey / Nacua / Taylor / Robinson.

**One inherent 0.1 discrepancy, do not chase it.** PoR sums per-week `calcPts` (each rounded to
1dp, because replacement is weekly), while the Player Stats table rounds the season aggregate
once. McCaffrey 2025 is 383.5 by the first method and 383.4 by the second. That is rounding, not
a bug, and the weekly method is the correct one for PoR.

**`measure_starter_mix.py` needs the played-week guard.** Its first run reported 56 league-weeks
and WR 53.7, because Sleeper serves `starters` for unplayed 2026 weeks that managers have already
set lineups for — the same "an unplayed week is not an absent week" trap that once booked phantom
losses into the median math. Gated on `points > 0` it reproduces 42 league-weeks and
QB 22.2 / RB 37.0 / WR 55.6 / TE 17.0 exactly.

---

#### Step 2 as built (2026-09-04) — the PoR engine

`scripts/build_trade_roi.py` → `trade-roi.json` (104 KB, committed). All 52 trades
expanded, all 147 rookie picks scored, the pick curve fitted, verdicts assigned.

**The engine reconciles by hand.** Baker Mayfield from the 2023-10-30 trade:
PoR 345.6, raw 778.0, 41 weeks — identical to an independent recomputation straight
off `stats-history.json` + `replacement-levels.json`. Pick tracing spot-checked the
same way (2025 R2 originally roster 1 → pick 16, slot 4 → Luther Burden).

**PoR is floored at zero per asset, and this is the single most important decision
in the file.** 31% of traded assets score negative before the floor, some past -60
(Cade Stover -78 as a 4th-round rookie TE, Mecole Hardman -65). Nobody ever started
those players. A rostered asset's true floor is zero, because a manager benches a
bust rather than paying a replacement-level penalty every week — and scoring the raw
negative made **dumping** a bust register as a +65 win for the team that gave him
away, which inverts the whole question the page asks. `por_signed` keeps the real
number for display (a BUST tag reads off it); it never enters a margin.

**A week counts only when the player recorded something scoreable.** A bare `gp`
line means he dressed and did nothing, which is a benched player, not a cost. Weeks
he missed contribute nothing — availability is already captured, because PoR is a
cumulative sum and a player who misses six games simply banks six fewer weeks.

**Four trades are reversals and get no verdict.** Ja'Marr Chase moved roster 10 → 8
and straight back **17 minutes later**, the same 2025 3rd going the other way each
time; Jaylen Wright the same across 14 hours. Distinct `transaction_id`s, so nothing
upstream dedupes them, but scoring both halves publishes two mirror-image ROBBERY
verdicts and tells the league that two managers each robbed the other on the same
afternoon. `find_reversals()` matches a later trade whose asset flows are the exact
inverse of an earlier one between the same rosters inside 48h.

**Thresholds were set from the real distribution, not picked in the abstract.**
Absolute |margin| percentiles across the 52 trades: p25=0, p50=27, p75=93, p90=166,
p100=346. Hence `EDGE 25` (just under the median), `CLEAR 75` (~p75),
`ROBBERY 150` (~p90) — plus a **3× ratio gate** on ROBBERY so a blowout where both
sides got real value stays a CLEAR WIN. A 390-vs-107 trade is lopsided, but the
loser still got a starter, and spending the word "robbery" there devalues it for the
trades where someone genuinely got nothing. Maturity gate is 8 scored weeks (~p25,
about half a season from the busiest asset).

Result: **33 of 52 graded** — DEAD EVEN 12, EDGE 10, CLEAR WIN 9, ROBBERY 2.
Withheld: 15 TOO EARLY TO CALL (10 still hold an undrafted pick, 5 too new), 4
REVERSED. Both robberies are genuinely lopsided (Baker Mayfield for what became
Javon Baker; Josh Jacobs + a pick that became Tetairoa McMillan for Rome Odunze + a
pick that became Jaylin Noel).

**The pick curve is fitted, not averaged.** Only 2 classes (98 picks) have played, so
a raw per-slot average is the mean of two observations. `build_pick_curve()` smooths
over a ±6-pick window then clamps monotone-decreasing, so a noisy pair at pick 9
cannot make pick 9 worth more than pick 3. Round averages get the same clamp and it
matters: raw they were `{1: 96.3, 2: 29.6, 3: 4.6, 4: 14.0, 5: 42.2}` — round 5 is
**two picks** (Trey Benson, Jaxson Dart) and round 4 is carried by Bucky Irving, so
untreated a traded 2027 4th would have priced above a 2027 3rd. Clamped:
`{1: 96.3, 2: 29.6, 3: 4.6, 4: 4.6, 5: 4.6}`.

Rookie-year PoR is the curve's basis rather than career PoR, so a 2024 pick cannot
out-rank a 2025 pick purely on having had an extra season to accumulate.

**Aggregate every leaderboard on `manager_index` (user_id), never on display name.**
Roster 9 is one human under two names — Mblack2889 in 2023/24, MJBlack from 2025 —
and keying on the name split his draft record across two rows and ranked him twice.
Roster 11 is the opposite trap and must not be merged: CCJ 2023-25, Andrew Bova from
2026, two people on one roster_id. Every row therefore carries the manager resolved
for **its own season**, and `manager_index` carries the canonical name plus
`names_seen` so an old row can be captioned with the name current at the time.
13 entries for 12 rosters, which is the correct count.

**First look at the output, for reference when the view is built.** Best drafter by
Σ(actual − expected) over the 2024+2025 classes: cbova1222 +380 (Bo Nix 237.5 and
Jayden Daniels 219.0, the two best rookie seasons in league history), jblack511 +245,
CHRISMERKELDUH +179; avobttam −150 and MJBlack −145 at the bottom. Face-valid.

**Bot wiring done 2026-09-04** — the Tuesday workflow now rebuilds all three data files in
dependency order every week. See "Automation (Tuesday Bot)" for the chain and the silent
failure mode `coverage_gaps()` exists to prevent.

---

#### Draft capital, opportunity and class strength (2026-09-04)

Matt's question: a pick's production should be read against its draft capital,
because "rounds 3 and 4 are given 0 chance whereas a top 3 pick might have been an
easy pick to make." Three things came out of testing that against the data, and all
three are now in `trade-roi.json`.

**The claim is right in outcome and wrong in mechanism, and the difference matters.**
Late picks are not benched — only 3/24 round-3 and 4/26 round-4+ picks never recorded
a scoreable week, and most had at least one week above replacement. What collapses is
**volume and quality together**:

| Band | n | hit rate | median PoR | usage pct | never used | got a role | avg PoR *given* a role |
|---|---|---|---|---|---|---|---|
| 1.01–1.03 | 6 | 83% | 118.8 | 85% | 0/6 | 6/6 | 123.5 |
| 1.04–1.06 | 6 | 83% | 99.8 | 82% | 0/6 | 6/6 | 108.2 |
| 1.07–1.12 | 12 | 67% | 72.0 | 61% | 1/12 | 10/12 | 89.8 |
| Round 2 | 24 | 12% | **0.0** | 46% | 0/24 | 21/24 | 33.8 |
| Round 3 | 24 | 4% | **0.0** | 34% | 3/24 | 16/24 | 6.9 |
| Round 4+ | 26 | 12% | **0.0** | 37% | 4/26 | 18/26 | 23.0 |

The **median rookie PoR in rounds 2, 3 and 4 is 0.0** — the typical pick after round 1
returns nothing at all. But note round 2: 21 of 24 got a real role and it still only
hit 12% of the time, and the `avg PoR given a role` column keeps falling long after
the opportunity gap closes. **So opportunity explains part of the cliff, not all of
it.** Do not let the page claim late picks merely "never got a chance" — they got a
smaller chance and were worse with it. Both columns are published for that reason.

"Top 3 is an easy pick" holds up (83% hit rate at 1.01–1.06) but is not free: Cameron
Ward at 1.03 returned 10.2 and Travis Hunter at 1.06 returned 9.9.

**`usage_pct`, not raw touches, for any cross-band claim.** Raw touches first reported
the 1.01–1.03 band at 384 against 75 for 1.04–1.06, which reads as the top three picks
getting five times the opportunity. They were not — that band happened to hold Caleb
Williams, Jayden Daniels and Cameron Ward, and a quarterback's pass attempts dwarf a
running back's carries. `Engine.usage_percentile()` ranks a player within his own
position and season; raw `touches` is kept only for a single player's own card.

**Class strength is a real confound and is now adjusted for.** The 2024 class produced
**2.39x** the total PoR of 2025 (2506 vs 1048); round 1 alone averaged 135.8 against
56.9. Both are measured over one rookie season each, so that is class quality, not one
class having had longer to accumulate. `class_factors` (2024: 1.41, 2025: 0.59) scales
each pick's expectation to the class it was actually made in, published on every row as
`expected_por_class_adj` beside the pooled `expected_por`.

It changes less than it looks: ranks move by at most one place. The one interpretive
flip is jhayes3134, −20 pooled to **+24** class-adjusted, i.e. from slightly below
expectation to slightly above once he stops being charged for drafting in the weak
year. Keep both numbers on the page — pooled answers "what did you actually get",
class-adjusted answers "did you draft well for the year you were in".

**Every rookie row now carries `opportunity`**: `weeks_dressed`, `weeks_used`,
`weeks_startable`, `touches`, `usage_pct`, `got_role` (6+ scoreable weeks). That is what
separates a bad landing spot from a bad evaluation — a pick that got 40 touches and
failed is not the same mistake as one that got 200 and failed, and a single PoR number
cannot tell them apart. Bucky Irving (2024 4.06) is the reference case: expected 2.3,
actual 176.4, usage percentile 81%, 16 of 16 weeks used.

---

#### Step 4 as built (2026-09-04) — the Draft ROI view

Fourth sub-view of Moves (`#moves-view-drafteval`, label **Draft ROI**), lazy-loaded, off the
same `trade-roi.json`. Deep links: `#draftroi`, `#bestdrafter`. Four Moves sub-views is within
budget — History runs five, and five is the ceiling.

**Functions:** `buildDraftEval()`, `renderDraftEval()`, `deDrafterRows()`, `deDrafterTableHtml()`,
`deCapitalHtml()`, `deHotspotHtml()`, `deBestWorstHtml()`, `dePlayedPicks()`, `deExpectedFor()`,
`setDraftEvalBasis()`. CSS in the appended `MOVES TAB — DRAFT ROI` layer (`.de-*`).

**Five blocks:** Best Drafter (ranked by actual minus expected, with a magnitude bar), What A
Pick Is Actually Worth (the `draft_capital` bands), Where The Value Hides (a round x slot heatmap,
teal above the slot's price and magenta below, each cell titled with the actual players), Steals
and Reaches (top and bottom five picks against expectation), and a sample-size caveat block.

**The basis toggle is the point of the view, not a setting.** "Adjusted for class strength"
measures a manager against the year he actually drafted in; "Raw" measures what he got. The
2024 class produced 2.39x the 2025 class, so the two answer genuinely different questions and
both are honest — which is why neither is hidden. Switching them reproduces the rank shuffle the
builder predicted (Bogardus and Merkel swap 3rd/4th; Hayes moves from -20 raw to +24 adjusted).

**A specificity bug worth remembering.** `.de-pos` / `.de-neg` set the color on the vs-expected
column, but `.de-tbl td` is (0,1,1) against a bare class's (0,1,0), so the entire column rendered
in body color in both themes — the one column a reader scans for a sign. Fixed by qualifying as
`.de-tbl td.de-pos`. It was invisible in a screenshot and only turned up in `getComputedStyle`;
**check computed color, not the picture, when a themed value looks flat.**

**Verified:** all 12 drafter rows match the builder's own numbers exactly, real names resolved
through `TEAMS` with `ownerLink()` throughout, zero console errors on a clean tab, tables scroll
inside their own `.dtblwrap` at 375px with zero page overflow, and both themes correct
(dark `#21F5E4`/`#FF3DBE`, light `#0E9C92`/`#D6258F`).

**A measurement trap, not a layout bug.** An overflow check reported 184px on a tab whose
`clientWidth` was **0** — the Browser pane had backgrounded the tab, so nothing was laid out and
every element "overflowed". Always assert the viewport is non-zero before trusting an overflow
number; forcing an explicit `resize_window` size is the reliable fix.

---

#### Step 3 as built (2026-09-04) — the Who Won That Trade? view

Third sub-view of Moves (`#moves-view-roi`), lazy-loaded, rendering entirely from the
committed `trade-roi.json`. No live API calls and no KTC on this view at all.

**Functions:** `loadTradeROI()` (hourly cache-buster, memoized in `_tradeROIPromise`),
`buildTradeROI()`, `renderROICards()`, `roiCardHtml()`, `roiAssetHtml()`, `roiManager()`,
`roiSummaryHtml()`, `toggleROIHow()`, `setROIFilter()`, `buildROITeamChips()`,
`toggleROITeam()`. CSS lives in the appended `MOVES TAB — WHO WON THAT TRADE?` layer
(`.roi-*` / `.ra-*`), per the redesign convention.

**The card:** date + verdict chip, then one block per side — manager, PoR total, and the
assets, with a teal left rail and teal total on the winner. Assets carry position, a
`via 2025 R1` tag when they arrived as a traded pick, a `BUST` tag when `por_signed < -25`,
and an italic `~30 proj` treatment for a pick that has not been drafted yet so nobody reads
a projection as earned points. Footer gives the margin and the weeks of evidence behind it.

**A summary strip sits above the filters** with the verdict spread and a collapsible
*"How is this scored?"* explainer. That explainer is not optional decoration: this view
publishes a number that calls someone's trade a robbery, so the four things that would
otherwise start an argument — points over replacement, the zero floor on busts, picks
counting as the player taken, and scores being recomputed live — are stated in plain
English on the page itself, with the actual thresholds quoted from `trade-roi.json`.

**`shortName()` does not exist** — this view's chip bar called it on the strength of the
VISUAL THEME note and threw a live `ReferenceError`. That note is now corrected; the real
function is `abbrev()`. Manager names on both the chips and the cards resolve through
`TEAMS`/`t(uid)` to the **real** name, falling back to the Sleeper handle stored in
`trade-roi.json` only for a manager no longer in `TEAMS` (CCJ). Every name goes through
`ownerLink()`, so all 99 of them open a profile.

**Verified in-browser:** 52 cards on All Trades and 33 on Graded (matching the builder),
zero console errors on a clean tab, zero page overflow at both 375px and desktop, light mode
inheriting the palette correctly (teal `#0E9C92`, magenta `#D6258F`) with the neon glows
present in dark and absent in light. `?v=`-style verification needs a **fresh tab or a
cache-busted URL** — `python http.server` 304s aggressively and served the pre-fix page three
times while the file on disk was already correct.

---

#### Step 5 as built (2026-09-03) — live-season accrual

Pulled forward ahead of items 2-4: the season opens 2026-09-09, and until this runs the live
season stays absent from `stats-history.json` entirely, so every 2026 trade would score 0-0
no matter what happened on the field.

**`generate_stats.py` gained three things**, all of which exist because it now runs unattended:

- **`--live-only`.** Copies completed seasons through from the existing file and rebuilds only the
  in-progress one. A weekly full rebuild would re-fetch ~51 weeks that can never change, and would
  put three years of good data at the mercy of one flaky request every single Tuesday.
- **`check_no_data_loss()`.** A hard gate before writing: refuses to publish an output that drops a
  season, drops any week from a season, or loses more than 5% of a season's players. **Tested by
  simulating a 503 on week 7** — the run aborts with exit code 1 and the file is byte-identical
  afterwards. `build_season()` also refuses to return a season with any failed week, so a hole can
  never reach the merge in the first place.
- **`__file__`-relative paths.** It wrote to a bare `'stats-history.json'`, so it only worked when
  invoked from the project directory; the workflow runs from the repo root.

**A real bug the safety gate caught on its first live test.** `get_league_chain()` walked the
chain with a *loop counter* rather than each league's own season, so calling it for any season
other than 2026 truncated the chain and dropped the 2023 league's rosters from the player
universe — 2025 rebuilt to 401 players instead of 441. The gate blocked the write and named the
number. The walk is now keyed and terminated on `info['season']`. **This is the gate justifying
itself on day one; do not remove it as belt-and-suspenders.**

**`loadStatsHistory()` gained the hourly cache-buster** (`?_=`+hour) that `loadProjectionsFile`,
`loadCommentary` and the rest already used. This file changed roughly once a year until now; from
this week it changes weekly in-season, and a browser-cached copy would hold the live season a week
behind.

**The workflow itself was broken and had never run** — see Automation (Tuesday Bot) for the full
finding and the two rules that came out of it. Short version: a multi-line `python -c` at column 0
inside a `run: |` block made the entire file invalid YAML from the day it was written.
`deploy-pages.yml` also had to gain the Tuesday workflow in its `workflow_run` chain, because the
bot now commits a file the site actually fetches.

**Verified end to end:** all five workflow files parse; `--live-only --dry-run` runs correctly from
the repo root and writes nothing; a simulated live season *with* data (2025) rebuilds to the same
441 players / 17 weeks with no loss; a simulated API failure aborts and leaves the file untouched;
the `WEEK=` one-liner resolves `?` on an empty state and `3` on `[1,2,3]`; and in-browser the site
requests `stats-history.json?_=496799`, renders 441 rows, and logs no new errors.

**Still to check on 2026-09-15** (the first Tuesday with real 2026 data): that the run adds a
`"2026"` block with week 1 only, that the deploy chain fires, and that the Player Stats tab is
unaffected — the live season renders through `build2026Stats()` off the live API and never reads
`stats-history.json`, so it should be untouched either way.

**Unrelated drift noticed while verifying, not acted on:** the Phase 6 console report now says
*"Unmatched KTC report — 3 player(s) across all 12 rosters"*, where CLAUDE.md records 0 as of
2026-08-20. Possibly just the local run falling back to the committed `ktc-values.json` after the
live scrape 403s. Worth a look before the next grading period.

---

## WHAT NOT TO DO

- Do not introduce React, Vue, npm, or any build tool
- Do not break the single-file structure
- Do not remove the CORS fallback chain
- Do not add back `getTradeAI()` or AI scoring dimensions to the Trade Evaluator — the June 2026 overhaul replaced them with KTC values intentionally
- Do not remove the `.cache-bar` DOM or its child IDs — they are used programmatically by `setCacheBar()` and `refreshData()`
- Do not revert the Arcade Neon palette/type (teal #21F5E4 · magenta #FF3DBE · purple #9A55FF on #06060C, Saira Condensed display) — see VISUAL THEME. The redesign lives in appended, banner-commented CSS layers at the end of `<style>`; style by class + variables.
- Do not use DM Mono for main content — it belongs only for intentional code/timestamp contexts
- Do not add the consolation winner card back to the home panel
- Do not put a text block back beside the header banner - it already reads "THE OTHER LEAGUE"
- Do not apply `drop-shadow()` to `.hdr-logo` while the banner is an opaque JPEG - see Logo Files
- Do not add the sidebar back without explicit request
- Do not add a sixth top-level nav tab — see the nav-budget rule under KEY DESIGN DECISIONS. Build it as a sub-view.
- Do not remove a `TAB_ALIASES` entry. They are the only thing keeping links already texted around the league from landing on a blank page.
- Do not put a secret, an API key or anything you would mind the league reading behind the Commissioner gate — it is a doorknob lock on a public site, and the whole file is public source.
- Do not remove the `commishStopTimer()` call in `showTab` — the monitor's poll would keep re-fetching every data file in the background for the life of the session.
- Do not give the Commissioner a nav tab. It is a panel with no button precisely so the nav stays at five; see the nav-budget rule.
- Do not restore the Rules panel, `buildScoring()` or `SLABELS` — deleted 2026-08-21 as a restatement of what Sleeper shows. `SDATA` is NOT part of that deletion; it feeds `calcPts()` and every point figure on the site.
