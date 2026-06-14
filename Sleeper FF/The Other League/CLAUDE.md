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
    ├── ktc-values.json                ← KTC dynasty values (updated weekly by GitHub Action)
    ├── stats-history.json             ← historical player stats cache
    └── scripts/
        ├── tuesday_update.py          ← weekly H2H records updater
        ├── fetch_ktc.py               ← KTC values scraper
        └── bot_state.json             ← tracks which weeks have been applied
```

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
  - `/projections/nfl/{year}/{week}` → projected player stats (**no "regular" in path** — different from stats endpoint)
- CORS note: Direct browser fetch may fail. Fallback proxies in order: `corsproxy.io`, `api.allorigins.win`

### Anthropic API
- The "Ask Claude" tab was removed from the UI (panel and icon tab are gone)
- `getTradeAI()` was also removed in the June 2026 Trade Evaluator overhaul
- `sendAI()`, `addMsg()`, `clearChat()`, `aiMessages`, `LEAGUE_CONTEXT`, `QUICK_PROMPTS` remain in JS as dead code — safe to clean up in a future pass but do not remove without confirming no other callers exist

---

## NAVIGATION STRUCTURE

### Sticky Shell
`<div class="sticky-shell">` uses `position: sticky; top: 0; z-index: 100`. It contains:
1. `<header>` → logo (home link) + "Open in Sleeper" pill + dark mode toggle
2. `<nav class="icon-nav">` → 9 icon tabs + 1 refresh button

The header logo (`<div class="hdr-logo-link">`) calls `showTab('home')` on click — it IS the home button.

### Icon Nav
Each tab is `<div class="icon-tab" onclick="showTab('id',this)" data-tab="id">` with an emoji icon and text label. The active tab gets `class="active"` and a teal bottom border.

The Refresh button at the end is `<div class="icon-tab nav-refresh-btn" onclick="refreshData()">` — styled with a left border separator; it never gets the active class.

**Mobile layout (≤ 680px):** The nav wraps into two rows of 5 using `flex-wrap: wrap` with each tab at `width: 20%`. Row 1: Careers, Scores, Rivalries, Trade Eval, Rosters. Row 2: Draft, Stats, Txns, League, Refresh. Labels use 8px font with tighter letter-spacing on mobile. Desktop remains a single scrollable row with the same left-to-right order.

### URL Hash Routing
`showTab(tab, el)` calls `history.replaceState(null,'','#'+tab)`. On boot, `routeFromHash()` reads `location.hash` and navigates to the matching tab. `hashchange` event is also wired. Valid tab IDs are in `VALID_TABS` array in JS.

### `body.is-home` CSS Class
`document.body.classList.toggle('is-home', tab==='home')` — set in HTML on `<body class="is-home">` at load, toggled in `showTab()`. CSS rules under `body.is-home` hide the sidebar, cache bar, and utility strips, and give the home panel edge-to-edge layout.

### Tabs and Panels

Tab order (desktop L→R; mobile row 1 then row 2):

| # | Icon | Tab Label | `showTab` ID | Panel ID | Lazy load? |
|---|------|-----------|--------------|----------|-----------|
| ← | (logo click) | Home | `home` | `panel-home` | No — static HTML with countdown JS |
| 1 | 📊 | Careers | `careers` | `panel-careers` | Yes — `buildCareers()` on first visit |
| 2 | 🏈 | Scores | `scores` | `panel-scores` | Yes — `buildScores()` on first visit. Year tabs: 2026 (default), 2025, 2024, 2023. W15–W17 marked "PLAYOFFS". W4/W13 pills turn pink for rivalry years. |
| 3 | ⚔️ | Rivalries | `rivalries` | `panel-rivalries` | Re-renders every visit via `buildRivalries()` |
| 4 | ⚖️ | Trade Eval | `trade` | `panel-trade` | Yes — `initTradeEval()` on first visit. |
| 5 | 👥 | Rosters | `rosters` | `panel-rosters` | No — loaded at boot via `init()` |
| 6 | 🎯 | Draft | `draft` | `panel-draft` | Yes — `buildDraft2026()` at boot; past years on demand |
| 7 | 📈 | Stats | `stats` | `panel-stats` | Yes — `buildPlayerStats()` on first visit |
| 8 | 📋 | Transactions | `transactions` | `panel-transactions` | Yes — `buildTransactions()` on first visit |
| 9 | ℹ️ | League | `league` | `panel-league` | No — static HTML |
| 10 | ↺ | Refresh | — | — | Calls `refreshData()` directly; not a panel tab |

**Removed tabs:** "Ask Claude" (`ai` / `panel-ai`) was removed from the UI. The underlying JS functions are dead code (see Anthropic API section).

### Home Panel (`panel-home`)
Contains:
- `TOL Large Logo.png` as hero image with neon glow (`.home-hero-logo`)
- NFL Season countdown to **Sep 9, 2026 8:20 PM ET** — `startCountdown()` function, IDs: `cd-days`, `cd-hours`, `cd-mins`, `cd-secs`
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
- `roster-team-chips` — multi-select team filter chip bar (built by `buildTeamFilterChips`)

### Rivalries Panel
- `rivalry-grid` — rivalry matchup cards

### Draft Panel
- `draft-view-past` — visible by default; all years including 2026 render here via `buildDraftHistory()`
- `draft-view-2026` — hidden by default (`display:none`); reserved for future use; `d26-tbody` is unpopulated
- `d26-list-view`, `d26-board-view`, `d26-tbody` — inside the hidden 2026 view
- `draft-history-container` — inside `draft-view-past`; holds rendered picks
- `draft-team-chips` — multi-select team filter chip bar above the year toggle

### Player Stats Panel
- `stats-yr-toggle`, `stats-pos-filter`, `stats-wk-filter`, `stats-container`
- `sg-pass`, `sg-rush`, `sg-rec` — stat group toggle buttons (Passing / Rushing / Receiving); toggling rebuilds the table
- `stats-team-chips` — multi-select team filter chip bar (includes "All Teams" + "Free Agents" + one chip per team); built once by `buildStatsTeamChips()`; filters rows via `applyStatsFilters()` show/hide (no re-fetch)

### Transactions Panel
- `txn-container`, `txn-yr-toggle`, `txn-filter-bar`, `txn-player-search`, `txn-player-results`
- `txn-team-chips` — multi-select team filter chip bar (replaced the old `txn-team-filter` dropdown)

### Careers Panel
- `careers-container` — career stats table + season standings

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

### Stats Banner (Perpetual Stats)
- `buildLeaderStats()` — computes and renders all 7 perpetual stats from `SEASON_HISTORY` + cached pick/transaction data. Called at boot and after each background data fetch. Targets IDs inside `panel-careers`.

### Careers
- `buildCareers()` — calls `buildLeaderStats()` to refresh pills, then builds the career earnings/placement table and per-season standings tables

### Scores Tab
State variables: `currentScoresYear` (default 2026), `currentScoresWeek` (default 1)

- `buildScores()` — fetches matchups for `currentScoresYear` via `findLeagueIds()` + `fetchAllMatchups()`, then calls `renderHistoricalScores()`
- `renderHistoricalScores(container, matchups, week)` — renders matchup cards; handles 2026 "projected" banner + `—` scores for pre-season; applies bracket chips from `PLAYOFF_BRACKET_INFO`; applies rivalry banner from `RIVALRY_WEEKS`
- `setScoresYear(year, el)` — switches year tab, resets to W1, calls `updateRivalryPills(year)`, rebuilds scores
- `setScoresWeek(week, el)` — switches week pill, rebuilds scores
- `goToScoresWeek(year, week)` — navigates from Rivalries tab: switches to scores tab, sets year+week, calls `updateRivalryPills(year)`, rebuilds scores
- `updateRivalryPills(year)` — toggles `.rivalry` class on W4/W13 pills based on `RIVALRY_WEEKS[year]`; called whenever year changes

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
- `buildRivalries()` — renders 6 rivalry cards; re-renders on every tab visit; always shows a "2026: TBD · W4 W13" placeholder row for each rivalry until live matchup data is available
- `buildH2HForYear(year, maxWeek)` — builds H2H map from cached matchup data for a single year (up to `maxWeek`; default 17)
- `findRivalWeeks(year, ridA, ridB, maxWeek)` — returns sorted list of week numbers where two roster IDs faced each other (default `maxWeek=14`)

### Player Stats
State variables: `currentStatsYear` (default 2026), `currentStatsPos` (default `'all'`), `currentStatsWeek` (default `'season'`), `statsShowPass`, `statsShowRush`, `statsShowRec` (all default `true` — control column group visibility), `currentStatsTeams` (Set — roster_ids; `0` = free agents; empty = all teams).

- `fetchPlayerStats(year)` / `fetchWeekStats(year, week)` — fetches and caches stat data for 2023–2025 (permanent localStorage)
- `fetch2026SeasonStats()` — fetches all 17 weeks of actuals (`/stats/nfl/regular/2026/{week}`) + projections (`/projections/nfl/2026/{week}`) in parallel; identifies completed weeks by `gp >= 1`; aggregates actuals and projected separately; caches in session-only `_stats2026Cache` (cleared on Refresh, not localStorage)
- `fetch2026WeekStats(week)` — tries actuals first; falls back to projections if no `gp >= 1` data
- `calcPts(stats, pos)` — calculates fantasy points using `SDATA`. **Note:** Projections API returns different field names than stats API — projection aggregation must capture all numeric fields (not filter by STAT_KEYS) or use `pts_std`/`pts_half_ppr`/`pts_ppr` fallback.
- `build2026Stats(c, pos)` — 2026 renderer; season view shows dual "Act. Pts" / "Proj Pts" columns; week view shows actuals or projected with PROJ chip; uses unified column builder (same as `buildPlayerStats`)
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
- `buildDraft2026()` — **never called** — dead code; `d26-tbody` is never populated; `draft-view-2026` stays hidden
- `buildDraftHistory(year)` — fetches and renders past draft results for ALL years (including 2026); calls `buildTeamFilterChips` after rendering
- `renderDraftPicks(container, picks, year)` — filters picks by `currentDraftTeams` before rendering
- `renderDraftBoard(picks, year)` — filters picks by `currentDraftTeams` before rendering (shows only selected teams' columns on board view)

### Tab Navigation
- `showTab(tab, el)` — activates tab + panel; triggers lazy-load on first visit; toggles `body.is-home`; updates URL hash

### Trade Evaluator
- `initTradeEval()` — lazy-init: populates team dropdowns, builds pos/team chips, calls `fetchKTCValues()`, then builds player list and renders table; calls `buildFuturePicksMap()` after
- `fetchKTCValues()` — fetches `https://keeptradecut.com/dynasty-rankings?format=1&tep=1` HTML, parses `var playersArray = [...]` via bracket-counting, extracts `superflexValues.tep.value` per player; tries direct then two CORS proxies; falls back to `KTC_SNAPSHOT` if all fail. 24h localStorage cache under `tol_ktc_v3`.
- `loadKTCCache()` — checks `tol_ktc_v3` for a valid 24h cache; sets `_ktcValues` and `_ktcSource`
- `getKTCEntry(name)` — exact-name lookup in `_ktcValues` or `KTC_SNAPSHOT`; returns `{value, position, nflTeam, age, rank, trend}` or null
- `getKTCEntryFuzzy(name)` — exact match → normalized match (strips apostrophes/periods, lowercases) → null; used for Sleeper→KTC name mapping
- `normalizeName(n)` — strips apostrophes, backticks, periods; lowercases; collapses spaces; used for fuzzy name matching
- `getDynastyValue(pid)` — resolves a Sleeper player_id → KTC value via name lookup + last-name fallback; returns 800 if not found
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

