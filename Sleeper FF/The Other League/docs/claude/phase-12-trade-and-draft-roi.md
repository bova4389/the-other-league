# Phase 12: Trade ROI + Rookie Draft ROI — The Other League reference

Moved verbatim out of `CLAUDE.md` on 2026-11-11 so it loads only when needed. A cross-reference to another section may now point to a different `docs/claude/` file; grep the folder for the heading.

## DEVELOPMENT ROADMAP (continued)

### Phase 12 — Trade ROI + Rookie Draft ROI — **step 1 (data layer) shipped 2026-09-03**

**Goal:** Two new sub-views under the Moves panel: **"Who Won That Trade?"** (a scored card per
trade, every trade in league history) and **"Rookie Draft ROI"** (best-drafter leaderboard +
a hot-spot board showing which draft slots over-deliver).

Both are sub-views of `panel-draft` (Moves), joining Draft and Trades & Waivers. **Not a new
top-level tab** — see the nav-budget rule in WHAT NOT TO DO.

---

#### Feasibility — verified against live Sleeper data 2026-09-03

**Pick → player tracing is exact, not fuzzy.** This was the open question and it is closed.
Each trade's `draft_picks[]` entry carries `roster_id` = the pick's **original** owner (plus
`previous_owner_id` and `owner_id` for the hop). Each draft object carries `slot_to_roster_id`
mapping draft slot → original owner. So:

> `(season, round, original_owner_roster_id)` → the unique pick in that season's draft where
> `round` matches and `slot_to_roster_id[draft_slot] == original_owner` → its `player_id`.

`(round, draft_slot)` was confirmed unique in every draft. Measured result across all 4 seasons:

```
52 trades   (2023: 10 · 2024: 26 · 2025: 9 · 2026: 7)
74 traded pick assets
   58 → resolved to the actual drafted player
   16 → genuine future picks (2027/2028), priced from KTC
    0 → unresolved
```

Do **not** reach for name matching or `pick_no` arithmetic here. `pick_no` is
`(round-1)*12 + draft_slot`, which is *not* contiguous — each season has a lone round-5
consolation bonus pick (2024 pick_no 51 · 2025 pick_no 53 · 2026 pick_no 52), so every draft
has 49 picks with pick numbers running past 48.

**2023 is excluded from rookie ROI because it was not a rookie draft.** It was the 29-round
startup **auction** (348 picks, `metadata.amount` present). 2024/2025/2026 are 4-round linear
rookie drafts, 49 picks each. Rookie ROI universe = 147 picks, of which 98 have played a down.

**Roster 11 changed managers.** CCJ managed it 2023–2025; Andrew Bova took it over in 2026.
Every leaderboard must attribute a move to the **manager at the time of the move**, not the
current roster owner. All other 11 rosters are continuous across all four seasons.

**League chain** (`previous_league_id`): 2026 `1316225642072662016` · 2025 `1196516179326291968`
· 2024 `1048702761132478464` · 2023 `959292811319287808`.

**Trades live in `/transactions/{week}` for weeks 1–18.** Week 0 is empty in all four seasons —
do not bother fetching it. Offseason trades land in week 1 of the upcoming season's league.
Filter on `type == 'trade'` **and** `status == 'complete'`.

---

#### Known data gaps — fix these BEFORE building either page

**1. `stats-history.json` is structurally incomplete for this feature.**
`generate_stats.py` seeds its player list from `/league/{lid}/rosters` — i.e. only players
rostered *at the moment the script ran*. Anyone traded, busted and dropped is missing. Of the
208 players in the trade + rookie-draft universe, 74 have no 2025 season line, and **14 of
those have real 2025 stats on Sleeper**. Those 14 are exactly the population these pages exist
to expose: the busts. Scoring them as 0 would silently flatter whoever traded them away.

The fix: seed the universe from the **union** of (a) every `adds` key in every trade,
(b) every `player_id` in every draft's picks, and (c) every season's rosters — then fetch. Keep
the atomic-write discipline (temp file + `os.replace`, never `open(path,'w')` on a 1.2 MB file).

**2. There is no historical KTC and there never will be.** We only ever snapshot *current*
values, so "what was this worth on trade day" is unrecoverable for past trades. This is why the
score is performance-based rather than value-delta based. Do not try to reconstruct it.

