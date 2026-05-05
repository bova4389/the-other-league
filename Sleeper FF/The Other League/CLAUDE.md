# CLAUDE.md — The Other League Dynasty Dashboard

## WHAT THIS PROJECT IS

A personal fantasy football dashboard for "The Other League" — a 12-team dynasty league on the Sleeper platform. The site pulls live data from the Sleeper public API and the Anthropic API to display rosters, league history, draft picks, scoring rules, rivalries, and an AI analysis layer.

**Owner:** Matt Bova (commissioner). Built for personal use during development; eventually shared with league mates.

---

## PROJECT STRUCTURE

This is a **static HTML/JavaScript project** — no framework, no build step, no package manager. All files are plain `.html` with embedded CSS and JavaScript.

```
the-other-league/
├── CLAUDE.md                          — you are here
├── index.html                         — main unified dashboard (target state)
├── the-other-league-FINAL.html        — current working version (most complete)
├── the-other-league-Claude-html.html  — earlier version (reference only)
├── the-other-league-context.md        — master league context document
└── chunks/                            — prior standalone chunk files (reference)
    ├── chunk1-history.html
    ├── chunk2-rosters.html
    └── chunk3-draft.html
```

**Current state:** `the-other-league-FINAL.html` is the working file. It combines rosters, league info, scoring, rivalries, draft, transactions, career stats, and an embedded "Ask Claude" AI tab into one file.

**Deployment:** GitHub Pages (static hosting). No server, no backend. All API calls happen client-side from the browser.

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
- Endpoint: `https://api.anthropic.com/v1/messages`
- Model: `claude-sonnet-4-20250514`
- Used for: the "Ask Claude" tab — AI analysis chat with full league context injected as the first user message
- No API key handling needed in code (handled externally)

---

## TABS AND PANELS

The dashboard has 9 tabs rendered in `<div class="tabs">`. Each tab calls `showTab(id, el)` and maps to a `<div class="panel" id="panel-{id}">`. **Careers is the default active tab on load.**

| Tab Label       | `showTab` ID    | Panel ID              | Lazy load?                              |
|-----------------|-----------------|------------------------|------------------------------------------|
| Careers (default)| `careers`      | `panel-careers`        | Yes — `buildCareers()` on first visit    |
| Scores          | `scores`        | `panel-scores`         | Yes — `buildScores()` on first visit     |
| Rosters         | `rosters`       | `panel-rosters`        | No — loaded at boot via `init()`         |
| Player Stats    | `stats`         | `panel-stats`          | Yes — `buildPlayerStats()` on first visit |
| League Info     | `league`        | `panel-league`         | No — static HTML; scoring section rendered via `buildScoring()` at boot |
| Rivalries       | `rivalries`     | `panel-rivalries`      | Re-renders on every visit via `buildRivalries()` |
| Draft           | `draft`         | `panel-draft`          | Yes — `buildDraft2026()` at boot; past years on demand |
| Transactions    | `transactions`  | `panel-transactions`   | Yes — `buildTransactions()` on first visit |
| ⚖ Trade Eval   | `trade`         | `panel-trade`          | Yes — `initTradeEval()` on first visit  |
| ⚡ Ask Claude   | `ai`            | `panel-ai`             | No — static form; sends on user action  |

---

## KEY ELEMENT IDs

### Header / Cache Bar
- `cache-dot` — colored dot (live vs cached)
- `cache-status-txt` — cache status message
- `refresh-btn` — clears cache and re-fetches
- `t-icon`, `t-lbl` — theme toggle icon and label

### Stats Pills (top status bar)
- `stat-champs` — past champions list
- `stat-earn-val`, `stat-earn-sub` — highest career earnings
- `stat-wins-val`, `stat-wins-sub` — most career wins
- `stat-cons-val`, `stat-cons-sub` — most consistent finisher
- `stat-picks-val`, `stat-picks-sub` — most draft picks
- `stat-trades-val`, `stat-trades-sub` — most trades completed
- `stat-worst-val`, `stat-worst-sub` — worst average finish

### Sidebar
- `team-list` — sidebar team items (built by `buildSidebar()`)