### Boot
- `startCountdown()` — countdown timer to **Sep 9, 2026 8:20 PM ET**; ticks every 1s
- `routeFromHash()` — reads `location.hash` on boot and navigates to matching tab
- `init()` — boot sequence: loads/caches rosters, builds leader stats, prefetches historical data in background

### Automation (Tuesday Bot)
Weekly automation that runs every Tuesday at 9am ET (after Monday Night Football) to update `h2h-records.md` with the prior week's H2H results.

- **`scripts/tuesday_update.py`** — fetches `state/nfl` to detect current week, fetches matchups from Sleeper API, parses and rewrites `h2h-records.md`. Flags: `--week N`, `--dry-run`, `--force`. Tracks applied weeks in `scripts/bot_state.json`.
- **`.github/workflows/tuesday-update.yml`** — GitHub Actions cron (Tuesday 1pm UTC); also has manual trigger with week/dry-run/force inputs. Commits `h2h-records.md` + `bot_state.json` if changed.
- **`scripts/run_tuesday_update.bat`** — Windows launcher called by Task Scheduler; logs to `scripts/tuesday_update.log`.
- **`scripts/setup_scheduled_task.ps1`** — one-time setup to register the Windows Task Scheduler task. Task is **dormant until Sep 9, 2026** (`StartBoundary`); fires on next boot if PC was off at 9am.
- **`.github/workflows/season-reminder.yml`** — GitHub Actions creates a GitHub Issue on Sep 2, 2026 as a reminder to activate the bot; GitHub emails the repo owner automatically.