**3. 2026 has zero games played** (season opens 2026-09-09). All 7 of the 2026 trades score
0–0 until real weeks land, and `scripts/tuesday_update.py` does **not** currently extend
`stats-history.json`. Adding 2026 weekly accrual to the Tuesday bot is part of this phase.

---

#### Scoring model — decisions locked 2026-09-03

**Metric: points over replacement (PoR).** Fantasy points via `calcPts()`/`SDATA`, minus what a
replacement-level player at that position produced over the same span. Raw points were rejected
because in a superflex league whoever receives the QB always "wins" — a QB-for-RB trade can read
412 vs 289 on raw points and flip the moment replacement level is applied.

**Replacement ranks are measured, not assumed.** Derived from the actual positional distribution
of started players across 42 real league-weeks (2023–2025, weeks 1–14, `/matchups/{week}`
`starters`), against `roster_positions` = 1 QB / 2 RB / 2 WR / 1 TE / 1 FLEX / 3 WRRB_FLEX /
1 SUPER_FLEX (11 starters, 12 teams):

| Pos | Avg started per league-week | Replacement |
|-----|-----------------------------|-------------|
| WR  | 55.6 | **WR57** |
| RB  | 37.0 | **RB38** |
| QB  | 22.2 | **QB23** |
| TE  | 17.0 | **TE18** |

Compute replacement **per position per week**, not per season — that is what absorbs bye weeks
and injury weeks correctly. Baselines must be computed over the **full NFL player pool** from
`/stats/nfl/regular/{y}/{w}`, not over `stats-history.json` (which only holds league-relevant
players and would put replacement level far too high). Bake the result into a small
`replacement-levels.json` keyed `year → week → position → points`.

**Credit rule (v1): points credit to the trade forever.** All points a player scores after the
trade date count toward that trade, whether or not the acquirer kept him. This is the pure "who
got the better asset" reading and the math is unarguable. Two richer rules were considered and
deferred: *realized value* (stop the clock when the acquirer gives him up — needs week-by-week
roster reconstruction from the transaction log) and *chaining* (B's return becomes whatever B
later got for the player, recursively). Chaining is the most interesting version of this page;
build it as Phase 12b on top of a working v1, not instead of one.

**Window.** Start = trade `created` (ms epoch) mapped to (season, week); offseason trades start
at week 1 of the coming season. End = today, recomputed on every page load — that is what makes
the page "continually update" for free, with no stored scores to go stale.

**Score shape: margin + verdict chip.** Each side's PoR total, the margin, and a verdict:
`DEAD EVEN` / `EDGE` / `CLEAR WIN` / `ROBBERY`. Thresholds should combine an absolute PoR floor
with a relative gap so a tiny two-bench-player swap can never earn `ROBBERY`. No 0–100 score
(the normalization would be arbitrary and would move the argument onto the formula) and no
letter grades (they hide the margin — a blowout and a squeaker both read as A/C).

**Maturity gate.** Cumulative PoR is the honest answer to "who won," but a 2024 trade has two
seasons of payout and an August 2026 trade has none. Every card carries a maturity meter (weeks
elapsed + games played by its assets), and a trade under the threshold gets a **TOO EARLY TO
CALL** stamp *instead of* a verdict — never a verdict computed off three games. Any trade still
holding an undrafted 2027/2028 pick is automatically unsettled.

**Picks, and the units problem.** KTC values are in the thousands; PoR is in the hundreds. They
cannot be summed. Resolve it with an **empirical pick curve built from this league's own
history**: for each rookie draft slot, the average PoR its selection has produced (2024 + 2025
classes). An unresolved future pick converts to expected PoR through that curve, rendered in a
visually distinct "projected" treatment so nobody reads it as earned points. Use KTC only to
*rank* an unresolved pick's likely slot, never as a score term directly. This curve is shared
with the Rookie Draft ROI view, which keeps the two pages consistent by construction.

**FAAB.** Only 2 of 52 trades moved waiver budget. Display it on the card; do not attempt to
score it. There is no defensible FAAB→points conversion at this sample size.

---

#### Rookie Draft ROI view

Scored off the same PoR engine and the same pick curve.

- **Best drafter** = Σ (actual PoR − expected PoR for that slot) across every pick a manager
  made, attributed to the manager at the time of the pick. Show per-class and all-time.
- **Hot spots** = a round × slot board heat-mapped by average PoR-over-expected, answering
  "where in this draft does value actually hide."
