# CLAUDE.md — The Other League Dynasty Dashboard

## WHAT THIS PROJECT IS

A personal fantasy football dashboard for "The Other League" — a 12-team dynasty league on the Sleeper platform. The site pulls live data from the Sleeper public API to display rosters, league history, draft picks, scoring rules, rivalries, and a trade evaluator with live KTC values.

**Commissioner:** Matt Bova. Built for personal use, shared with league mates via GitHub Pages.

---

## PROJECT STRUCTURE

This is a **static HTML/JavaScript project** — no framework, no build step, no package manager. All files are plain `.html` with embedded CSS and JavaScript.

```
the-other-league/
├── CLAUDE.md                          — you are here
├── index.html                         — 8-line stub that redirects to the-other-league-FINAL.html
├── the-other-league-FINAL.html        — THE working file (3300+ lines, all logic embedded)
├── the-other-league-context.md        — master league context document
└── chunks/                            — prior standalone chunk files (reference only)
```

**Current state:** `the-other-league-FINAL.html` is the **only** file to edit. It contains all HTML, CSS, and JavaScript in one file.

**Deployment:** GitHub Pages (static hosting). Push to `main` → site updates automatically.

---

## EXTERNAL APIS

### Sleeper API (no auth required)
- Base: `https://api.sleeper.app/v1`
- League ID: `1316225642072662016`
- Key endpoints:
  - `/league/{lid}` — league info
  - `/league/{lid}/rosters` — all 12 rosters
  - `/league/{lid}/traded_picks` — pick trade log
  - `/league/{lid}/matchups/{week}` — matchup scores for a given week
  - `/league/{lid}/transactions/{week}` — transactions for a given week
  - `/league/{lid}/drafts` — drafts list
  - `/draft/{draft_id}/picks` — picks for a draft
  - `/players/nfl` — full player database (~5MB, slow)
- CORS note: Direct browser fetch may fail. Fallback proxies in order: `corsproxy.io`, `api.allorigins.win`

### Anthropic API
- Used **only** by `getTradeAI()` inside the Trade Evaluator panel
- The "Ask Claude" tab was removed from the UI (panel and icon tab are gone)
- `sendAI()`, `addMsg()`, `clearChat()`, `aiMessages`, `LEAGUE_CONTEXT`, `QUICK_PROMPTS` remain in JS because `getTradeAI()` calls them — do not delete them

---

## NAVIGATION STRUCTURE

### Sticky Shell
`<div class="sticky-shell">` uses `position: sticky; top: 0; z-index: 100`. It contains:
1. `<header>` — logo (home link) + "Open in Sleeper" pill + dark mode toggle
2. `<nav class="icon-nav">` — 9 icon tabs + 1 refresh button

The header logo (`<div class="hdr-logo-link">`) calls `showTab('home')` on click — it IS the home button.

### Icon Nav
Each tab is `<div class="icon-tab" onclick="showTab('id',this)" data-tab="id">` with an emoji icon and text label. The active tab gets `class="active"` and a teal bottom border.

The Refresh button at the end is `<div class="icon-tab nav-refresh-btn" onclick="refreshData()">` — styled with a left border separator; it never gets the active class.

### URL Hash Routing
`showTab(tab, el)` calls `history.replaceState(null,'','#'+tab)`. On boot, `routeFromHash()` reads `location.hash` and navigates to the matching tab. `hashchange` event is also wired. Valid tab IDs are in `VALID_TABS` array in JS.

### `body.is-home` CSS Class
`document.body.classList.toggle('is-home', tab==='home')` — set in HTML on `<body class="is-home">` at load, toggled in `showTab()`. CSS rules under `body.is-home` hide the sidebar, cache bar, and utility strips, and give the home panel edge-to-edge layout.

### Tabs and Panels

| Icon | Tab Label | `showTab` ID | Panel ID | Lazy load? |
|------|-----------|--------------|----------|-----------|
| (logo click) | Home | `home` | `panel-home` | No — static HTML with countdown JS |
| 📊 | Careers | `careers` | `panel-careers` | Yes — `buildCareers()` on first visit |
| ℹ️ | League | `league` | `panel-league` | No — static HTML |
| ⚔️ | Rivalries | `rivalries` | `panel-rivalries` | Re-renders every visit via `buildRivalries()` |
| 🏈 | Scores | `scores` | `panel-scores` | Yes — `buildScores()` on first visit |
| 📋 | Rosters | `rosters` | `panel-rosters` | No — loaded at boot via `init()` |
| 📈 | Stats | `stats` | `panel-stats` | Yes — `buildPlayerStats()` on first visit |
| 🎯 | Draft | `draft` | `panel-draft` | Yes — `buildDraft2026()` at boot; past years on demand |
| 🔄 | Transactions | `transactions` | `panel-transactions` | Yes — `buildTransactions()` on first visit |
| ⚖️ | Trade Eval | `trade` | `panel-trade` | Yes — `initTradeEval()` on first visit |
| ↺ | Refresh | — | — | Calls `refreshData()` directly; not a panel tab |

