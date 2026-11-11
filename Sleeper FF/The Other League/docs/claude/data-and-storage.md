# Data Objects and localStorage Keys — The Other League reference

Moved verbatim out of `CLAUDE.md` on 2026-11-11 so it loads only when needed. A cross-reference to another section may now point to a different `docs/claude/` file; grep the folder for the heading.

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
| `tol_txn_{year}` | permanent (2023–2025); **1h TTL for the current season** (+ cleared on Refresh) | All completed transactions. The live season was permanent until 2026-10-06, which froze the 2026 trade log and the Hall of Fame Trades / Waiver Wire Warrior cards at each browser's first visit. A refresh with any failed week keeps the old copy rather than saving a log with a hole in it. |
| `tol_txn_ts_{year}` | permanent | Fetch stamp for the TTL above, same pattern as `tol_matchups_ts_{year}`. |
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