- **Draft capital board** — what a pick at each band actually buys: hit rate, median
  PoR, `usage_pct`, and crucially `avg PoR given a role`. See "Draft capital,
  opportunity and class strength" below; this is a required part of the view, not a
  nice-to-have. Reporting a late pick's PoR without its opportunity invites the wrong
  conclusion in both directions.
- **Show pooled AND class-adjusted** over/under-expectation per manager.
- **Sample-size honesty is mandatory on this view.** Only 2 classes (98 picks) have played:
  2024 has two seasons, 2025 has one, 2026 has none. With a sample this thin, fit a smooth
  decay curve across all picks rather than using raw per-slot averages — a raw slot average over
  two observations is noise. Say so on the page; do not present a 2-pick cell as a finding.

---

#### Build order

1. ~~**Data layer.**~~ **Done 2026-09-03.** See "Step 1 as built" below.
2. ~~**`scripts/build_trade_roi.py` → `trade-roi.json`.**~~ **Done 2026-09-04.**
   See "Step 2 as built" below.
3. ~~**Moves > Who Won That Trade?**~~ **Done 2026-09-04.** See "Step 3 as built" below.
4. ~~**Moves > Rookie Draft ROI** + hot-spot board.~~ **Done 2026-09-04.** See "Step 4 as built".
5. ~~**Tuesday bot extension**~~ **Done 2026-09-03** — pulled forward ahead of items 2-4 because
   the season opens 2026-09-09. See "Step 5 as built" below.

**Complexity: High.** The data layer is the majority of the work and the only part that is hard
to get right; both views are rendering once it exists.

---

#### Step 1 as built (2026-09-03)

`stats-history.json` regenerated, `replacement-levels.json` created, both committed.

**Universe widened, verified against the old file.** 2023 346→391 players, 2024 342→423,
2025 340→441; file 1.21→1.32 MB. **Zero regressions** — every player and every stat value in
the previous file is present and identical in the new one. 10 players were recovered into 2025
alone (Sterling Shepard, Khalil Herbert, Isaac Guerendo, Malachi Corley, Cade Stover, Tyler
Conklin, Jamari Thrash, Mason Rudolph, Jarrett Stidham, Mecole Hardman).

A further 6 traded/drafted players stay absent **and that is correct**: Sleeper returns only
`gms_active` and `pos_rank_*` for them, with no production of any kind. There is no stat line
to score, and absence already reads as zero. Do not "fix" this by inventing rows for them.

**`pass_int_td` was added to `STAT_KEYS`.** `calcPts()` has always read it (pick-six thrown,
−1) but the generator never wrote it, so the site could not score it. Now collected.

**The live season is omitted from the file entirely, on purpose.** `fetchWeekStats()` treats
the mere *presence* of a week key as data — it does not check whether the object is empty — and
then `savePerm()`s the result forever. A written-out `"2026":{"weeks":{"1":{}}}` would have
pinned every player to zero for the whole live season, permanently, per visitor. `generate_stats.py`
now omits empty weeks and omits a year with no played weeks. Keep it that way.

**Replacement baselines.** `replacement-levels.json` (2.6 KB) holds year → week → position →
points, from a 5-player band centered on the replacement rank rather than a single rank, because
one boom game by the exact Nth player would otherwise swing every PoR figure that week. Season
means came out QB 10.2–11.1 · TE 9.0–9.5 · RB 5.9–6.8 · WR 6.3–6.4 — stable across all three
seasons, TE above RB/WR as the 0.5/catch TE premium and a 12-team TE pool imply.

Baselines are computed over the **whole NFL pool** from `/stats/nfl/regular/{y}/{w}`, never over
`stats-history.json` — that file is already filtered to league-relevant players and ranking
inside it would set replacement far too high.

**Scoring parity is verified, not assumed.** `calc_pts()` in `build_replacement_levels.py` was
checked field-by-field against `calcPts()` and `SDATA` in `index.html`, *and* against the live
`scoring_settings` from the league API: 27 keys, zero differences, no field read by one and not
the other. If you touch either scorer, re-run that check.

**PoR does what it was chosen to do.** 2025 raw-points top 12 contains 5 QBs with Josh Allen
2nd; the PoR top 12 contains 1 QB with Allen 7th, led by McCaffrey / Nacua / Taylor / Robinson.

