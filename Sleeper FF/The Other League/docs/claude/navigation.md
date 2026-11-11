# Navigation and Element IDs — The Other League reference

Moved verbatim out of `CLAUDE.md` on 2026-11-11 so it loads only when needed. A cross-reference to another section may now point to a different `docs/claude/` file; grep the folder for the heading.

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
| 4 | **Moves** | `draft` | `panel-draft` | **Draft** (default) - Trades & Waivers - Draft ROI |
| 5 | Trade | `trade` | `panel-trade` | **Evaluator** (default) - Who Won That Trade? |

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

### Trade Panel (`panel-trade`)

Two views via `setTradeView('eval'|'roi', el)`, titles from `TRADE_VIEW_META`, same
self-contained-divs pattern as the other panels. **Scope selectors to `#trade-view-toggle`** —
an unscoped `.yr-btn` also matches the KTC table and draft toggles, which is the bug the Teams
panel already hit once.

0. `#trade-view-eval` (**"Evaluator"**) — the default; everything the tab used to be.
1. `#trade-view-roi` (**"Who Won That Trade?"**) — moved here from Moves 2026-09-04.

**Each view pays for its own data.** `setTradeView` lazy-inits the evaluator (KTC fetch) only when
the eval view opens, and `buildTradeROI()` only when the ROI view opens; `showTab` now gates its
`initTradeEval()` call on `_tradeView==='eval'`. Deep-linking `#whowon` therefore renders 52 cards
with **zero** KTC traffic — verified, `_tradeInit` is still false on that path.

`#whowon` / `#traderoi` were repointed at the Trade tab in the same change. **They were not
removed** — those hashes have been texted round the league; see the `TAB_ALIASES` rule.

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
- **It also pauses on `visibilitychange` (2026-09-04).** Leaving the site's own tab was already
  handled; backgrounding the *browser* tab was not. Chrome does not stop a hidden tab's intervals,
  it only throttles them — to roughly once a minute, then once an hour — so a Commissioner tab left
  parked went on re-fetching the whole registry for as long as the browser stayed open. That was
  visible as a wall of `ERR_CONNECTION_REFUSED` from a stale tab after the local server stopped.
  On return it re-probes **immediately** rather than showing numbers that went stale while away,
  and it only resumes when the panel is actually the active one and still unlocked.

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
`trade-roi.json`, different question.

**Who Won That Trade? moved OUT of Moves to the Trade panel on 2026-09-04** (Matt's call). Both
halves of the Trade tab are now about trades, Moves is back to three sub-views, and the two
`trade-roi.json` views ended up on different tabs — which is fine, because they answer different
questions and Draft ROI is a *draft* record, which is what Moves is for.

`#whowon`/`#traderoi` (trade view) and `#draftroi`/`#bestdrafter` (Draft ROI) are `TAB_ALIASES`
deep links — not retired hashes,
but so the page can be texted round the league and land on itself rather than the Moves default.

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
