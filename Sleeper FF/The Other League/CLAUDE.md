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
    ├── projections-<year>.json        ← all 17 weeks of Sleeper projections, trimmed (updated DAILY by GitHub Action)
    ├── stats-history.json             ← historical player stats cache
    ├── roster-grades-snapshot-<year>.json ← Phase 6 frozen preseason grade — does NOT exist yet; manually committed once/year (Aug1-mid Sep) via the Export panel in Rosters > Grades & Outlook
    └── scripts/
        ├── tuesday_update.py          ← weekly H2H records updater
        ├── fetch_ktc.py               ← KTC values scraper
        ├── fetch_projections.py       ← daily Sleeper projections pull → projections-<year>.json
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
  - `/state/nfl` → current season + week; drives "is this the live season/week" decisions instead of hardcoded years
  - `/projections/nfl/regular/{year}/{week}` → projected player **stat lines** (NOT points — the `pts_ppr`/`pts_std`/`pts_half_ppr` fields it also returns are Sleeper's generic scoring and know nothing about this league; never display them. Score the raw line through `calcPts()`/`SDATA` instead). ~590 KB per week for all ~9,400 players, which is why the committed `projections-<year>.json` exists. **Corrected 2026-08-19** — this note previously said "no regular in path," which was wrong (or the API changed): that URL returns HTTP 200 with an empty `{}` for every player, always, silently. Confirmed live against multiple real players and multiple weeks, including a completed 2025 week, that `regular` in the path (matching the stats endpoint's format) is required to get real data.
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
- `roster-view-teams` / `roster-view-grades` — sub-tab views inside the Rosters panel, toggled by `setRosterView('teams'|'grades', el)`. `roster-view-grades` is the Phase 6 "Grades & Outlook" section (see DEVELOPMENT ROADMAP Phase 6). Kept as self-contained divs so they can be lifted into a separate top-level panel later without touching the JS.
- `roster-grades-container` / `roster-grades-grid` — Phase 6 output; lazy-built by `buildRosterGrades()` on first click of the "Grades & Outlook" toggle button (`rview-grades-btn`)
- `grade-card-{uid}` — individual Phase 6 grade card per team (reuses `.r-card`/`.rch`/`.rcb`/`.pg` classes from the Team Rosters view — no new CSS)

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
- `renderHistoricalScores(container, matchups, week, projTotals)` — renders matchup cards; shows a projected score + `PROJ` chip for any team that hasn't scored yet and has a projection; applies bracket chips from `PLAYOFF_BRACKET_INFO`; applies rivalry banner from `RIVALRY_WEEKS`.
  **2026-08-20 fix:** this used to read `entry.projected_points` from the matchups payload. **Sleeper's matchup endpoint has no such field** — verified live, it returns `roster_id`/`points`/`matchup_id`/`starters`/`players`/`players_points`/`starters_points` and nothing else — so the value was always `null` and every 2026 matchup rendered `—` forever. The two helpers written to fix this (`fetchWeekProjections`, `calcTeamProjected`) were never wired to a caller, and `fetchWeekProjections` used the dead URL form on top of that. All three are gone; projections now come from `computeWeekProjections()`.
- `setScoresYear(year, el)` — switches year tab, resets to W1, calls `updateRivalryPills(year)`, rebuilds scores
- `setScoresWeek(week, el)` — switches week pill, rebuilds scores
- `goToScoresWeek(year, week)` — navigates from Rivalries tab: switches to scores tab, sets year+week, calls `updateRivalryPills(year)`, rebuilds scores
- `updateRivalryPills(year)` — toggles `.rivalry` class on W4/W13 pills based on `RIVALRY_WEEKS[year]`; called whenever year changes

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
- `buildRivalries()` — renders 6 rivalry cards; re-renders on every tab visit; always shows a "2026: TBD · W4 W13" placeholder row for each rivalry until live matchup data is available
- `buildH2HForYear(year, maxWeek)` — builds H2H map from cached matchup data for a single year (up to `maxWeek`; default 17)
- `findRivalWeeks(year, ridA, ridB, maxWeek)` — returns sorted list of week numbers where two roster IDs faced each other (default `maxWeek=14`)

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

### Roster Grades & Outlook (Phase 6 — scaffolding built 2026-08-18)
Lives inside the Rosters panel as a sub-tab (`setRosterView`), not a new top-level tab — see Rosters Panel IDs above. Data layer is built for all 12 teams; card UI is functional but unpolished (reuses `.r-card` classes, no new CSS). See DEVELOPMENT ROADMAP Phase 6 for spec, decisions made, and what's still open.