**One inherent 0.1 discrepancy, do not chase it.** PoR sums per-week `calcPts` (each rounded to
1dp, because replacement is weekly), while the Player Stats table rounds the season aggregate
once. McCaffrey 2025 is 383.5 by the first method and 383.4 by the second. That is rounding, not
a bug, and the weekly method is the correct one for PoR.

**`measure_starter_mix.py` needs the played-week guard.** Its first run reported 56 league-weeks
and WR 53.7, because Sleeper serves `starters` for unplayed 2026 weeks that managers have already
set lineups for — the same "an unplayed week is not an absent week" trap that once booked phantom
losses into the median math. Gated on `points > 0` it reproduces 42 league-weeks and
QB 22.2 / RB 37.0 / WR 55.6 / TE 17.0 exactly.

---

#### Step 2 as built (2026-09-04) — the PoR engine

`scripts/build_trade_roi.py` → `trade-roi.json` (104 KB, committed). All 52 trades
expanded, all 147 rookie picks scored, the pick curve fitted, verdicts assigned.

**The engine reconciles by hand.** Baker Mayfield from the 2023-10-30 trade:
PoR 345.6, raw 778.0, 41 weeks — identical to an independent recomputation straight
off `stats-history.json` + `replacement-levels.json`. Pick tracing spot-checked the
same way (2025 R2 originally roster 1 → pick 16, slot 4 → Luther Burden).

**PoR is floored at zero per asset, and this is the single most important decision
in the file.** 31% of traded assets score negative before the floor, some past -60
(Cade Stover -78 as a 4th-round rookie TE, Mecole Hardman -65). Nobody ever started
those players. A rostered asset's true floor is zero, because a manager benches a
bust rather than paying a replacement-level penalty every week — and scoring the raw
negative made **dumping** a bust register as a +65 win for the team that gave him
away, which inverts the whole question the page asks. `por_signed` keeps the real
number for display (a BUST tag reads off it); it never enters a margin.

**A week counts only when the player recorded something scoreable.** A bare `gp`
line means he dressed and did nothing, which is a benched player, not a cost. Weeks
he missed contribute nothing — availability is already captured, because PoR is a
cumulative sum and a player who misses six games simply banks six fewer weeks.

**Four trades are reversals and get no verdict.** Ja'Marr Chase moved roster 10 → 8
and straight back **17 minutes later**, the same 2025 3rd going the other way each
time; Jaylen Wright the same across 14 hours. Distinct `transaction_id`s, so nothing
upstream dedupes them, but scoring both halves publishes two mirror-image ROBBERY
verdicts and tells the league that two managers each robbed the other on the same
afternoon. `find_reversals()` matches a later trade whose asset flows are the exact
inverse of an earlier one between the same rosters inside 48h.

**Thresholds were set from the real distribution, not picked in the abstract.**
Absolute |margin| percentiles across the 52 trades: p25=0, p50=27, p75=93, p90=166,
p100=346. Hence `EDGE 25` (just under the median), `CLEAR 75` (~p75),
`ROBBERY 150` (~p90) — plus a **3× ratio gate** on ROBBERY so a blowout where both
sides got real value stays a CLEAR WIN. A 390-vs-107 trade is lopsided, but the
loser still got a starter, and spending the word "robbery" there devalues it for the
trades where someone genuinely got nothing. Maturity gate is 8 scored weeks (~p25,
about half a season from the busiest asset).

Result: **33 of 52 graded** — DEAD EVEN 12, EDGE 10, CLEAR WIN 9, ROBBERY 2.
Withheld: 15 TOO EARLY TO CALL (10 still hold an undrafted pick, 5 too new), 4
REVERSED. Both robberies are genuinely lopsided (Baker Mayfield for what became
Javon Baker; Josh Jacobs + a pick that became Tetairoa McMillan for Rome Odunze + a
pick that became Jaylin Noel).

**The pick curve is fitted, not averaged.** Only 2 classes (98 picks) have played, so
a raw per-slot average is the mean of two observations. `build_pick_curve()` smooths
over a ±6-pick window then clamps monotone-decreasing, so a noisy pair at pick 9
cannot make pick 9 worth more than pick 3. Round averages get the same clamp and it
matters: raw they were `{1: 96.3, 2: 29.6, 3: 4.6, 4: 14.0, 5: 42.2}` — round 5 is
**two picks** (Trey Benson, Jaxson Dart) and round 4 is carried by Bucky Irving, so
untreated a traded 2027 4th would have priced above a 2027 3rd. Clamped:
`{1: 96.3, 2: 29.6, 3: 4.6, 4: 4.6, 5: 4.6}`.

