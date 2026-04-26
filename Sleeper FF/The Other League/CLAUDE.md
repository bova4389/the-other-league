# CLAUDE.md — The Other League Dynasty Dashboard

## WHAT THIS PROJECT IS

A personal fantasy football dashboard for "The Other League" — a 12-team dynasty league on the Sleeper platform. The site pulls live data from the Sleeper public API and the Anthropic API to display rosters, league history, draft picks, scoring rules, rivalries, and an AI analysis layer.

**Owner:** Matt Bova (commissioner). Built for personal use during development; eventually shared with league mates.

---

## PROJECT STRUCTURE

This is a **static HTML/JavaScript project** — no framework, no build step, no package manager. All files are plain `.html` with embedded CSS and JavaScript.

```
the-other-league/
├── index.html                              — root redirect to the dashboard
└── Sleeper FF/The Other League/
    ├── CLAUDE.md                           — you are here
    └── the-other-league-FINAL.html         — the working dashboard (all-in-one)
```

**Current state:** `the-other-league-FINAL.html` is the working file (~1,970 lines). It combines rosters, league info, scoring, rivalries, draft, transactions, career stats, and an embedded "Ask Claude" AI tab into one self-contained file.

**Deployment:** GitHub Pages (static hosting). `index.html` is an instant `<meta refresh>` redirect to the dashboard. No server, no backend. All API calls happen client-side from the browser.

---

## EXTERNAL APIS

### Sleeper API (no auth required)
- Base: `https://api.sleeper.app/v1`
- League ID: `1316225642072662016` (const `LID`)
- Endpoints actually fetched:
  - `/league/{LID}` — current league info (week, settings)
  - `/league/{LID}/rosters` — all 12 rosters
  - `/league/{LID}/matchups/{week}` — matchups for a specific week
  - `/league/{LID}/traded_picks` — all traded draft picks
  - `/league/{leagueId}/transactions/{week}` — adds, drops, trades, waivers
  - `/league/{leagueId}/drafts` — draft list for a season
  - `/draft/{draft_id}/picks` — all picks in a draft
  - `/players/nfl` — full player database (~5MB, slow)
- CORS note: Direct browser fetch may fail. Fallback proxies in order: `corsproxy.io`, `api.allorigins.win`

### Anthropic API
- Endpoint: `https://api.anthropic.com/v1/messages`
- Model: `claude-sonnet-4-20250514`
- Used for: the "Ask Claude" tab — AI analysis chat with full league context injected via `LEAGUE_CONTEXT`
- No API key handling needed in code (handled externally)

---

## TABS & PANELS

Each tab button calls `showTab(name, el)`. Panels use the ID `panel-{name}`.

| Tab Label | `showTab()` name | Panel ID | Notes |
|---|---|---|---|
| Scores | `scores` | `panel-scores` | Live week or off-season standings; lazy-loads matchup data |
| Rosters | `rosters` | `panel-rosters` | Live from Sleeper; player chips colored by slot type |
| League Info | `league` | `panel-league` | Payouts, format, waivers, playoffs — static HTML |
| Scoring | `scoring` | `panel-scoring` | Renders from `SDATA`; built on first view |
| Rivalries | `rivalries` | `panel-rivalries` | 6 matchups with all-time + year records; lazy-loads H2H data |
| Draft | `draft` | `panel-draft` | 2026 order + past years (2025/2024/2023); list and board views |
| Transactions | `transactions` | `panel-transactions` | Filterable log; player search across all seasons |
| Careers | `careers` | `panel-careers` | Earnings table and placements 2023–2025; built on first view |
| ⚡ Ask Claude | `ai` | `panel-ai` | Anthropic-powered chat; full context prepended to every message |

---

## KEY DATA OBJECTS (hardcoded `const` blocks)

