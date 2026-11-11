# Automation (GitHub Action Bots) — The Other League reference

Moved verbatim out of `CLAUDE.md` on 2026-11-11 so it loads only when needed. A cross-reference to another section may now point to a different `docs/claude/` file; grep the folder for the heading.

## JAVASCRIPT FUNCTIONS (continued)

### Automation (Tuesday Bot)
Weekly automation that runs every Tuesday at 9am ET (after Monday Night Football). It now does
**two** jobs: update `h2h-records.md` with the prior week's H2H results, and extend
`stats-history.json` with the live season's played weeks (Phase 12).

- **`scripts/tuesday_update.py`** — fetches `state/nfl` to detect current week, fetches matchups from Sleeper API, parses and rewrites `h2h-records.md`. Flags: `--week N`, `--dry-run`, `--force`. Tracks applied weeks in `scripts/bot_state.json`.
  **`state.week` is the upcoming week by Tuesday, not the finished one (fixed 2026-09-15).** The
  first live run read `week=2` the Tuesday after Week 1, fetched an unplayed week, and exited 1 —
  which also skipped the whole Phase 12 chain behind it. Auto-detect now steps back one week when
  the reported week has no scores (`week_has_points()`). Don't "simplify" it back to `state.week`:
  the same bug would also have silently dropped Week 14, since state reads 15 by then.

  **A week with no scores exits 0, not 1 (2026-09-15).** Only `--week` reaches that guard now that
  auto-detect steps back, and "the week you asked for hasn't happened yet" is not a broken bot.
  Exiting 1 sent a red failure email every pre-season Tuesday — which is exactly how the real
  week-detection bug above went unread for two weeks.
- **The Phase 12 data chain** — three steps, added 2026-09-03/04, all running **after** the H2H
  commit and each `continue-on-error`, so a data failure can never cost an H2H update that
  already succeeded. **The order is load-bearing and each step is gated on the previous one:**

  1. `generate_stats.py --live-only` → `stats-history.json`
  2. `scripts/build_replacement_levels.py --live-only` → `replacement-levels.json`
  3. `scripts/build_trade_roi.py` → `trade-roi.json`

  Each reads the one before it. Getting the order wrong is **not** a loud failure:
  `build_trade_roi.py` skips any week it has no replacement baseline for (`base is None ->
  continue`), so running it against stale baselines publishes a file in which the whole live
  season silently scored zero — every 2026 trade frozen at 0-0 all year while the page reports
  them as scored, with nothing anywhere to trace it back to. `coverage_gaps()` is the backstop:
  it refuses to build when `stats-history.json` holds a played week that `replacement-levels.json`
  cannot score. Verified by simulating a 2026 Week 1 stats update against stale baselines.

  All three skip the write entirely when the only thing that would change is the `generated`
  date (`unchanged_but_for_stamp()`), so the offseason does not produce a weekly commit whose
  entire content is a one-character date bump on a 1.3 MB file. **That helper must round-trip
  the payload through JSON before comparing** — an in-memory dict keyed by int
  (`pick_curve.by_pick`) sorts numerically while the same data read back from disk sorts
  lexicographically (`"1","10","11",..,"2"`), so without the round-trip the compare reports a
  change on every run and the skip never fires. That bug was live for one build.

  A final `always()` step prints each link's outcome and raises a `::warning::` if any failed,
  so a broken chain is visible rather than hidden behind a green tick.
- **`.github/workflows/tuesday-update.yml`** — GitHub Actions cron (Tuesday 1pm UTC); also has manual trigger with week/dry-run/force inputs. Commits `h2h-records.md` + `bot_state.json`, then the three Phase 12 data files together, each only if changed.

**This workflow had never run once before 2026-09-03 — the file was not valid YAML.** The commit
message's `WEEK=$(python -c "` was a *multi-line* command whose body sat at column 0 inside a
`run: |` block. A block scalar ends at the first line indented less than the block, so YAML parsed
`import json, os` as a top-level key and rejected the whole file. Nothing failed loudly; the
workflow simply never appeared as runnable, and the only "H2H records update" string in the git
log is the commit that created the bot. It went unnoticed because the H2H script is a no-op out of
season anyway. Confirmed by parsing the committed file: invalid, while the KTC and projections
workflows parse fine and have many `chore(bot)` commits.

