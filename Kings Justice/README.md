# King's Justice - Sleeper Data Pipeline

Pulls the complete history of the **King's Justice** Sleeper league (chopped /
elimination format) and writes clean JSON + CSV files you can hand straight to
Claude for analysis.

- **Current season league id:** `1383926066564837376`
- **My team:** The Executioner (`avobttam`)

---

## How to run it

You need Python 3 and one package:

```
pip install requests
```

Then, from inside this folder:

```
python scripts/pull_kings_justice.py
```

That is the whole thing. It prints its progress, then finishes with a
plain-English summary of what it found.

### The other options

| Command | What it does |
|---|---|
| `python scripts/pull_kings_justice.py` | Normal run. **Use this one weekly.** |
| `... --refresh-all` | Throws away every cached response and re-pulls the whole history from scratch. Slow. Use if something looks wrong. |
| `... --refresh-players` | Just re-downloads the NFL player list (do this if new players show up as `UNKNOWN`). |
| `... --out /some/folder` | Write the files somewhere else. |
| `... --league-id <id>` | Start from a different league. **Next season, put the new league id at the top of the script instead** - the variable is `CURRENT_LEAGUE_ID`. |

### Running it weekly during the season

Just run it again. It is designed for exactly this:

- Every response is cached in `scripts/.cache/`.
- Finished weeks are read from the cache and never re-downloaded.
- Only the live week and the current season get re-fetched.

So a mid-season re-run costs a handful of API calls, not hundreds, and it adds
the new week to the existing files rather than starting over.

---

## What you get

```
kings_justice_data/
  players_lookup.json      <- player id -> name/position/team (shared, cached ~1 week)
  league_chain.json        <- season year -> league id, for every season found
  new_owners.json          <- who is new this year vs. every prior season
  pipeline_report.txt      <- the plain-English summary from the last run

  2026/
    league_settings.json          scoring rules, roster slots, status
    owners.json                   user_id, username, team name, avatar
    rosters.json                  who owns which roster + FAAB spent/remaining
    draft_results.json            every pick, with real player names
    weekly_scores.json            roster_id, week, points, team name
    transactions_all_weeks.json   every waiver/free agent/trade, names joined
    waiver_bids.json              FAAB auctions grouped per player (see below)
    season_summary.json           elimination reconstruction + validation flags
    season_summary.csv            the week-by-week table, easy to paste anywhere
  2025/
    ... same structure
  2024/
    ... same structure
```

### `season_summary.csv` - the one to look at first

| Week | Eliminated Team | Eliminated Score | Weekly High Team | Weekly High Score | Teams Alive At Start | Elimination Confirmed By Drops | Is Final Week | Flags |
|---|---|---|---|---|---|---|---|---|

`Elimination Confirmed By Drops` is the trust column. `yes` means the chop was
independently confirmed against the transaction log. **`NO` means look at it
by hand** - the reason is spelled out in the `Flags` column.

### `waiver_bids.json` - the FAAB auctions

One entry per player claimed per week, with `all_bids` listing every claim
Sleeper returned for that player - winners and losers - sorted highest bid
first. `status: "complete"` won the player, anything else lost.

Each file also carries a `losing_bid_visibility` block that counts what
actually came back, so you can see at a glance whether losing bids are
available for that season rather than having to take it on faith.

---

## How the elimination logic works

Sleeper has **no "eliminated" field**, so the script reconstructs it:

1. Everyone starts alive.
2. For each week that was actually played, look **only at teams still alive**.
3. Lowest score that week -> **chopped**. Highest score -> **wins the $25**.
4. Repeat until two teams are left. The next played week is the final, and the
   higher score there takes 1st place ($350); the other takes 2nd ($150).
5. Everyone else is placed in reverse chop order - last team chopped is 3rd.

**Why "only teams still alive" matters:** a team chopped in week 3 has an empty
roster and scores 0.00 in week 4. If you did not filter them out, that dead team
would look like the lowest scorer every single week from then on and nobody else
would ever get chopped. This is the single biggest trap in the whole job, and it
is covered by a test.

### The cross-check

A chopped team's whole roster gets auto-dropped to waivers. So for every chop the
script takes the players who were on that roster that week, looks for them coming
back as `drop` transactions from the same roster in that week or the next, and
requires at least **50%** to match before calling the elimination confirmed.

Anything that does not line up gets written to the `Flags` column and repeated in
the end-of-run report:

- a **tie** for lowest score (the chop is a coin-flip and needs a human)
- a still-alive team scoring **0.00** (almost certainly missing data, not a real chop)
- a chop the **drop log does not back up**

The script never silently guesses - if it is unsure, it says so.

---

## Notes and gotchas

- **The Sleeper API is public and read-only.** No login, no API key, nothing to
  configure. The script throttles itself to ~90 calls/minute out of politeness.
- **`scripts/.cache/` is gitignored** and can be deleted at any time. Deleting it
  just means the next run re-downloads everything.
- **Mid-draft seasons work fine.** With no matchups yet, the script writes the
  owners/rosters/draft files and reports the season as in progress rather than
  erroring out.
- **New season?** Change `CURRENT_LEAGUE_ID` at the top of
  `scripts/pull_kings_justice.py`. Everything else is found automatically by
  following `previous_league_id` backwards.