---

## DATA OBJECTS

### `TEAMS` — static team registry
```javascript
// user_id → { name, team, you, tier, note?, co? }
```
`you: true` marks Matt Bova's team. `co` is for co-owned teams.

### `RM` / `RMR` — roster → owner mapping
```javascript
const RM = { 1: '721908735856967680', ... };  // roster_id → user_id
const RMR = {};  // user_id → roster_id (computed at boot)
```

### `RIVALS` — 6 rivalry pairs (started 2025)
### `SEASON_HISTORY` — past season results (2023–2025)
### `SDATA` / `SLABELS` — scoring values and display names
### `DRAFT_ORDER_2026` — 2026 round 1 order (13 picks — includes consolation bonus pick 1.13)
### `KTC_SNAPSHOT` — hardcoded dynasty player values (Superflex + PPR + TE Premium, June 2026). ~80 players + all 2027/2028 pick tiers (Early/Mid/Late × 4 rounds). Used as fallback when live KTC fetch fails. Pick values represent the +25% slider position (full KTC). Format: `name → value (number)` for snapshot; `name → {value, position, nflTeam, age, rank, trend}` for live cached data.
### `LEAGUE_CONTEXT` — static context string (dead code — `getTradeAI()` was removed)
### `RIVALRY_WEEKS` — rivalry week numbers per year: `{ 2025: [4, 13], 2026: [4, 13] }`. Controls pink pill styling on Scores tab and rivalry banner on matchup cards.
### `PLAYOFF_BRACKET_INFO` — playoff bracket labels for W15/W16/W17. Keyed `year → week → { "NameA|NameB" → { label, style } }`. Names are sorted alphabetically before joining with `|`. Covers 2023, 2024, 2025 fully. Add 2026 data here once playoff matchup pairings are known. Styles: `'gold'` (championship), `'bronze'` (3rd/5th place), `'silver'` (consolation final), omit for regular bracket rounds.