Rookie-year PoR is the curve's basis rather than career PoR, so a 2024 pick cannot
out-rank a 2025 pick purely on having had an extra season to accumulate.

**Aggregate every leaderboard on `manager_index` (user_id), never on display name.**
Roster 9 is one human under two names — Mblack2889 in 2023/24, MJBlack from 2025 —
and keying on the name split his draft record across two rows and ranked him twice.
Roster 11 is the opposite trap and must not be merged: CCJ 2023-25, Andrew Bova from
2026, two people on one roster_id. Every row therefore carries the manager resolved
for **its own season**, and `manager_index` carries the canonical name plus
`names_seen` so an old row can be captioned with the name current at the time.
13 entries for 12 rosters, which is the correct count.

**First look at the output, for reference when the view is built.** Best drafter by
Σ(actual − expected) over the 2024+2025 classes: cbova1222 +380 (Bo Nix 237.5 and
Jayden Daniels 219.0, the two best rookie seasons in league history), jblack511 +245,
CHRISMERKELDUH +179; avobttam −150 and MJBlack −145 at the bottom. Face-valid.

**Bot wiring done 2026-09-04** — the Tuesday workflow now rebuilds all three data files in
dependency order every week. See "Automation (Tuesday Bot)" for the chain and the silent
failure mode `coverage_gaps()` exists to prevent.

---

#### Draft capital, opportunity and class strength (2026-09-04)

Matt's question: a pick's production should be read against its draft capital,
because "rounds 3 and 4 are given 0 chance whereas a top 3 pick might have been an
easy pick to make." Three things came out of testing that against the data, and all
three are now in `trade-roi.json`.

**The claim is right in outcome and wrong in mechanism, and the difference matters.**
Late picks are not benched — only 3/24 round-3 and 4/26 round-4+ picks never recorded
a scoreable week, and most had at least one week above replacement. What collapses is
**volume and quality together**:

| Band | n | hit rate | median PoR | usage pct | never used | got a role | avg PoR *given* a role |
|---|---|---|---|---|---|---|---|
| 1.01–1.03 | 6 | 83% | 118.8 | 85% | 0/6 | 6/6 | 123.5 |
| 1.04–1.06 | 6 | 83% | 99.8 | 82% | 0/6 | 6/6 | 108.2 |
| 1.07–1.12 | 12 | 67% | 72.0 | 61% | 1/12 | 10/12 | 89.8 |
| Round 2 | 24 | 12% | **0.0** | 46% | 0/24 | 21/24 | 33.8 |
| Round 3 | 24 | 4% | **0.0** | 34% | 3/24 | 16/24 | 6.9 |
| Round 4+ | 26 | 12% | **0.0** | 37% | 4/26 | 18/26 | 23.0 |

The **median rookie PoR in rounds 2, 3 and 4 is 0.0** — the typical pick after round 1
returns nothing at all. But note round 2: 21 of 24 got a real role and it still only
hit 12% of the time, and the `avg PoR given a role` column keeps falling long after
the opportunity gap closes. **So opportunity explains part of the cliff, not all of
it.** Do not let the page claim late picks merely "never got a chance" — they got a
smaller chance and were worse with it. Both columns are published for that reason.

"Top 3 is an easy pick" holds up (83% hit rate at 1.01–1.06) but is not free: Cameron
Ward at 1.03 returned 10.2 and Travis Hunter at 1.06 returned 9.9.

**`usage_pct`, not raw touches, for any cross-band claim.** Raw touches first reported
the 1.01–1.03 band at 384 against 75 for 1.04–1.06, which reads as the top three picks
getting five times the opportunity. They were not — that band happened to hold Caleb
Williams, Jayden Daniels and Cameron Ward, and a quarterback's pass attempts dwarf a
running back's carries. `Engine.usage_percentile()` ranks a player within his own
position and season; raw `touches` is kept only for a single player's own card.

