# JS Functions: Data Layer, Teams, Moves, Trade, Boot — The Other League reference

Moved verbatim out of `CLAUDE.md` on 2026-11-11 so it loads only when needed. A cross-reference to another section may now point to a different `docs/claude/` file; grep the folder for the heading.

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

### Boot
- `startCountdown()` — countdown timer to **Sep 9, 2026 8:20 PM ET**; ticks every 1s
- `routeFromHash()` — reads `location.hash` on boot and navigates to matching tab
- `init()` — boot sequence: loads/caches rosters, builds leader stats, prefetches historical data in background
  **It also refreshes the live season's matchups and transactions (2026-10-06).** Before that only
  the Scores tab ever fetched `tol_matchups_<live year>`, so Rivalries, the H2H explorer, the
  nemesis board, the Hall of Fame and the career table showed whatever a browser cached on its
  last Scores visit — all six Week 4 rivalry games read "TBD" the day after they were played.
  **None of those views is fed by a weekly job, and none needs one:** they are computed in the
  browser from live Sleeper data on every load. The Tuesday bot's `h2h-records.md` is not read by
  the site at all. A stale History page is a caching bug, never a missed bot run.