Two rules that follow from it:
1. **Never paste a multi-line script body into a `run: |` block.** The `WEEK=` extraction is now a
   single line. Anything longer belongs in a `.py` file called by the step.
2. **Parse every workflow file after editing it** — `python -c "import yaml,sys; yaml.safe_load(open(f))"`
   over `.github/workflows/*.yml`. All five parse as of 2026-09-03.

The same step also read `scripts/bot_state.json`, a path that does not exist from the repo root
(it is `Sleeper FF/The Other League/scripts/bot_state.json`), so every commit message would have
said "Week ?" even once the file parsed. Fixed at the same time.

**Every bot script forces UTF-8 on stdout, and must keep doing so (added 2026-09-04).**
A dress rehearsal of the whole chain on Windows ahead of the Sep 15 live run died immediately:
`UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'`. The scripts print arrows,
em dashes and check marks; a Windows console — and any redirected output, which is exactly what
the Task Scheduler launcher does — defaults to cp1252 and cannot encode them. GitHub Actions runs
on Ubuntu under UTF-8 and was never affected, which is why this sat unnoticed through the whole of
Phase 12: the only path anyone had actually exercised was the one immune to it.

It would have taken the Windows scheduled task down on its very first live firing, silently,
into a log file nobody reads. All six scripts (`generate_stats.py`, `tuesday_update.py`,
`build_replacement_levels.py`, `build_trade_roi.py`, `fetch_ktc.py`, `fetch_projections.py`) now
carry a `sys.stdout.reconfigure(encoding='utf-8')` guard above their first `print()`, and
`run_tuesday_update.bat` sets `PYTHONIOENCODING=utf-8` as a second layer. **A new bot script needs
the same guard** — write one without it and it works in CI and only ever fails on the user's PC.

**The Windows scheduled task runs the H2H step ONLY — not the Phase 12 chain — and does not push.**
`run_tuesday_update.bat` calls `tuesday_update.py` and stops there. GitHub Actions is the real bot
and the only thing that rebuilds and commits the three data files. The local task is a leftover
belt-and-suspenders path whose one effect is to leave `h2h-records.md` modified in the working copy,
which will then conflict with whatever the Actions run pushed for the same week. If it fires at all
after Sep 9, expect that dirty file and discard it rather than committing it.

- **`scripts/run_tuesday_update.bat`** — Windows launcher called by Task Scheduler; logs to `scripts/tuesday_update.log`.
- **`scripts/setup_scheduled_task.ps1`** — one-time setup to register the Windows Task Scheduler task. Task is **dormant until Sep 9, 2026** (`StartBoundary`); fires on next boot if PC was off at 9am.
- **`.github/workflows/season-reminder.yml`** — GitHub Actions creates a GitHub Issue on Sep 2, 2026 as a reminder to activate the bot; GitHub emails the repo owner automatically.

### Automation (KTC Bot — deep lookup added 2026-08-20)
`scripts/fetch_ktc.py` runs in two passes:
1. **Top-500.** `keeptradecut.com/dynasty-rankings` embeds `var playersArray`, and it is **capped at exactly 500 players**. Verified: `?page=0/1/2` all return the same 500 (pagination is client-side), and the trade-calculator page's `playersArray`/`superflexPlayers` are capped the same way. There is no public JSON API — the page contains no fetch/ajax/`url:` reference at all.
2. **Deep lookup.** Fetches the league's own Sleeper rosters, finds any rostered non-K/DEF player with no match after alias/normalize/suffix (mirroring `getKTCEntryFuzzy` in Python), resolves a slug from `sitemap-dynasty.xml`, and reads `var player = {...}` off that player's own page for a real `superflexValues.tep` value. Entries are marked `"deep": true`. Anything with no slug is written to the file's `unresolved` array — which is what `_ktcUnresolved` and `resolveRosterPlayerValue` consume.