---

## LOCALSTORAGE KEYS

| Key | TTL | Contents |
|-----|-----|----------|
| `tol_cache_v2` | 6h | Current season rosters |
| `tol_ktc_v3` | 24h | Live KTC player values (Superflex+PPR+TEP) — map of `{playerName: {value,position,nflTeam,age,rank,trend}}` |
| `tol_theme` | permanent | User theme preference |
| `tol_lids` | permanent | Past league IDs |
| `tol_matchups_{year}` | permanent (2023–2025); **cleared on Refresh for 2026** | All 17 weeks of matchup data |
| `tol_txn_{year}` | permanent (2023–2025); **cleared on Refresh for 2026** | All completed transactions |
| `tol_drafts_{year}` | permanent | All draft picks |
| `tol_stats_{year}` | permanent | Season stats aggregated from 17 weeks (2023–2025 only) |
| `tol_stats_wk_{year}_{week}` | permanent | Single-week stats (2023–2025 only) |
| `_stats2026Cache` | session (JS variable, not localStorage) | 2026 actual + projected stats; cleared on Refresh via `refreshData()` |

---

## VISUAL THEME — Arcade Neon (NFL Blitz)

Aesthetic: late-90s NFL Blitz / arcade-neon sports broadcast — glossy electric-teal + hot-magenta + neon-purple on near-black, pulled directly from the TOL logo. Premium / "legit" (ESPN/Sleeper-grade), **mobile-first**. Dark is the default theme; light mode is fully supported.