| Name | Description |
|---|---|
| `LID` | Sleeper league ID string |
| `CACHE_KEY` | `'tol_cache_v2'` — localStorage key for current-season roster cache |
| `CACHE_TTL` | 6 hours in milliseconds |
| `TEAMS` | Maps user_id → `{name, team, you, tier, co?, note?}` for all 12 owners |
| `RM` | Maps roster_id (1–12) → user_id |
| `RMR` | Reverse of RM: user_id → roster_id |
| `RIVALS` | Array of 6 `{a: user_id, b: user_id}` rivalry pairs |
| `SEASON_HISTORY` | Keys 2023/2024/2025; each has `{buyin, pot, payouts, placements, consolation_winner?}` |
| `SLABELS` | Maps scoring stat keys → human-readable label strings |
| `SDATA` | Maps scoring stat keys → point values (all non-PPR scoring rules) |
| `DRAFT_ORDER_2026` | Array of 13 `{pick, uid, how}` objects for the 2026 rookie draft |
| `LEAGUE_CONTEXT` | Large string injected into every Anthropic API call (scoring, rosters, history, rivalries) |
| `QUICK_PROMPTS` | Maps prompt keys (`draft`, `trade`, `roster`, `waiver`, `rivalry`, `tes`, `contenders`, `myteam`) → preset prompt strings |

---

## KEY JAVASCRIPT FUNCTIONS

### Helpers
| Function | What it does |
|---|---|
| `t(uid)` | Returns TEAMS entry for a user_id, with fallback object if unknown |
| `rToTeam(rid)` | Converts roster_id to team object via RM |
| `pname(pid)` | Returns player full name from cachedPlayers, or `'#pid'` if missing |
| `ppos(pid)` | Returns player position from cachedPlayers, or `''` if missing |
| `fmtDate(ms)` | Formats epoch ms → `'Mon, Jan 01, 2025'` |
| `fmtDateShort(ms)` | Formats epoch ms → `'Mon, 01'` (abbreviated) |

### Theme & Cache
| Function | What it does |
|---|---|
| `toggleTheme()` | Toggles dark/light theme and saves to localStorage |
| `applyTheme()` | Reads theme from localStorage on page load |
| `saveCache(rosters)` | Writes rosters + timestamp to `tol_cache_v2` |
| `loadCache()` | Reads cached rosters; returns null if expired or missing |
| `clearCache()` | Deletes `tol_cache_v2` from localStorage |
| `savePerm(key, data)` | Saves to localStorage with no TTL (for historical season data) |
| `loadPerm(key)` | Reads from permanent localStorage (no expiry check) |
| `setCacheBar(fromCache, ts)` | Updates the cache status indicator bar in the header |
| `refreshData()` | Clears cache and re-fetches everything from Sleeper |

### API & Data Loading
| Function | What it does |
|---|---|
| `api(path)` | Fetches from Sleeper with CORS fallback chain (direct → corsproxy.io → allorigins) |
| `findLeagueIds()` | Walks `previous_league_id` chain to discover 2023/2024/2025 league IDs |
| `fetchAllMatchups(leagueId, year)` | Fetches all 17 weeks of matchups for a season; caches permanently |
| `buildH2HMap()` | Computes all-time H2H record map from all cached matchup seasons |
| `buildH2HForYear(year)` | Computes H2H record map for a single season |
| `fetchTransactions(leagueId, year)` | Fetches all 17 weeks of transactions for a season; caches permanently |

### Render — Scores Tab
| Function | What it does |
|---|---|
| `buildScores()` | Entry point for Scores tab; shows off-season standings or live week |
| `renderScoresOffseason(c)` | Renders 2025 final standings table during off-season |
| `renderScoresWeek(container, week)` | Renders matchup cards for a week with all-time H2H records |
| `changeScoreWeek(week)` | Switches scores view to a different week |

### Render — Rosters Tab
| Function | What it does |
|---|---|
| `buildRosters(rostersData, playersData)` | Renders all 12 roster cards with player chips colored by slot type |

### Render — Rivalries Tab
| Function | What it does |
|---|---|
| `buildRivalries()` | Renders all 6 rivalry cards with all-time + per-year records |