### Scores Panel
- `scores-container` — main scores area; holds matchup cards or off-season standings
- `match-grid-inner` — dynamically created inside `scores-container` during season

### Rosters Panel
- `rosters-container` — roster grid (12 `r-card` divs)
- `roster-card-{uid}` — individual roster card per team (used by `scrollToTeam()`)

### Scoring Panel
- `score-grid` — grid of scoring rule items

### Rivalries Panel
- `rivalry-grid` — rivalry matchup cards

### Draft Panel
- `draft-view-2026` — 2026 draft view container
- `draft-view-past` — past draft years view container
- `d26-list-view`, `d26-board-view` — list/board toggle views for 2026
- `d26-tbody` — table body for 2026 draft order
- `d26-list-btn`, `d26-board-btn` — view toggle buttons for 2026
- `draft-past-list-view`, `draft-past-board-view` — list/board toggle for past drafts
- `dpast-list-btn`, `dpast-board-btn` — view toggle buttons for past drafts
- `draft-history-container` — renders inside `draft-past-list-view`

### Player Stats Panel
- `stats-yr-toggle` — year filter buttons (2025 / 2024 / 2023)
- `stats-pos-filter` — position filter pills (All / QB / RB / WR / TE / Rookies)
- `stats-wk-filter` — week filter pills (Season / W1–W17)
- `stats-container` — player stats table render area

### Transactions Panel
- `txn-container` — transaction list render area
- `txn-yr-toggle` — year filter buttons
- `txn-filter-bar` — type filter pills (All / Waivers / Free Agent / Trades)
- `txn-team-filter` — team dropdown select
- `txn-player-search` — player history search input
- `txn-player-results` — player history search results

### Careers Panel
- `careers-container` — career stats table

### Trade Evaluator Panel
- `ktc-badge` — shows "Values: KTC Live ✓" (green) or "Values: Snapshot" (yellow) after `fetchKTCValues()` resolves

### AI Panel
- `ai-input` — chat input field
- `ai-send-btn` — send button
- `ai-history` — message thread container

---

## JAVASCRIPT FUNCTIONS

### Theme
- `toggleTheme()` — toggles `data-theme` on `<html>`, saves to `localStorage`
- `applyTheme()` — restores saved theme on page load

### Cache
- `saveCache(rosters)` — writes roster data + timestamp to `localStorage[tol_cache_v2]`
- `loadCache()` — reads cache; returns `null` if missing or older than 6h
- `clearCache()` — removes `tol_cache_v2` from localStorage
- `savePerm(key, data)` — writes data with no TTL (for historical data that never changes)
- `loadPerm(key)` — reads permanent data from localStorage
- `setCacheBar(fromCache, ts)` — updates the cache dot, text, and refresh button
- `refreshData()` — clears cache, resets state, re-runs `init()`

### Sleeper API
- `api(path)` — fetches from Sleeper with CORS fallback chain (direct → corsproxy.io → allorigins.win)
- `findLeagueIds()` — walks `previous_league_id` chain to discover past season league IDs; caches in `tol_lids`

### Matchups / H2H
- `fetchAllMatchups(leagueId, year)` — fetches all 17 weeks of matchups for a season; caches in `tol_matchups_{year}`
- `buildH2HMap()` — builds all-time H2H record map from all cached matchup seasons; returns `h2h[ridA][ridB] = {w, l}`
- `buildH2HForYear(year)` — same as `buildH2HMap()` but for a single season only

### Scores Tab
- `buildScores()` — entry point: checks if season is live (week > 0) or off-season
- `renderScoresOffseason(c)` — shows 2025 final standings when no active season
- `renderScoresWeek(container, week)` — renders matchup cards for a given week with all-time H2H records
- `changeScoreWeek(week)` — nav handler for prev/next week buttons

### Sidebar
- `buildSidebar()` — populates `#team-list` from `RM` + `TEAMS`
- `scrollToTeam(uid)` — switches to Rosters tab and smooth-scrolls to that team's card

### Rosters
- `buildRosters(rostersData, playersData)` — renders 12 roster cards with position-colored player chips; starters/bench/taxi/IR in separate sections