**Removed tabs:** "Ask Claude" (`ai` / `panel-ai`) was removed from the UI. The underlying JS functions are kept because `getTradeAI()` uses them.

### Home Panel (`panel-home`)
Contains:
- `TOL Large Logo.png` as hero image with neon glow (`.home-hero-logo`)
- NFL Season countdown to Sep 10, 2026 8:20 PM ET — `startCountdown()` function, IDs: `cd-days`, `cd-hours`, `cd-mins`, `cd-secs`
- 2025 Champion card: Jake Blackwell / "Nacua Matata" / Pick 1.12
- League meta pills: Commissioner · Matt Bova, Est. · 2023, Dynasty · 12 Teams

**Removed from home panel:** Consolation winner card (Nick Merkel), Quick-nav grid (replaced by icon nav)

### Careers Panel (`panel-careers`)
Contains:
1. Section title "LEAGUE LEADERS" + subtitle
2. `.career-status-bar` — the perpetual stats bar (7 `.s-pill` items) — **lives here, not globally**
3. `#careers-container` — career stats table + per-season standings tables (built by `buildCareers()`)

The perpetual stats bar was formerly a global `.status` div shown above all panels. It was moved inside this panel so it only appears on the Careers tab.

---

## REMOVED / HIDDEN ELEMENTS

- **Sidebar** (`.sidebar`) — `display: none !important` — the All Teams team list is gone. `buildSidebar()` and `scrollToTeam()` still exist in JS but sidebar is invisible.
- **Cache bar** (`.cache-bar`) — `display: none !important` inline style — the "Cached data · Last fetched Xm ago · Refresh" row is hidden. The DOM elements and IDs (`cache-dot`, `cache-status-txt`, `refresh-btn`) still exist in the HTML so `setCacheBar()` and `refreshData()` work correctly.
- **Sleeper bar** (`.sleeper-bar`) — removed from HTML. "Open in Sleeper" link moved to the header.

---

## KEY ELEMENT IDs

### Header
- `t-icon`, `t-lbl` — theme toggle icon and label
- `cache-dot` — colored dot (live vs cached) — inside hidden `.cache-bar`
- `cache-status-txt` — cache status message — inside hidden `.cache-bar`
- `refresh-btn` — original refresh button — inside hidden `.cache-bar`; `refreshData()` still uses it programmatically

### Perpetual Stats (inside `panel-careers`)
- `stat-champs` — past champions list
- `stat-earn-val`, `stat-earn-sub` — highest career earnings
- `stat-wins-val`, `stat-wins-sub` — most career wins
- `stat-cons-val`, `stat-cons-sub` — most consistent finisher
- `stat-picks-val`, `stat-picks-sub` — most draft picks
- `stat-trades-val`, `stat-trades-sub` — most trades completed
- `stat-worst-val`, `stat-worst-sub` — worst average finish

### Scores Panel
- `scores-container` — main scores area

### Rosters Panel
- `rosters-container` — roster grid (12 `r-card` divs)
- `roster-card-{uid}` — individual roster card per team

### Rivalries Panel
- `rivalry-grid` — rivalry matchup cards

### Draft Panel
- `draft-view-2026`, `draft-view-past`
- `d26-list-view`, `d26-board-view`, `d26-tbody`
- `draft-history-container`

### Player Stats Panel
- `stats-yr-toggle`, `stats-pos-filter`, `stats-wk-filter`, `stats-container`

### Transactions Panel
- `txn-container`, `txn-yr-toggle`, `txn-filter-bar`, `txn-team-filter`, `txn-player-search`, `txn-player-results`

### Careers Panel
- `careers-container` — career stats table + season standings

### Trade Evaluator Panel
- `ktc-badge` — shows live vs snapshot KTC values status

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

### Stats Banner (Perpetual Stats)
- `buildLeaderStats()` — computes and renders all 7 perpetual stats from `SEASON_HISTORY` + cached pick/transaction data. Called at boot and after each background data fetch. Targets IDs inside `panel-careers`.

### Careers
- `buildCareers()` — calls `buildLeaderStats()` to refresh pills, then builds the career earnings/placement table and per-season standings tables

### Scores Tab
- `buildScores()` — entry point: checks live vs off-season
- `renderScoresOffseason(c)` — shows 2025 final standings
- `renderScoresWeek(container, week)` — renders matchup cards with H2H records
- `changeScoreWeek(week)` — prev/next week handler

### Rosters
- `buildRosters(rostersData, playersData)` — renders 12 roster cards with position-colored player chips