**Class strength is a real confound and is now adjusted for.** The 2024 class produced
**2.39x** the total PoR of 2025 (2506 vs 1048); round 1 alone averaged 135.8 against
56.9. Both are measured over one rookie season each, so that is class quality, not one
class having had longer to accumulate. `class_factors` (2024: 1.41, 2025: 0.59) scales
each pick's expectation to the class it was actually made in, published on every row as
`expected_por_class_adj` beside the pooled `expected_por`.

It changes less than it looks: ranks move by at most one place. The one interpretive
flip is jhayes3134, −20 pooled to **+24** class-adjusted, i.e. from slightly below
expectation to slightly above once he stops being charged for drafting in the weak
year. Keep both numbers on the page — pooled answers "what did you actually get",
class-adjusted answers "did you draft well for the year you were in".

**Every rookie row now carries `opportunity`**: `weeks_dressed`, `weeks_used`,
`weeks_startable`, `touches`, `usage_pct`, `got_role` (6+ scoreable weeks). That is what
separates a bad landing spot from a bad evaluation — a pick that got 40 touches and
failed is not the same mistake as one that got 200 and failed, and a single PoR number
cannot tell them apart. Bucky Irving (2024 4.06) is the reference case: expected 2.3,
actual 176.4, usage percentile 81%, 16 of 16 weeks used.

---

#### Step 4 as built (2026-09-04) — the Draft ROI view

Fourth sub-view of Moves (`#moves-view-drafteval`, label **Draft ROI**), lazy-loaded, off the
same `trade-roi.json`. Deep links: `#draftroi`, `#bestdrafter`. Four Moves sub-views is within
budget — History runs five, and five is the ceiling.

**Functions:** `buildDraftEval()`, `renderDraftEval()`, `deDrafterRows()`, `deDrafterTableHtml()`,
`deCapitalHtml()`, `deHotspotHtml()`, `deBestWorstHtml()`, `dePlayedPicks()`, `deExpectedFor()`,
`setDraftEvalBasis()`, `dePickListHtml()`, `toggleDrafterPicks()`. CSS in the appended
`MOVES TAB — DRAFT ROI` layer (`.de-*`) plus the 2026-09-04 twistie layer.

**Every Best Drafter row expands to the picks behind it (2026-09-04).** A twistie left of the
manager name reveals that manager's individual picks — pick, player, position, produced, expected,
vs expected, weeks used — newest class first then by pick number, with HIT and BUST tags.
`_deOpen` holds which rows are expanded; **default is none**, because twelve open lists bury the
ranking the table exists to show.

**The detail is summed from the same rows as the total, not looked up again.** `deDrafterRows()`
now keeps each pick on `row.picks`, so the expansion cannot drift from the row above it. Verified
mechanically: all 12 managers reconcile exactly (actual, expected and vs-expected) under **both**
expectation bases, and the per-manager pick counts total 98, the full played-pick universe.