### Scoring
- `buildScoring()` — renders non-zero scoring values from `SDATA` into `#score-grid`

### Rivalries
- `buildRivalries()` — renders 6 rivalry cards with H2H records from 2025 forward; re-renders on every tab visit

### Player Stats
- `fetchPlayerStats(year)` — fetches all 17 weeks of stats for all current dynasty roster players; permanently caches in `tol_stats_{year}`
- `fetchWeekStats(year, week)` — fetches stats for a single week; permanently caches in `tol_stats_wk_{year}_{week}`
- `calcPts(stats, pos)` — calculates estimated fantasy points from raw stat object using `SDATA` scoring settings
- `buildPlayerStats(year, posFilter)` — renders player stats table sorted by estimated points; shows raw stat columns and point total
- `setStatsYear(year, el)` — switches active year, re-renders stats
- `setStatsWeek(week, el)` — switches between season total and a specific week; re-renders stats
- `setStatsPos(pos, el)` — switches position filter; re-renders stats
- `showPlayerStats(playerId)` — shows detailed stat breakdown modal/view for a specific player

### Transactions
- `fetchTransactions(leagueId, year)` — fetches all completed transactions for a season; permanently caches past years
- `buildTransactions(filter, year)` — renders filtered transaction list into `#txn-container`
- `populateTxnTeamDropdown()` — fills `#txn-team-filter` select once on first visit
- `setTxnTeam(value)` — updates `currentTxnTeam` and re-renders
- `setTxnYear(year, el)` — switches active year, clears player search, re-renders
- `setTxnFilter(type, el)` — switches type filter, re-renders
- `onTxnPlayerSearch(val)` — debounced (350ms) input handler for player search
- `runPlayerSearch(query)` — searches all seasons' transactions + draft history for a player; requires `cachedPlayers`
- `renderTxnRow(tx)` — renders a waiver/free agent transaction row
- `renderTxnTrade(tx, date)` — renders a two-sided trade card
- `clearPlayerSearch()` — resets player search input and hides results

### Draft
- `buildDraft2026()` — renders 2026 draft order table; fetches traded picks from Sleeper to annotate traded slots. Draft is **linear** (same order every round, not snake). tradedFrom map keyed by `"round.roster_id"` → `owner_id` (current holder)
- `renderDraft2026Board()` — renders 2026 draft order as a board (teams as columns); built once on demand
- `setDraft26View(view, el)` — toggles list/board for 2026 draft
- `buildDraftHistory(year)` — fetches and renders past draft results for 2023/2024/2025
- `renderDraftPicks(container, picks, year)` — renders picks as a sortable list table
- `renderDraftBoard(picks, year)` — renders picks as a board with teams as columns
- `setDraftPastView(view, el)` — toggles list/board for past draft results
- `setDraftYear(year, el)` — switches between 2026 order and past year results

### Stats Banner
- `buildLeaderStats()` — computes and renders all 7 header stats from `SEASON_HISTORY` + cached pick/transaction data; called at boot and after each background data fetch

### Careers
- `buildCareers()` — builds career earnings/placement table from `SEASON_HISTORY` for 2023–2025

### Tab Navigation
- `showTab(tab, el)` — activates a tab + panel; triggers lazy-load functions on first visit

### Trade Evaluator
- `initTradeEval()` — lazy-init on first tab visit: populates team dropdowns, kicks off `fetchKTCValues()`
- `fetchKTCValues()` — tries to fetch live KTC dynasty values via unofficial JSON endpoint + CORS proxy chain; falls back to `KTC_SNAPSHOT` if fetch fails or returns < 50 players; sets `_ktcSource` to `'live'` or `'snapshot'`
- `getKTCValue(playerName)` — looks up player value from `_ktcValues` (live) or `KTC_SNAPSHOT` (fallback); fuzzy-matches on last name
- `getPickValue(year, round)` — returns pick value from `KTC_PICK_VALUES`
- `evaluateTrade()` — reads selected players/picks from both sides, computes value delta using KTC values, renders result card with winner/loser and value breakdown
- `getTradeAI(giveUid, receiveUid)` — calls Claude API with team rosters + trade details for AI analysis; appended after `evaluateTrade()` result