### Rivalries
- `buildRivalries()` — renders 6 rivalry cards; re-renders on every tab visit

### Player Stats
- `fetchPlayerStats(year)` / `fetchWeekStats(year, week)` — fetches and caches stat data
- `calcPts(stats, pos)` — calculates fantasy points using `SDATA`
- `buildPlayerStats(year, posFilter)` — renders stats table
- `setStatsYear()`, `setStatsWeek()`, `setStatsPos()` — filter handlers

### Transactions
- `fetchTransactions(leagueId, year)` — fetches and permanently caches past transactions
- `buildTransactions(filter, year)` — renders filtered list
- `runPlayerSearch(query)` — searches all seasons + draft history for a player

### Draft
- `buildDraft2026()` — renders 2026 linear draft order (same order every round, not snake)
- `buildDraftHistory(year)` — fetches and renders past draft results

### Tab Navigation
- `showTab(tab, el)` — activates tab + panel; triggers lazy-load on first visit; toggles `body.is-home`; updates URL hash

### Trade Evaluator
- `initTradeEval()` — lazy-init: populates team dropdowns, kicks off `fetchKTCValues()`
- `fetchKTCValues()` — tries live KTC JSON; falls back to `KTC_SNAPSHOT` if < 50 players returned
- `evaluateTrade()` — computes value delta using KTC values, renders result card
- `getTradeAI(giveUid, receiveUid)` — calls Claude API with trade details

### Boot
- `startCountdown()` — countdown timer to Sep 10, 2026 8:20 PM ET; ticks every 1s
- `routeFromHash()` — reads `location.hash` on boot and navigates to matching tab
- `init()` — boot sequence: loads/caches rosters, builds leader stats, prefetches historical data in background

---

## DATA OBJECTS

### `TEAMS` — static team registry
```javascript
// user_id → { name, team, you, tier, note?, co? }
```
`you: true` marks Matt Bova's team. `co` is for co-owned teams.

### `RM` / `RMR` — roster ↔ owner mapping
```javascript
const RM = { 1: '721908735856967680', ... };  // roster_id → user_id
const RMR = {};  // user_id → roster_id (computed at boot)
```

### `RIVALS` — 6 rivalry pairs (started 2025)
### `SEASON_HISTORY` — past season results (2023–2025)
### `SDATA` / `SLABELS` — scoring values and display names
### `DRAFT_ORDER_2026` — 2026 round 1 order (13 picks — includes consolation bonus pick 1.13)
### `KTC_SNAPSHOT` — hardcoded dynasty player values (snapshot April 2026)
### `KTC_PICK_VALUES` — pick values by year + round
### `LEAGUE_CONTEXT` — static context string injected into AI calls

---

## LOCALSTORAGE KEYS

| Key | TTL | Contents |
|-----|-----|----------|
| `tol_cache_v2` | 6h | Current season rosters |
| `tol_theme` | permanent | User theme preference |
| `tol_lids` | permanent | Past league IDs |
| `tol_matchups_{year}` | permanent | All 17 weeks of matchup data |
| `tol_txn_{year}` | permanent | All completed transactions |
| `tol_drafts_{year}` | permanent | All draft picks |
| `tol_stats_{year}` | permanent | Season stats aggregated from 17 weeks |
| `tol_stats_wk_{year}_{week}` | permanent | Single-week stats |

---

## VISUAL THEME — Retro Neon Sports Broadcast

Aesthetic: late-90s ESPN2 / NFL Blitz / neon arcade sports. Dark UI with neon glow accents.

### Color Palette

| Role | Variable | Value |
|------|----------|-------|
| Primary accent | `--accent` | `#16E0D6` Electric Teal |
| Secondary accent | `--accent2` | `#7B2EFF` Neon Purple |
| Tertiary accent | `--accent3` | `#FF4FD8` Hot Pink |
| Dark background | `--bg` | `#0B1020` |
| Panel surface | `--surface` | `#111827` Deep Navy |
| Card background | `--card` | `#151B2F` |
| Borders | `--border` | `#253652` |
| Body text | `--text` | `#F9FAFB` Soft White |
| Secondary text | `--text2` | `#c4d4e8` |
| Muted text | `--muted` | `#aabdcf` (brightened — was `#8aa0be`) |

### Typography System

Three-level hierarchy — **no DM Mono for anything the user sees in main content**:

| Use Case | Font | Notes |
|----------|------|-------|
| Section titles, stat values | **Bebas Neue** | All-caps display, sporty |
| Display labels (stat pill labels, rivalry record labels, badge text) | **Bebas Neue** | Larger sizes (11–14px) with letter-spacing |
| Nav tab labels | **DM Sans 700** | Bold uppercase, `letter-spacing: .14em` — Bebas Neue was too condensed |
| Body text, table cells, player chips, buttons, form elements | **DM Sans** | Clean, readable |
| Code/timestamps/KTC values (intentional monospace) | **DM Mono** | Used sparingly; never in main content areas |