### Render — Draft Tab
| Function | What it does |
|---|---|
| `buildDraft2026()` | Populates 2026 draft order table (picks, trades, how earned) |
| `renderDraft2026Board()` | Renders 2026 picks as a team-column grid |
| `setDraft26View(view, el)` | Toggles list vs board view for 2026 draft |
| `setDraftYear(year, el)` | Switches draft view between 2026 order and past seasons |
| `buildDraftHistory(year)` | Fetches past-season draft picks and renders them |
| `renderDraftPicks(container, picks, year)` | Renders past draft picks as a table |
| `renderDraftBoard(picks, year)` | Renders past draft picks as team-column grid |
| `setDraftPastView(view, el)` | Toggles list vs board view for past draft results |

### Render — Transactions Tab
| Function | What it does |
|---|---|
| `buildTransactions(filter, year)` | Renders filtered transaction log |
| `populateTxnTeamDropdown()` | Populates the team filter dropdown |
| `setTxnTeam(value)` | Sets team filter and rebuilds transactions view |
| `setTxnYear(year, el)` | Switches transactions to a different season |
| `setTxnFilter(type, el)` | Switches filter type (all / waiver / free_agent / trade) |
| `onTxnPlayerSearch(val)` | Debounced handler for player history search input |
| `runPlayerSearch(query)` | Searches all seasons for a player's transactions |
| `renderTxnRow(tx)` | Renders a single add/drop transaction row |
| `renderTxnTrade(tx, date)` | Renders a trade card with both sides |
| `clearPlayerSearch()` | Clears player search input and hides results |

### Render — Careers Tab
| Function | What it does |
|---|---|
| `buildCareers()` | Renders career stats table: earnings, placements per year, avg finish |

### Render — Header Stats
| Function | What it does |
|---|---|
| `buildLeaderStats()` | Computes and renders all 7 leader stat pills in the header |

### Render — Sidebar & Navigation
| Function | What it does |
|---|---|
| `buildSidebar()` | Populates the team list sidebar with clickable team items |
| `scrollToTeam(uid)` | Switches to Rosters tab, scrolls to that team's card |
| `buildScoring()` | Renders scoring rules grid from SDATA |
| `showTab(tab, el)` | Activates a panel and triggers lazy-load for that tab |

### AI Chat
| Function | What it does |
|---|---|
| `quickPrompt(key)` | Fills AI input with a preset prompt from QUICK_PROMPTS and sends |
| `clearChat()` | Clears AI message history |
| `addMsg(role, content)` | Adds and renders a message in the chat history |
| `sendAI()` | Posts to Anthropic API with LEAGUE_CONTEXT + conversation history |

### Init
| Function | What it does |
|---|---|
| `init()` | Page entry point: loads rosters, inits sidebar/stats, prefetches historical data |

---

## LOCALSTORAGE KEYS

| Key | Lifetime | Purpose |
|---|---|---|
| `tol_cache_v2` | 6-hour TTL | Current-season rosters + fetch timestamp |
| `tol_theme` | Permanent | User theme preference (`dark` or `light`) |
| `tol_lids` | Permanent | Past league IDs discovered via `previous_league_id` chain |
| `tol_matchups_2025` | Permanent | All 17 weeks of 2025 matchup data |
| `tol_matchups_2024` | Permanent | All 17 weeks of 2024 matchup data |
| `tol_matchups_2023` | Permanent | All 17 weeks of 2023 matchup data |
| `tol_txn_2025` | Permanent | All 2025 transactions |
| `tol_txn_2024` | Permanent | All 2024 transactions |
| `tol_txn_2023` | Permanent | All 2023 transactions |
| `tol_drafts_2025` | Permanent | 2025 draft picks |
| `tol_drafts_2024` | Permanent | 2024 draft picks |

---

## HEADER STAT PILLS

Seven stat pills rendered in the header by `buildLeaderStats()`:

| Label | Element ID | Notes |
|---|---|---|
| 🏆 Past Champions | `stat-champs` | All champions 2023–2025 with year |
| 💰 Highest Career Earnings | `stat-earn-val` / `stat-earn-sub` | Computed from `SEASON_HISTORY.payouts` |
| 🏅 Most Career Wins | `stat-wins-val` / `stat-wins-sub` | Hardcoded to 55 (Chris Bova) |
| 🎯 Most Consistent Finisher | `stat-cons-val` / `stat-cons-sub` | Best average placement across all seasons |
| 📋 Most Draft Picks | `stat-picks-val` / `stat-picks-sub` | Computed from `DRAFT_ORDER_2026` + live traded_picks |
| 🔄 Most Trades Completed | `stat-trades-val` / `stat-trades-sub` | Computed from cached transaction data |
| 📉 Worst Average Finish | `stat-worst-val` / `stat-worst-sub` | Worst average placement across all seasons |

---

## HOW TO WORK ON THIS PROJECT

### Always plan before acting
Before making any changes, present a written plan of what you intend to do and wait for approval. Do not edit files speculatively. Token efficiency matters — avoid redundant reads and unnecessary rewrites.

### Verify in browser
The only way to test is to open the HTML file in a browser. There is no local dev server, no test suite, and no linter. After changes, confirm the file opens without console errors and the relevant feature works visually.

### Comment all code in plain English
Every meaningful block of code — functions, event handlers, API calls, render loops — should have a short comment above it in plain English explaining what it does. Matt is not an engineer; the code should be readable by a non-technical person.

Example:
```javascript
// Fetch all rosters from Sleeper and render player chips for each team
async function buildRosters() { ... }
```

### Keep everything in one file
Do not split CSS, JS, or HTML into separate files. GitHub Pages serves static files and the project is intentionally self-contained. All styles go in `<style>`, all scripts go in `<script>`, inside the single `.html` file.

---

## KEY DESIGN DECISIONS (don't change without asking)

- **Non-PPR scoring** with TE premium (+0.5/rec) and distance bonuses — this affects all AI analysis context
- **Dark/light theme toggle** — persists via `localStorage` key `tol_theme`
- **LocalStorage caching** — current season rosters cached for 6 hours (`tol_cache_v2`); historical data (matchups, transactions, drafts) cached permanently since past seasons don't change
- **CORS fallback chain** — always try direct fetch first, then two proxy fallbacks
- **Roster chip colors**: green = starter, blue = taxi squad, orange = IR/reserve
- **Lazy loading** — expensive tabs (Rivalries, Transactions, Careers, Draft History) only build on first click

---

## LEAGUE CONTEXT SUMMARY (for AI features)

- 12 teams, dynasty format, ~Year 4
- Commissioner/user: Matt Bova — team "Show Me Your Penix" (mid-tier, between contender and rebuild)
- 2025 Champion: Jake Blackwell ("Nacua Matata") — gets pick 1.12
- 2025 Consolation: Nick Merkel ("Breeces Peanut ButterCups") — gets pick 1.13
- Contenders: Chris Bova, Jake Bogardus
- Active traders (best trade partners): Chris Merkel, Nick Merkel
- 2027 rule change already voted in: 1 WRRB_FLEX → WR/RB/TE FLEX (increases TE value significantly)
- Full context for AI chat lives in the `LEAGUE_CONTEXT` const in the HTML file

---

## PLANNED FEATURES (not yet built)

- Post-playoff full bracket view (currently shows regular-season placements only)
- Matchup history and schedule viewer (weekly scores exist; full schedule grid does not)
- Expanded AI context (pass live roster data into Claude calls; currently context is static)

---

## WHAT NOT TO DO

- Do not introduce React, Vue, npm, or any build tool without explicit discussion first
- Do not break the single-file structure
- Do not remove the CORS fallback chain from API calls
- Do not use `localStorage` for anything sensitive (API keys, personal data)
- Do not rewrite large sections of working code to fix a small issue — patch surgically