### AI Chat
- `quickPrompt(key)` — fills `#ai-input` with a pre-set prompt from `QUICK_PROMPTS` and calls `sendAI()`
- `clearChat()` — resets `aiMessages` and clears `#ai-history`
- `addMsg(role, content)` — appends a message bubble to `#ai-history`; parses markdown bold/bullets for assistant messages
- `sendAI()` — reads input, calls Anthropic API, renders response; injects `LEAGUE_CONTEXT` as preamble

### Boot
- `init()` — boot sequence: loads/caches rosters, builds leader stats, prefetches historical matchup/draft/transaction data in background, kicks off `buildScores()` and `buildDraft2026()`

---

## DATA OBJECTS

### `TEAMS` — static team registry
```javascript
// user_id → { name, team, you, tier, note?, co? }
const TEAMS = { ... };
```
Tiers used: `'contender'`, `'mid'`, `'trader'`, `'champion'`. The `you: true` flag marks Matt Bova's team. `co` is set for co-owned teams.

### `RM` — roster → owner mapping
```javascript
// roster_id (1–12, number key) → user_id string
const RM = { 1: '721908735856967680', ... };
```

### `RMR` — reverse: owner → roster
```javascript
// user_id string → roster_id integer
const RMR = {}; // computed from RM at boot
```

### `RIVALS` — rivalry pairs
```javascript
// Array of 6 pairs: { a: user_id, b: user_id }
const RIVALS = [ ... ];
```
Rivalries started in 2025. H2H records computed from 2025 forward only.

### `SEASON_HISTORY` — past season results
```javascript
// year → { buyin, pot, payouts: { user_id: dollars }, placements: [user_id], consolation_winner? }
const SEASON_HISTORY = { 2023: {...}, 2024: {...}, 2025: {...} };
```
`placements` is ordered 1st through 12th. `payouts` only lists earners. Used by `buildLeaderStats()` and `buildCareers()`.

### `SLABELS` — scoring key display names
```javascript
// scoring_key → human-readable label
const SLABELS = { pass_td: 'Pass TD', ... };
```

### `SDATA` — scoring values
```javascript
// scoring_key → point value (float)
const SDATA = { pass_td: 4.0, rec: 0.0, bonus_rec_te: 0.5, ... };
```
Only non-zero entries are rendered in the Scoring tab.

### `DRAFT_ORDER_2026` — 2026 round 1 draft order
```javascript
// Array of 13 entries: { pick: '1.01', uid: user_id, how: string }
const DRAFT_ORDER_2026 = [ ... ];
```
13 picks because pick 1.13 is the consolation winner's bonus pick (Nick Merkel). The 2026 draft is **linear** — rounds 2–4 repeat the same order as round 1 (not snake). Picks 1.09 = Chris Bova (4th place), 1.10 = Jake Bogardus (3rd place).

### `KTC_SNAPSHOT` — hardcoded dynasty player values
```javascript
// player_name (lowercase) → integer value on KTC scale (~1–9999)
// Snapshot taken April 2026 — update before 2026 season
const KTC_SNAPSHOT = { ... };
```
Used as fallback when live KTC fetch fails. Comment in code warns to update before each season.

### `KTC_PICK_VALUES` — pick values by year + round
```javascript
// year → { round: value }
const KTC_PICK_VALUES = { 2026: { 1: 2800, 2: 900, 3: 450, 4: 250 }, ... };
```

### `QUICK_PROMPTS` — AI quick prompt text
```javascript
// key → prompt string
// Keys: 'draft', 'trade', 'roster', 'waiver', 'rivalry', 'tes', 'contenders', 'myteam'
const QUICK_PROMPTS = { ... };
```

### `LEAGUE_CONTEXT` — AI system context string
Static multi-line string injected as preamble in every AI conversation. Contains all 12 teams, scoring rules, history, rivalries, and 2027 rule change.