### Pink Usage (accent3 `#FF4FD8`)
Pink should be prominent throughout dark mode. Currently pink is used on:
- Stat pill labels (PAST CHAMPIONS, HIGHEST CAREER EARNINGS, etc.)
- All table headers (`.dtbl th`, `.career-tbl th`) with glow
- Section subtitles (`.sec-sub`)
- Fun-card labels (`.fun-label`)
- Section row labels (`.sec-row-label`)
- Rivalry card record totals and labels
- Rivalry card top border accent stripe
- Scores tab H2H strip at bottom of each matchup card
- "Open in Sleeper" link in header

### Teal Usage (accent `#16E0D6`)
- Active nav tab bottom border and label
- Winning team left border stripe on matchup cards
- Leading score highlight
- Primary interactive hover states

### Glow System
All neon glows live in the `RETRO NEON SPORTS THEME — ENHANCEMENTS` block and the `TYPOGRAPHY OVERHAUL` block near the end of `<style>`. Scoped to `[data-theme="dark"]`. Pattern: `text-shadow: 0 0 Xpx rgba(R,G,B,0.Y)`. Keep values subtle.

### Logo Files (wired in)
- `TOL Large Logo.png` — sticky header (52px tall) and home panel hero (max 420px)
- `TOL Small Logo.png` — available if needed
- `TOL Abbreviated Icon.png` — favicon + iOS add-to-homescreen icon

### PWA / Mobile
```html
<link rel="icon" type="image/png" href="TOL Abbreviated Icon.png">
<link rel="apple-touch-icon" href="TOL Abbreviated Icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="The Other League">
<meta name="theme-color" content="#0B1020">
```

---

## KEY DESIGN DECISIONS (don't change without asking)

- **Non-PPR scoring** with TE premium (+0.5/rec) and distance bonuses
- **Dark/light theme toggle** — persists via `localStorage['tol_theme']`
- **LocalStorage caching** — Sleeper roster data cached 6h; historical data permanent
- **CORS fallback chain** — direct → corsproxy.io → allorigins.win; never remove
- **Single-file architecture** — all HTML, CSS, JS in `the-other-league-FINAL.html`
- **Roster chips colored by position** — QB=purple, RB=green, WR=blue, TE=orange, K=gray, DEF=red
- **Rivalries from 2025 forward only** — pre-2025 matchups excluded from rivalry records
- **2026 draft is linear, not snake** — rounds 2–4 follow the same order as round 1
- **Sidebar is permanently hidden** — `display: none !important`. `scrollToTeam()` and `buildSidebar()` exist in JS but sidebar is not visible.
- **Cache bar is permanently hidden** — hidden via inline `style="display:none"` on the div. The underlying elements still exist and `refreshData()` / `setCacheBar()` still work correctly — do not remove the DOM elements.
- **Perpetual stats live in `panel-careers`** — the `.career-status-bar` inside `panel-careers` holds the stat pills. They are populated by `buildLeaderStats()` which is called at boot and after each background fetch.
- **Home panel has no quick-nav grid** — navigation is entirely via the icon nav and the logo home link
- **"Ask Claude" tab removed from UI** — the panel and icon tab are gone, but the underlying JS (`sendAI`, `addMsg`, etc.) must remain because `getTradeAI()` calls them

---

## LEAGUE CONTEXT SUMMARY

- 12 teams, dynasty format, Year 4 (2026 upcoming)
- Commissioner: Matt Bova — team "Show Me Your Penix"
- 2025 Champion: Jake Blackwell ("Nacua Matata") — gets pick 1.12
- 2025 Consolation: Nick Merkel ("Breeces Peanut ButterCups") — gets pick 1.13
- Contenders: Chris Bova ("Titsburg Feelers"), Jake Bogardus ("BoKnows723")
- Active traders: Chris Merkel, Nick Merkel
- 2027 rule change voted in: 1 WRRB_FLEX → WR/RB/TE FLEX (increases TE value)
- Full context in: `the-other-league-context.md`

---

## WHAT NOT TO DO

- Do not introduce React, Vue, npm, or any build tool
- Do not break the single-file structure
- Do not remove the CORS fallback chain
- Do not delete `sendAI()`, `addMsg()`, `clearChat()`, `aiMessages`, or `LEAGUE_CONTEXT` — they are used by `getTradeAI()` in the Trade Evaluator
- Do not remove the `.cache-bar` DOM or its child IDs — they are used programmatically by `setCacheBar()` and `refreshData()`
- Do not revert to the old lime-green/blue/orange palette
- Do not use DM Mono for main content — it belongs only for intentional code/timestamp contexts
- Do not add the consolation winner card back to the home panel
- Do not add the sidebar back without explicit request
