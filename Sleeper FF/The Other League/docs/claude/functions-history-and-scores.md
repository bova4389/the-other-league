# JS Functions: History, Scores, Recaps, Rivalries, Profiles — The Other League reference

Moved verbatim out of `CLAUDE.md` on 2026-11-11 so it loads only when needed. A cross-reference to another section may now point to a different `docs/claude/` file; grep the folder for the heading.

## JAVASCRIPT FUNCTIONS (continued)

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

### Rivalries
- `buildRivalries()` — renders 6 rivalry cards covering 2023–2026 (see KEY DESIGN DECISIONS); re-renders on every tab visit and when the boot prefetch lands; always shows a "2026: TBD · W4 W13" placeholder row for each rivalry until live matchup data is available. Also calls the three Phase 2 builders below, every visit.
- `buildH2HForYear(year, maxWeek)` — builds H2H map from cached matchup data for a single year (up to `maxWeek`; default 17)
- `findRivalWeeks(year, ridA, ridB, maxWeek)` — returns sorted list of week numbers where two roster IDs faced each other (default `maxWeek=14`)

### Head-to-Head Explorer + Nemesis Board (Phase 2 — built 2026-08-21)
Deliberately a **different question** from the 6 `RIVALS` cards above: "any two managers, ever," not just the 6 pairs the league formally calls rivals. It walks every cached season back to 2023, same guards as `buildH2HMap` (`weekWasPlayed`, `REG_WEEKS`-capped), so it can never disagree with the all-time totals shown elsewhere on the site. Verified against synthetic matchup data covering a win, a loss, a tie, an unplayed week (all-zero points) and a week 15 game — the unplayed week and the post-`REG_WEEKS` week are both correctly excluded, and win/loss/tie/margin/chronological-sort all came back exact.

- `buildAllTimePairs()` — one walk over `tol_matchups_{year}` for 2023–2026, grouping every regular-season matchup by roster-id pair (keyed `lo|hi`, lower roster_id first) into a `games[]` array. Not memoized — recomputed on every `buildRivalries()` call, same as `buildH2HMap`; cheap at this data volume (4 seasons × 14 weeks × 6 games).
- `pairView(pairs, ridX, ridY)` — orients one pair's games to `ridX`'s point of view: `{w, l, tie, gp, pf, pa, avgMargin, games[]}`, sorted chronologically. Returns `null` when the two have never played a regular-season game against each other — a normal state (most of the 66 possible pairs have only 1–2 meetings across 4 seasons, some none at all), not an error condition; callers render a plain sentence for it rather than an empty table.
- `computeNemesisMap(minGames)` — thin wrapper over `buildH2HMap()`: per manager, the opponent with the worst win% among opponents played at least `minGames` times (Nemesis Board uses 2), tie-broken toward more losses. Gating on a minimum sample means one loss to someone played only once can't crown a "nemesis."
- `buildH2HPicker()` — renders the 12×12 clickable grid into `#h2h-picker-grid`. Cell color: `.lead`/`.trail`/(default) via `--accent`/`--accent3`, matching the fav/dog-style axis used elsewhere on the site. Clicking a cell calls `selectH2HPair`.
- `selectH2HPair(ridX, ridY)` / `renderH2HDetail()` — `_h2hSelected` is a module-level var that persists across re-renders (a Rivalries tab revisit doesn't lose the pair you had open). Detail card reuses `.riv-card`/`.riv-at-row`/`.riv-history` wholesale from the existing rivalry cards, plus a `.dtbl` game log table with a `goToScoresWeek` link per game, same pattern as the official rivalry cards' week links.
- `buildNemesisBoard()` — renders `#nemesis-board` as a 12-row `.dtbl`, one row per manager sorted by name, reusing `.hof-sub` for the record text. "Not enough data yet" for anyone with no opponent meeting the 2-game minimum.

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
