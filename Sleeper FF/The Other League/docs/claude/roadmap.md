# Development Roadmap (all phases but 6 and 12) — The Other League reference

Moved verbatim out of `CLAUDE.md` on 2026-11-11 so it loads only when needed. A cross-reference to another section may now point to a different `docs/claude/` file; grep the folder for the heading.

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
   **Team names come from here too, and only from here.** The script reads them live from that
   season's `/league/{lid}/users` on every run and prints them at the top; it used to carry a
   hardcoded `OWNER_TEAM` table that was seven names stale by Week 7 of 2026, so every write-up
   quoted the August names. For the live season it also warns about any old name (from
   `TEAM_NAME_HISTORY`) found in either JSON file, and about any `TEAMS` entry in `index.html`
   that no longer matches Sleeper. **Clear every warning before committing a week.** When `TEAMS`
   is stale, update it and append a new 2026 row to `TEAM_NAME_HISTORY`, never overwrite one.
   The one expected warning is "Joshin Around" in Week 4, which is history on purpose.
2. `weekly-recaps-<year>.json` — one entry keyed by week number:
   `{headline, facts: [{k,v}], paragraphs: []}`. 2–3 paragraphs, **about 200 words in all, 250 at
   most** (see "The saved recap image" below for why): longer than a matchup write-up, shorter
   than a season recap. 3–5 `facts` reads best; past 6 the strip wraps badly on mobile.
3. `matchup-commentary-<year>.json` — one entry per game keyed `"week|matchup_id"`, unchanged
   Phase 8 shape and voice.
4. **Do NOT write survivor eliminations into either file.** The tracker computes them. The only
   thing to check is that the week's scores are final on Sleeper before pointing anyone at it.

**The saved recap image is shaped like an iPhone screen** (Matt, 2026-10-21, same change as
Commish Hub's `778d727`). **Save image** / **Preview image** on the recap card draw an off-screen
copy at 393 × 852 points and save it at 3×, so 1179 × 2556, which fills a phone with no
scrolling. It used to save 720px wide, which a phone shrinks to about 55%, so body text read at
about 8.5pt. `fitRecapPhone()` tries text sizes from 21px down and keeps the largest one where
the whole card fits, so a short week comes out big and a long one smaller. **Below 11px it stops
shrinking** and the image runs taller instead (Matt's call over "fit at any size"). Every size in
the `.wr-card.exporting.phone` CSS is `calc(var(--fs) * k)`, not `em`, because `.sv-tm` and
`.sv-flag` sit inside `.sv-line` and `em` would compound. The fit waits for
`document.fonts.ready`, or it measures fallback fonts and overflows once the real ones load.

**Why the word budget is 200, not the hub's 300.** TOL's image also carries the logo header, URL
footer and the survivor block, and in mid-season the survivor block is about a quarter of the
screen. Measured 2026-10-23 at the 11px floor with the Week 3–4 survivor block: Week 3 (211 words)
ran 858px tall, 6px over; Week 1 (252) ran 908; Week 4 (329) ran 973, about 14% taller than the
screen. A 96-word test fit at 13.25px. So about 200 words fits one screen and 250 runs about 6%
over. The block shrinks as teams are eliminated and disappears after Week 12, so late-season
weeks have more room.

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