### Runtime state variables
```javascript
let cachedRosters = null;    // Sleeper rosters array
let cachedPlayers = null;    // Sleeper players object { player_id: {...} }
let cachedLeague = null;     // Sleeper league object (current week etc.)
let cachedLeagueIds = null;  // { 2025: id, 2024: id, 2023: id }
let currentTxnYear = 2025;   // active year in Transactions tab
let currentTxnFilter = 'all'; // active type filter in Transactions tab
let currentTxnTeam = null;   // roster_id or null (team filter in Transactions tab)
let currentStatsYear = 2025; // active year in Player Stats tab
let currentStatsPos = 'all'; // active position filter in Player Stats tab
let currentStatsWeek = 'season'; // active week in Player Stats tab ('season' or 1–17)
let currentScoresYear = 2025; // active year in Scores tab
let currentScoresWeek = 1;   // active week in Scores tab
let _draftPicks = null;      // picks for the currently loaded past draft year (board view)
let _tradeInit = false;      // trade evaluator tab has been initialized
let _ktcValues = null;       // live KTC values if fetch succeeds; null = use snapshot
let _ktcSource = 'snapshot'; // 'live' or 'snapshot'
let aiMessages = [];         // running AI conversation history
```

---

## LOCALSTORAGE KEYS

| Key | TTL | Contents |
|-----|-----|----------|
| `tol_cache_v2` | 6h | Current season rosters (only current season) |
| `tol_theme` | permanent | User theme preference (`'dark'` or `'light'`) |
| `tol_lids` | permanent | Past league IDs `{ 2025: id, 2024: id, 2023: id }` |
| `tol_matchups_{year}` | permanent | All 17 weeks of matchup data for that season |
| `tol_txn_{year}` | permanent | All completed transactions for that season |
| `tol_drafts_{year}` | permanent | All draft picks for that season |
| `tol_stats_{year}` | permanent | Season stats for all dynasty roster players (aggregated from 17 weeks) |
| `tol_stats_wk_{year}_{week}` | permanent | Single-week stats for a specific year + week |

---

## KEY DESIGN DECISIONS (don't change without asking)

- **Non-PPR scoring** with TE premium (+0.5/rec) and distance bonuses — this affects all AI analysis context
- **Dark/light theme toggle** — persists via `localStorage`
- **LocalStorage caching** — Sleeper data cached for 6 hours to reduce API calls; cache key is `tol_cache_v2`
- **CORS fallback chain** — always try direct fetch first, then two proxy fallbacks
- **Roster chips colored by position** — QB=purple, RB=green, WR=blue, TE=orange, K=gray, DEF=red. Sections labeled separately (Starters / Bench / Taxi / IR)
- **Rivalries computed from 2025 forward** — pre-2025 matchups not included in rivalry records
- **2026 draft is linear, not snake** — rounds 2–4 follow the same order as round 1 (worst-to-best finish every round)

---

## LEAGUE CONTEXT SUMMARY (for AI features)

- 12 teams, dynasty format, ~Year 4
- Commissioner/user: Matt Bova — team "Show Me Your Penix" (mid-tier, between contender and rebuild)
- 2025 Champion: Jake Blackwell ("Nacua Matata") — gets pick 1.12
- 2025 Consolation: Nick Merkel ("Breeces Peanut ButterCups") — gets pick 1.13
- Contenders: Chris Bova, Jake Bogardus
- Active traders (best trade partners): Chris Merkel, Nick Merkel
- 2027 rule change already voted in: 1 WRRB_FLEX → WR/RB/TE FLEX (increases TE value significantly)
- Full context available in: `the-other-league-context.md`

---

## BACKLOG / NOT YET BUILT

- Post-playoff full bracket view (currently only regular-season final standings shown in Scores tab)
- Live roster data passed into Claude API calls (currently only static `LEAGUE_CONTEXT` string is injected)

---

## WHAT NOT TO DO

- Do not introduce React, Vue, npm, or any build tool without explicit discussion first
- Do not break the single-file structure
- Do not remove the CORS fallback chain from API calls
- Do not use `localStorage` for anything sensitive (API keys, personal data)
- Do not rewrite large sections of working code to fix a small issue — patch surgically