Two guardrails: `MAX_DEEP_LOOKUPS` (40) aborts rather than mass-requesting KTC if an upstream name-format change makes everyone look unmatched, and the whole deep pass is wrapped so a Sleeper hiccup or KTC layout change downgrades to "top-500 only" instead of losing the values already in hand.

**Slug matching needs a different normalizer than name matching.** `squash()` strips everything non-alphanumeric, because slugs flatten punctuation differently: De'Von Achane is `de-von-achane-1398`, which normalizes to "de von achane" while his name normalizes to "devon achane". Only squashing both to `devonachane` lines them up.

`ALIASES` in the script mirrors `KTC_NAME_ALIASES` in `index.html` — **keep the two in sync.**

**`bracket_extract()` searches for the opening bracket; it does not assume one follows the marker
(fixed 2026-09-15).** It used to return everything from the end of the marker onward, which was
indistinguishable from correct for as long as KTC wrote `var playersArray = [...]` bare. The bot
succeeded on 2026-09-07 and failed on 2026-09-14 with `JSONDecodeError: Expecting value: line 1
column 1` — the marker was still found, so the "not found" guard never fired; what followed it was
no longer bare JSON. Any wrapper (`JSON.parse('[...]')` being the obvious one) came back glued to
the front of the array. The scan now skips up to `WRAPPER_SCAN` (200) chars to the first `[`/`{`,
which both shapes satisfy, and both passes go through the one function.

**A decode failure now prints what was actually extracted** — the first 200 chars — instead of a
bare traceback. "Expecting value: line 1 column 1" says nothing about *what KTC changed* and cost a
whole round trip to diagnose. This is the diagnostic, not a confirmed root cause: the fix was
written from the traceback, with no live KTC page available to read. **If the next scheduled run
still fails, the log now carries the answer** — read the `extracted ... starting:` line.

Note that a failure here leaves `ktc-values.json` untouched rather than half-written, so the site
keeps serving the last good values (2026-09-07's, at the time of writing).

### Automation (Projections Bot — added 2026-08-20)
- **`scripts/fetch_projections.py`** — pulls all 17 weeks of `/projections/nfl/regular/{year}/{week}`, keeps only QB/RB/WR/TE with a real projection and only the ~30 keys this league scores, writes `projections-<year>.json`. Flags: `--year N`, `--dry-run`. Aborts rather than overwriting a good file if a pull comes back gutted (<200 players in week 1).
- **`.github/workflows/update-projections.yml`** — daily cron at 11:00 UTC (7 AM ET); commits the file only when it changed.
- **Deploy chaining (important):** commits pushed by a job using the default `GITHUB_TOKEN` do **not** fire `push`-triggered workflows — GitHub blocks that to stop workflows recursing. So the projections and KTC bots would commit their data files and the live Pages site would never pick them up. `deploy-pages.yml` therefore also triggers on `workflow_run` for all three bot workflows (guarded by a `conclusion == 'success'` check). Don't remove that trigger thinking the `push` one already covers it — this was a latent gap for the KTC bot too.
  **"Tuesday Weekly H2H Update" joined that list 2026-09-03.** It was legitimately absent before:
  its only output was `h2h-records.md`, which the site never fetches (0 references in
  `index.html`). Now that the same workflow commits `stats-history.json`, which *is* fetched at
  runtime, it has to be chained or the bot would update the file every Tuesday and the live site
  would never serve it. **Any bot that starts writing a file the site fetches must be added here.**
- **`update-ktc.yml` runs on cron + dispatch, plus a narrow push trigger on `scripts/fetch_ktc.py` only (fixed 2026-08-20).** It previously used `paths-ignore`, which only skips a push whose files are *all* ignored — so every ordinary code push fired a full KTC scrape. The git log showed it plainly: four consecutive code pushes, four immediate `chore(bot)` commits, each of which also redeployed Pages through the `workflow_run` chain. `update-projections.yml` never had a push trigger and was always correct; this brings KTC in line.

---