**Six blocks:** Best Drafter (ranked by actual minus expected, with a magnitude bar), What A
Pick Is Actually Worth (the `draft_capital` bands), Where The Value Hides (a round x slot heatmap,
teal above the slot's price and magenta below, each cell titled with the actual players), Steals
and Reaches (top and bottom five picks against expectation), **What These Columns Mean**
(`deGlossaryHtml()`), and a sample-size caveat block.

**The glossary exists because two of those columns are context and two are the score, and nothing
said which was which.** "Got a role" in particular reads like it ought to move the ranking and does
not: only `rookie_por` and `expected_por` feed Vs expected, while `hits` and `roles` are counters
that never touch it. It also defines "got a role" precisely — `weeks_used >= 6`, where a *used*
week means the player recorded something scoreable, so a bare `gp` line (dressed, did nothing)
does not count. **Its two thresholds are read from `trade-roi.json`** (`hit_por`,
`role_min_weeks`), never hardcoded, so the prose cannot drift from the builder.

**The basis toggle is the point of the view, not a setting.** "Adjusted for class strength"
measures a manager against the year he actually drafted in; "Raw" measures what he got. The
2024 class produced 2.39x the 2025 class, so the two answer genuinely different questions and
both are honest — which is why neither is hidden. Switching them reproduces the rank shuffle the
builder predicted (Bogardus and Merkel swap 3rd/4th; Hayes moves from -20 raw to +24 adjusted).

**A specificity bug worth remembering.** `.de-pos` / `.de-neg` set the color on the vs-expected
column, but `.de-tbl td` is (0,1,1) against a bare class's (0,1,0), so the entire column rendered
in body color in both themes — the one column a reader scans for a sign. Fixed by qualifying as
`.de-tbl td.de-pos`. It was invisible in a screenshot and only turned up in `getComputedStyle`;
**check computed color, not the picture, when a themed value looks flat.**

**Verified:** all 12 drafter rows match the builder's own numbers exactly, real names resolved
through `TEAMS` with `ownerLink()` throughout, zero console errors on a clean tab, tables scroll
inside their own `.dtblwrap` at 375px with zero page overflow, and both themes correct
(dark `#21F5E4`/`#FF3DBE`, light `#0E9C92`/`#D6258F`).

**A measurement trap, not a layout bug.** An overflow check reported 184px on a tab whose
`clientWidth` was **0** — the Browser pane had backgrounded the tab, so nothing was laid out and
every element "overflowed". Always assert the viewport is non-zero before trusting an overflow
number; forcing an explicit `resize_window` size is the reliable fix.

---

#### Step 3 as built (2026-09-04) — the Who Won That Trade? view

Third sub-view of Moves (`#moves-view-roi`), lazy-loaded, rendering entirely from the
committed `trade-roi.json`. No live API calls and no KTC on this view at all.

**Functions:** `loadTradeROI()` (hourly cache-buster, memoized in `_tradeROIPromise`),
`buildTradeROI()`, `renderROICards()`, `roiCardHtml()`, `roiAssetHtml()`, `roiManager()`,
`roiSummaryHtml()`, `toggleROIHow()`, `setROIFilter()`, `buildROITeamChips()`,
`toggleROITeam()`. CSS lives in the appended `MOVES TAB — WHO WON THAT TRADE?` layer
(`.roi-*` / `.ra-*`), per the redesign convention.

**The card:** date + verdict chip, then one block per side — manager, PoR total, and the
assets, with a teal left rail and teal total on the winner. Assets carry position, a
`via 2025 R1` tag when they arrived as a traded pick, a `BUST` tag when `por_signed < -25`,
and an italic `~30 proj` treatment for a pick that has not been drafted yet so nobody reads
a projection as earned points. Footer gives the margin and the weeks of evidence behind it.

**Filters are multi-select across three independent axes (2026-09-04).** They AND with each
other and OR within themselves:

- **Status** — `_roiStatus`, buttons in `#roi-filter-bar`, ordered **All Trades > Graded >
  Lopsided > Too Early**. Empty set means all. `setROIFilter(f)` toggles; `'all'` clears.
  "Graded + Lopsided" is the case that motivated this and resolves to 33 — lopsided is a subset of
  graded, so the union is graded, which is exactly the "everything except Too Early" view wanted.
- **Verdict** — `_roiVerdicts`. The ROBBERY / CLEAR WIN / EDGE / DEAD EVEN chips in the summary
  are now **buttons**, not labels (`toggleROIVerdict`).
- **Manager** — `_roiTeams`, unchanged, still keyed on user_id.

`clearROIFilters()` resets all three and is surfaced as a "Clear filters" button that only appears
when something is filtered.

**Every count in the summary follows the selection.** `roiSummaryHtml(rows)` takes the filtered
set, so the headline reads `21 of 52 trades / 16 scored / 5 still open` when one manager is
selected, and `52 trades since 2023` when nothing is. The summary therefore has to redraw with the
cards — it renders into `#roi-summary-host` from `renderROICards()`, where it used to be injected
once with `insertAdjacentHTML` and never updated.

**The verdict chips deliberately count a different set from the headline.** `roiVerdictScope()` is
everything passing the status and manager axes but **not** the verdict axis. Counting them
post-verdict would zero every chip you had not selected and leave no way to see what else was
there. A chip with nothing behind it dims to 35% rather than disappearing, so the row does not
reflow as you filter.

**A summary strip sits above the filters** with the verdict spread and a collapsible
*"How is this scored?"* explainer. That explainer is not optional decoration: this view
publishes a number that calls someone's trade a robbery, so the four things that would
otherwise start an argument — points over replacement, the zero floor on busts, picks
counting as the player taken, and scores being recomputed live — are stated in plain
English on the page itself, with the actual thresholds quoted from `trade-roi.json`.

**`shortName()` does not exist** — this view's chip bar called it on the strength of the
VISUAL THEME note and threw a live `ReferenceError`. That note is now corrected; the real
function is `abbrev()`. Manager names on both the chips and the cards resolve through
`TEAMS`/`t(uid)` to the **real** name, falling back to the Sleeper handle stored in
`trade-roi.json` only for a manager no longer in `TEAMS` (CCJ). Every name goes through
`ownerLink()`, so all 99 of them open a profile.

**Verified in-browser:** 52 cards on All Trades and 33 on Graded (matching the builder),
zero console errors on a clean tab, zero page overflow at both 375px and desktop, light mode
inheriting the palette correctly (teal `#0E9C92`, magenta `#D6258F`) with the neon glows
present in dark and absent in light. `?v=`-style verification needs a **fresh tab or a
cache-busted URL** — `python http.server` 304s aggressively and served the pre-fix page three
times while the file on disk was already correct.

---

#### Step 5 as built (2026-09-03) — live-season accrual

Pulled forward ahead of items 2-4: the season opens 2026-09-09, and until this runs the live
season stays absent from `stats-history.json` entirely, so every 2026 trade would score 0-0
no matter what happened on the field.

**`generate_stats.py` gained three things**, all of which exist because it now runs unattended:

- **`--live-only`.** Copies completed seasons through from the existing file and rebuilds only the
  in-progress one. A weekly full rebuild would re-fetch ~51 weeks that can never change, and would
  put three years of good data at the mercy of one flaky request every single Tuesday.
- **`check_no_data_loss()`.** A hard gate before writing: refuses to publish an output that drops a
  season, drops any week from a season, or loses more than 5% of a season's players. **Tested by
  simulating a 503 on week 7** — the run aborts with exit code 1 and the file is byte-identical
  afterwards. `build_season()` also refuses to return a season with any failed week, so a hole can
  never reach the merge in the first place.
- **`__file__`-relative paths.** It wrote to a bare `'stats-history.json'`, so it only worked when
  invoked from the project directory; the workflow runs from the repo root.

**A real bug the safety gate caught on its first live test.** `get_league_chain()` walked the
chain with a *loop counter* rather than each league's own season, so calling it for any season
other than 2026 truncated the chain and dropped the 2023 league's rosters from the player
universe — 2025 rebuilt to 401 players instead of 441. The gate blocked the write and named the
number. The walk is now keyed and terminated on `info['season']`. **This is the gate justifying
itself on day one; do not remove it as belt-and-suspenders.**

**`loadStatsHistory()` gained the hourly cache-buster** (`?_=`+hour) that `loadProjectionsFile`,
`loadCommentary` and the rest already used. This file changed roughly once a year until now; from
this week it changes weekly in-season, and a browser-cached copy would hold the live season a week
behind.

**The workflow itself was broken and had never run** — see Automation (Tuesday Bot) for the full
finding and the two rules that came out of it. Short version: a multi-line `python -c` at column 0
inside a `run: |` block made the entire file invalid YAML from the day it was written.
`deploy-pages.yml` also had to gain the Tuesday workflow in its `workflow_run` chain, because the
bot now commits a file the site actually fetches.

**Verified end to end:** all five workflow files parse; `--live-only --dry-run` runs correctly from
the repo root and writes nothing; a simulated live season *with* data (2025) rebuilds to the same
441 players / 17 weeks with no loss; a simulated API failure aborts and leaves the file untouched;
the `WEEK=` one-liner resolves `?` on an empty state and `3` on `[1,2,3]`; and in-browser the site
requests `stats-history.json?_=496799`, renders 441 rows, and logs no new errors.

**Checked on 2026-09-15** (the first Tuesday with real 2026 data) — **the run failed before it
reached any of that**, on week detection rather than on the Phase 12 chain. See "`state.week` is
the upcoming week by Tuesday" under Automation (Tuesday Bot). The three things still to confirm on the next run: that it adds a
`"2026"` block with week 1 only, that the deploy chain fires, and that the Player Stats tab is
unaffected — the live season renders through `build2026Stats()` off the live API and never reads
`stats-history.json`, so it should be untouched either way.

**Unrelated drift noticed while verifying, not acted on:** the Phase 6 console report now says
*"Unmatched KTC report — 3 player(s) across all 12 rosters"*, where CLAUDE.md records 0 as of
2026-08-20. Possibly just the local run falling back to the committed `ktc-values.json` after the
live scrape 403s. Worth a look before the next grading period.

---