**HOW THE REDESIGN IS STRUCTURED — read this before editing styles:**
- The redesign is a stack of **appended CSS layers at the very END of `<style>`**, each opened by a banner comment: `ARCADE NEON REDESIGN`, then one block per tab (`CAREERS TAB — Arcade Neon polish`, `SCORES TAB…`, `RIVALRIES…`, `TRADE EVALUATOR…`, `DRAFT · STATS · TRANSACTIONS · LEAGUE…`, `HOME TAB…`, `LIGHT MODE…`). They cascade over the original CSS above them — do not delete them.
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
`shortName(name)` (defined next to `abbrev()`) returns **first-initial + last name** ("Matt Bova" → "M Bova"). Used on every team filter chip (Rosters, Draft, Transactions, Stats, Trade Eval) because many owners share a first name. Use it for any new team-filter UI.

### Logo Files (wired in)
- `TOL Large Logo.png` — sticky header (76px tall; 46px mobile) + home hero (max 420px; 260px mobile)
- `TOL Abbreviated Icon.png` — favicon + iOS add-to-homescreen icon
- `TOL Small Logo.png` — available if needed

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

- **PPR scoring** with TE premium (+0.5/rec) and distance bonuses. `SDATA` has `rec: 1.0` (PPR). Do not set back to 0.0.
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
- **Sidebar is permanently hidden** — `display: none !important`. `scrollToTeam()` and `buildSidebar()` exist in JS but sidebar is not visible.
- **Cache bar is permanently hidden** — hidden via inline `style="display:none"` on the div. The underlying elements still exist and `refreshData()` / `setCacheBar()` still work correctly — do not remove the DOM elements.
- **Perpetual stats live in `panel-careers`** — the `.career-status-bar` inside `panel-careers` holds the stat pills. They are populated by `buildLeaderStats()` which is called at boot and after each background fetch.
- **Home panel has no quick-nav grid** — navigation is entirely via the icon nav and the logo home link
- **"Ask Claude" tab removed from UI** — the panel and icon tab are gone, but the underlying JS (`sendAI`, `addMsg`, etc.) must remain because `getTradeAI()` calls them

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

### Phase 1 — All-Time Records & Career Stats
**Goal:** New "Records" tab (or section within Careers) displaying all-time per-owner stats.
- All-time W/L record per owner
- Most championships, most playoff appearances
- Highest single-week score (all-time + per season)
- Biggest blowout margin, worst loss margin
- Longest win/lose streak (current + all-time)
- Most points scored in a season

**Data source:** Already in dashboard — Sleeper API + `SEASON_HISTORY` hardcoded data. **Complexity: Low.**

---

### Phase 2 — Head-to-Head Rivalry History
**Goal:** Expand the existing Rivalries tab with full all-time H2H detail.
- All-time H2H record between any two managers (clickable matchup grid)
- Full game log per rivalry (date, scores, winner)
- Average margin of victory per matchup
- "Nemesis" stat — who has the worst record against a specific opponent

**Data source:** Sleeper matchup API by week — same data used by `buildH2HMap()`. **Complexity: Low-medium.**

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

### Phase 6 — Roster Grades & Outlook
**Goal:** Per-team roster card showing dynasty health and outlook.
- KTC total roster value (ranked 1–12)
- Avg age of starters
- Win-now / contender / rebuilding classification
- Top 3 core assets
- Letter grade (A–F) with brief rationale

**Data source:** Sleeper rosters + KTC values (same as Phases 3–4). **Complexity: Medium — KTC integration is the key dependency.**

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

## WHAT NOT TO DO

- Do not introduce React, Vue, npm, or any build tool
- Do not break the single-file structure
- Do not remove the CORS fallback chain
- Do not add back `getTradeAI()` or AI scoring dimensions to the Trade Evaluator — the June 2026 overhaul replaced them with KTC values intentionally
- Do not remove the `.cache-bar` DOM or its child IDs — they are used programmatically by `setCacheBar()` and `refreshData()`
- Do not revert the Arcade Neon palette/type (teal #21F5E4 · magenta #FF3DBE · purple #9A55FF on #06060C, Saira Condensed display) — see VISUAL THEME. The redesign lives in appended, banner-commented CSS layers at the end of `<style>`; style by class + variables.
- Do not use DM Mono for main content — it belongs only for intentional code/timestamp contexts
- Do not add the consolation winner card back to the home panel
- Do not add the sidebar back without explicit request