- `setRosterView(view, el)` — toggles `roster-view-teams` / `roster-view-grades`; lazy-calls `buildRosterGrades()` on first switch to grades
- `AGE_CURVES` — per-position prime/decline-start/cliff ages (QB/RB/WR/TE only), confirmed by Matt 2026-08-18
- `ageTimelineScore(pos, age)` — 0–1 "runway" score from a player's age vs. their position's curve; returns `null` for positions with no curve (K/DEF/RDP) — callers must skip nulls, not treat them as 0
- `resolveRosterPlayerValue(pid)` — like `getDynastyValue()` but returns `{value, matched, reason, position, age, name}` and **never** collapses a no-match to 0. This is the function to use anywhere Phase 6-style "don't silently zero a real player" behavior is needed.
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
- `gradeRoster(teamData)` — Base score from value rank + quadrant + depth flags + unresolved-match count, plus ±0.4/-0.8 for Strong/Weak readiness. Then a hard CAP (not a modifier, applied last): `highDeadWeightRisk && readiness.tier!=='Strong'` clamps the score to 3.4, just under the A- cutoff — so that combination can reach at most a B+, regardless of raw dynasty value rank. Elite value + Strong readiness + a clean bench is still fully eligible for an A. **2026-08-19**: cap trigger switched from the old `highUnprovenRisk` (flat %, over-triggering) to `highDeadWeightRisk` (Bench Dead Weight rank, see `isDeadWeight` above). No AI/free text; thresholds are a v1 guess, tune once seen against real data across a season.
- `buildGradeRationale(teamData)` — template sentence assembled from the same computed values as the grade (no AI). Includes the readiness tier/rank and pick-value breakdown. **The "grade capped" text must exactly mirror `gradeRoster()`'s cap condition** (`highDeadWeightRisk && readiness.tier!=='Strong'`), not just `highDeadWeightRisk` alone — a 2026-08-19 verification pass caught exactly this bug: a team with `highDeadWeightRisk=true` but Strong readiness (which exempts the cap) was showing "— grade capped" in its rationale despite grading a clean A. Fixed to branch on the full condition; the non-capped case now reads "...heaviest in the league, but Strong readiness exempts the cap" instead.
- `getTopAssets(uid, n)` — top-N matched players by KTC value for a roster; each asset carries `unprovenNoPayoff` = `isUnproven(pid) && isStarterSlotShaky(pid)` — a rookie/2nd-year asset with no confirmed 2026 role, propping up the team's headline value without a current-year payoff. Rendered as a ⚠ on the card's asset chip.
- `buildUnmatchedReport(allTeamsData)` / `buildUnmatchedReportHtml(rows)` — Aggregate, cross-team rollup of every starter/bench player still unmatched after alias + fuzzy matching (the same per-card flags, consolidated). `buildRosterGrades()` both `console.table`s this and renders it as a table at the top of the Grades & Outlook view, above the team cards. This is the intended ongoing discovery process for growing `KTC_NAME_ALIASES`. As of 2026-08-19 (post Chig Okonkwo + Kenny Gainwell fixes): **7 players still unmatched league-wide** (Zach Ertz, Kareem Hunt, Joe Mixon, Brady Cook, Chris Oladokun, Tyler Lockett, Austin Ekeler) — checked each against the live 500-player KTC pool by last name; none have ANY entry under any spelling, confirming these are genuine KTC coverage gaps (journeyman/deep-bench veterans outside KTC's tracked pool), not name mismatches.
- `loadRosterGradeSnapshot(year)` — fetches `roster-grades-snapshot-{year}.json` from the repo root (same no-CORS pattern as `ktc-values.json`); returns `null` if the file doesn't exist yet (expected 404 until a snapshot is taken)
- `buildSnapshotPayload(allTeamsData, year)` / `buildSnapshotExportHtml(...)` — builds the frozen-snapshot JSON and a copyable `<textarea>` in the UI. Payload freezes `readinessTier`/`deadWeightCount`/`highDeadWeightRisk`/`pickValue` alongside the grade, since they're now grade inputs — this is what the grade was based on at snapshot time; the live card always shows current (unfrozen) readiness/depth/assets regardless. **There is no automated write path** — this is a static GitHub Pages site with no server. Taking the real snapshot is a manual step: visit Grades & Outlook in the Aug 1–mid-Sep window (before waivers/trades move values), copy the textarea JSON, commit it as `roster-grades-snapshot-<year>.json` at the repo root — same manual-commit pattern already used for `KTC_SNAPSHOT`.
- `buildRosterGrades()` / `renderRosterGrades(...)` / `renderGradeCard(...)` — main build/render; lazy-fetches KTC values + `buildFuturePicksMap()` if not already loaded, then computes + renders all 12 cards

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

### Automation (Projections Bot — added 2026-08-20)
- **`scripts/fetch_projections.py`** — pulls all 17 weeks of `/projections/nfl/regular/{year}/{week}`, keeps only QB/RB/WR/TE with a real projection and only the ~30 keys this league scores, writes `projections-<year>.json`. Flags: `--year N`, `--dry-run`. Aborts rather than overwriting a good file if a pull comes back gutted (<200 players in week 1).
- **`.github/workflows/update-projections.yml`** — daily cron at 11:00 UTC (7 AM ET); commits the file only when it changed.
- **Deploy chaining (important):** commits pushed by a job using the default `GITHUB_TOKEN` do **not** fire `push`-triggered workflows — GitHub blocks that to stop workflows recursing. So the projections and KTC bots would commit their data files and the live Pages site would never pick them up. `deploy-pages.yml` therefore also triggers on `workflow_run` for both bot workflows (guarded by a `conclusion == 'success'` check). Don't remove that trigger thinking the `push` one already covers it — this was a latent gap for the KTC bot too.
- `update-ktc.yml` has `projections-*.json` in its `paths-ignore` so the daily projections commit doesn't pointlessly re-run the KTC scraper.

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
| `tol_matchups_{year}` | permanent for completed seasons; **1h TTL for the current season** (+ cleared on Refresh) | All 17 weeks of matchup data. The current season needs a TTL because `starters` changes whenever a manager sets a lineup, and the Scores tab projects off those starters — a permanent cache pinned the whole year to whatever lineups happened to be set on first load. |
| `tol_matchups_ts_{year}` | permanent | Fetch stamp for the TTL above. Kept in a *separate* key because eight other call sites read `tol_matchups_{year}` directly and expect the bare `{week: [...]}` shape. |
| `tol_scoring_v1` | permanent (refreshed each boot) | The league's live `scoring_settings`, overlaid onto `SDATA` at parse time |
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

### Phase 1 — All-Time Records & Career Stats — **partially done**
**Goal:** New "Records" tab (or section within Careers) displaying all-time per-owner stats.
- ✅ All-time W/L record per owner — `buildCareers()` career table ("Total W-L" column) + per-opponent history in `buildRivalries()`
- ❌ Most championships, most playoff appearances — not built
- ❌ Highest single-week score (all-time + per season) — not built
- ❌ Biggest blowout margin, worst loss margin — not built
- ❌ Longest win/lose streak (current + all-time) — not built
- ❌ Most points scored in a season — not built

**Data source:** Already in dashboard — Sleeper API + `SEASON_HISTORY` hardcoded data. **Complexity: Low.** The remaining gap is specifically the weekly-stat records (single-week high, blowout/worst-loss margin, streaks) — not the career W/L, which already exists.

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

### Phase 6 — Roster Grades & Outlook — **scaffolding built 2026-08-18**
**Goal:** Per-team roster card showing dynasty health and outlook, as a sub-tab inside the existing Rosters panel (not a new top-level tab — see "Roster Grades & Outlook" under JAVASCRIPT FUNCTIONS for the full function list, and "Rosters Panel" under KEY ELEMENT IDs).

**Confirmed methodology (final, not the original single-axis draft):**
- Two-axis classification: **Value** (KTC total, ranked 1–12, split top4/mid4/bottom4) × **Timeline** (age-curve-weighted runway score per `AGE_CURVES`, NOT raw avg age)
- 4 named quadrants from crossing top/bottom value × young/old: Stacked Contender, Win-Now/Aging Window, Genuine Rebuild, Bad & No Future Currency (deliberately distinct from Rebuild)
- Matching hardened: `getKTCEntryFuzzy`/`normalizeName` had two real bugs (suffix-direction, ASCII apostrophe) found and fixed while building this — see JS function notes. Unmatched starters/bench are flagged in the UI, never silently zeroed; only taxi/IR get a nominal floor value.
- Position depth flags: bench value vs. league median bench value at that position
- Grade + rationale: rule-based from value/quadrant/depth/match-confidence, no AI/free text
- Snapshot: frozen once/year (Aug 1–mid-Sep window) as a committed `roster-grades-snapshot-<year>.json`; Outlook (composition/depth) refreshes live and is shown separately from the frozen grade

**Built:** full data layer (value summation, timeline scoring, quadrant classification, depth flags, grading, snapshot read + export-to-commit) + working card UI for all 12 teams, verified against live Sleeper/KTC data in-browser.

**Still open / TODO:**
- No real snapshot committed yet — `roster-grades-snapshot-2026.json` doesn't exist; the UI correctly shows a "live DRAFT" state until one is taken and committed in the Aug1–mid-Sep window
- Middle-value-third quadrant labels ("Building"/"Treading Water") are an assumption, not in the original 4-quadrant spec — confirm with Matt
- Timeline score is weighted across the whole roster, not starters-only — confirm that's the intended scope
- Grade thresholds in `gradeRoster()` are a v1 guess, untuned against a full season of real outcomes
- ✅ 2026-08-19: nickname/display-name mismatches now handled via `KTC_NAME_ALIASES` (checked before fuzzy matching) + `buildUnmatchedReport()` as the ongoing discovery process. **7 players remain unmatched league-wide** as of this date, each individually checked against the full live KTC pool by last name — confirmed genuine KTC coverage gaps, not name mismatches: Zach Ertz, Kareem Hunt, Joe Mixon, Brady Cook, Chris Oladokun, Tyler Lockett, Austin Ekeler.
- ✅ 2026-08-19: **Kenny Gainwell resolved — was a real matching bug, not a KTC gap.** KTC tracks him as "Kenneth Gainwell" (full first name); Sleeper uses "Kenny." Added to `KTC_NAME_ALIASES`. Matt's own team's total moved 73,423 → 76,386 KTC and is no longer showing an unverified-starter warning.
- ✅ 2026-08-19: timeline score now excludes confirmed-but-negligible-value players entirely (`NEAR_ZERO_KTC_THRESHOLD`), and a separate "Speculative Depth" (lottery-ticket) count is shown per team (`SPECULATIVE_VALUE_THRESHOLD`), not folded into the timeline score or grade. Near-zero exclusion currently affects 0 players league-wide; speculative counts range 0–5 across the 12 teams.
- ⚠️ 2026-08-19 (first pass, superseded same day): **Current-Year Readiness** was first built from `isStarterSlotShaky`/`computeTeamReadiness` (Strong/Average/Weak from how many of the manager's *actually-set* starter slots were shaky). Matt correctly flagged two flaws: it measures who's starting, not the *value* of those starters, and it falsely reads "Weak" for a manager who simply hasn't set a lineup (i LOVE mendoza showed 5 of 11 slots empty for exactly this reason, not because of bad players).
- ✅ 2026-08-19 (same day): **Current-Year Readiness rebuilt** around season-long projected points and an optimal-lineup solve — see "Current-Year Readiness (2026-08-19 full rebuild)" in JS function notes for the full mechanics (`getSeasonPointsByPid`, `getLeagueRosterPositions`, `computeOptimalLineup`, `computeReadinessRankings`). This also surfaced and fixed a real, previously-silent bug: the projections API URL was missing `regular` in the path and had been returning empty data for every player, always (see `fetch2026SeasonStats()` note above) — found while investigating why Sleeper's own projections weren't showing up, which Matt correctly pushed back on when told they weren't available. Verified against real data: i LOVE mendoza now resolves to a full 11/11 lineup, Average readiness, rank #8 of 12 — an honest "doesn't project as well as its dynasty value suggests" read instead of a false "half the lineup is empty" one.
- ✅ 2026-08-19: **Unproven Risk replaced with Bench Dead Weight.** Matt confirmed the recommended fix. The old flat "% of value in unproven players" trigger (10 of 12 teams flagged at 25%) is gone — replaced by `isDeadWeight` (veteran, years_exp≥2, confirmed KTC value ≤2000, same threshold `speculativeCount` uses on the young end) ranked across all 12 teams, worst third flagged as `highDeadWeightRisk`. Now driving both the quadrant "— High Bench Dead Weight" suffix and the grade cap. Verified: exactly 4 of 12 teams flagged (Titsburg 9, BoKnows723 8, SirWinsAlot 7, i LOVE mendoza 7), a real discriminating spread instead of nearly everyone.
- ✅ 2026-08-19: **grade formula blends Readiness in and applies Bench Dead Weight as a hard cap** — `highDeadWeightRisk && readiness.tier!=='Strong'` clamps the score so the team can reach at most a B+, never A-/A, regardless of raw value rank. `readiness.tier` comes from the projected-lineup ranking. See `gradeRoster()` in JS function notes for the exact mechanics, and the same section for a rationale-text bug this surfaced and fixed (a team with the cap condition only half-true was claiming "grade capped" when it wasn't actually capped).
- ✅ 2026-08-19: **Future draft-pick value now counted in Roster Value.** Matt caught that `total` was players-only. Now folds in 2027/2028 picks via the existing `buildFuturePicksMap()` + `getKTCPickValue()` (raw value, "Mid" tier default, not the Trade Evaluator's slider-adjusted value). Verified material: ~16,000–31,600 per team, roughly 15–25% of total value, genuinely shifted Value Rank for several teams once added — this wasn't a rounding-level fix.
- Visual polish deferred — cards reuse existing `.r-card` classes as-is, no new styling pass yet

**Data source:** Sleeper rosters + KTC values (same as Phases 3–4). **Complexity: Medium — KTC integration was the key dependency; matching turned out to need two real fixes.**

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
