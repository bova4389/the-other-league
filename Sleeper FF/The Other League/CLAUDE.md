# CLAUDE.md — The Other League Dynasty Dashboard

## WHAT THIS PROJECT IS

A personal fantasy football dashboard for "The Other League" — a 12-team dynasty league on the Sleeper platform. The site pulls live data from the Sleeper public API to display rosters, league history, draft picks, scoring rules, rivalries, and a trade evaluator with live KTC values.

**Commissioner:** Matt Bova. Built for personal use, shared with league mates via GitHub Pages.

---

## PROJECT STRUCTURE

This is a **static HTML/JavaScript project** — no framework, no build step, no package manager. All files are plain `.html` with embedded CSS and JavaScript.

```
the-other-league/                      ← outer repo root
├── index.html                         ← redirect stub to GitHub Pages site (do NOT edit for features)
├── .github/workflows/                 ← GitHub Actions (deploy-pages, update-ktc, tuesday-update)
└── Sleeper FF/The Other League/       ← THE actual project folder (edit everything here)
    ├── index.html                     ← THE working file (5000+ lines, all logic embedded)
    ├── CLAUDE.md                      ← you are here
    ├── TOL Large Logo.png             ← hero image (home panel + sticky header)
    ├── TOL Small Logo.png             ← available if needed
    ├── TOL Abbreviated Icon.png       ← favicon + iOS add-to-homescreen icon
    ├── TOL iPhone background image.png ← iOS splash screen
    ├── img/profiles/                  ← 12 manager headshots, 600x750 JPEG (~50 KB each, 660 KB)
    │                                    Source photos + cropping script live in `League Pics/`
    │                                    (untracked); only the web-sized JPEGs are committed.
    ├── ktc-values.json                ← KTC dynasty values (updated weekly by GitHub Action)
    ├── projections-<year>.json        ← all 17 weeks of Sleeper projections, trimmed (updated DAILY by GitHub Action)
    ├── stats-history.json             ← historical player stats cache (2023-2025; the live season
    │                                    is absent until it has played weeks — see generate_stats.py)
    ├── replacement-levels.json        ← Phase 12 weekly points-over-replacement baselines per position
    ├── trade-roi.json                 ← Phase 12 scored trades + rookie picks + pick curve
    ├── generate_stats.py              ← builds stats-history.json. NOT a one-off any more: the player
    │                                    universe is every player ever rostered, drafted OR traded here,
    │                                    so re-run it after trades and after each rookie draft
    ├── roster-grades-<period-id>.json  ← Phase 6 frozen grading period, e.g. roster-grades-2026-preseason.json
    │                                     (exists as of 2026-08-20). One file per grading run; hand-committed from the
    │                                     Export panel in Rosters > Grades & Outlook with ?admin=1 on the URL
    ├── matchup-commentary-<year>.json  ← Phase 8 Scores-tab PER-MATCHUP write-ups, keyed "week|matchup_id".
    │                                     2025 complete; 2026 scaffolded empty 2026-08-21, written live each week.
    ├── weekly-recaps-<year>.json       ← Phase 10 WHOLE-LEAGUE weekly recap, keyed by week number.
    │                                     Sits at the TOP of the Scores tab. 2026 scaffolded empty 2026-08-21.
    ├── season-recaps.json              ← Phase 9 Careers year-tab season write-ups, keyed by year.
    │                                     2023/2024/2025 written 2026-08-21.
    └── scripts/
        ├── tuesday_update.py          ← weekly H2H records updater
        ├── fetch_ktc.py               ← KTC values scraper (top-500 + per-player deep lookup)
        ├── fetch_projections.py       ← daily Sleeper projections pull → projections-<year>.json
        ├── build_matchup_facts.py     ← Phase 8 offline fact sheet; writes to a temp dir, never committed
        ├── build_season_facts.py      ← Phase 9 season-level fact sheet; same deal, never committed
        ├── build_replacement_levels.py ← Phase 12; writes replacement-levels.json (committed)
        ├── build_trade_roi.py         ← Phase 12; writes trade-roi.json (committed).
        │                                --report prints the distributions the thresholds came from
        ├── measure_starter_mix.py     ← Phase 12; measures the real positional starter mix that
        │                                sets REPLACEMENT_RANKS. Prints only, writes nothing
        └── bot_state.json             ← tracks which weeks have been applied
```

**Housekeeping (2026-08-20):** deleted `h2h_calc.py` (a one-off with 2023-25 scores pasted inline that only printed to stdout — `scripts/tuesday_update.py` supersedes it, pulling from the API and maintaining `h2h-records.md`) and `scripts/check_js.py` / `check_js2.py` (bracket-balance debuggers hardcoded to `Desktop/Claude Code/index.html`, a path that has only held the redirect stub since the project moved into this folder — they were broken *and* unreferenced). Together with the dead-code removal in `index.html`, that is ~36 KB gone.

**Current state:** `Sleeper FF/The Other League/index.html` is the **only** file to edit for features. It contains all HTML, CSS, and JavaScript in one file. The logo PNGs, `ktc-values.json`, and `stats-history.json` are in the same folder.

**Deployment:** GitHub Pages (static hosting). The `deploy-pages.yml` Action serves from `Sleeper FF/The Other League/`. Push to `main` → site updates automatically. Live at `https://bova4389.github.io/the-other-league/`

---

## REFERENCE DOCS — READ THE MATCHING ONE BEFORE TOUCHING THAT AREA

Most of what used to be in this file now lives in `docs/claude/`, moved verbatim on 2026-11-11 so
a session only pays for the parts it needs. The two sections below that stayed here (KEY DESIGN
DECISIONS and WHAT NOT TO DO) are the guardrails, and they apply everywhere. The docs hold the
per-area detail. **Before you change an area, read its doc.** Do not work from what the code
seems to imply.

| Before touching… | Read |
|---|---|
| Nav tabs, panels, sub-views, hash routing, `TAB_ALIASES`, the Commissioner panel, element IDs | [`docs/claude/navigation.md`](docs/claude/navigation.md) |
| Theme, cache, Sleeper fetch, projections, rosters, player stats, transactions, draft, Trade Evaluator, boot | [`docs/claude/functions-data-and-tabs.md`](docs/claude/functions-data-and-tabs.md) |
| All-time stats engine, Careers, Scores tab, matchup commentary, season recaps, survivor pool, median game, H2H / rivalries, manager profiles | [`docs/claude/functions-history-and-scores.md`](docs/claude/functions-history-and-scores.md) |
| Roster Grades & Outlook (code and Phase 6 rules) | [`docs/claude/roster-grades.md`](docs/claude/roster-grades.md) |
| The Tuesday, KTC, or projections bots, or any `.github/workflows` file | [`docs/claude/automation.md`](docs/claude/automation.md) |
| Data objects (`RM`, `SDATA`, `SEASON_PAYOUTS`…) or any `localStorage` key | [`docs/claude/data-and-storage.md`](docs/claude/data-and-storage.md) |
| Colors, fonts, CSS layers, logo files | [`docs/claude/visual-theme.md`](docs/claude/visual-theme.md) |
| **Writing a weekly recap or matchup commentary** (Phases 8 and 10), or picking new work | [`docs/claude/roadmap.md`](docs/claude/roadmap.md) |
| Trade ROI, Rookie Draft ROI, points-over-replacement | [`docs/claude/phase-12-trade-and-draft-roi.md`](docs/claude/phase-12-trade-and-draft-roi.md) |

**Roadmap at a glance:** Phases 1, 2, 6, 9, and 11 shipped. Phase 7 is substantially complete.
Phases 8 and 10 have shipped machinery and get new content every week. Phase 12 shipped
2026-09-03/04 with a weekly bot. **Phases 3, 4, and 5 are not started.**

**When a comment or doc says "see CLAUDE.md, <section>", that section may have moved to one of
these docs.** Grep `docs/claude/` for the heading.

---

## EXTERNAL APIS

### Sleeper API (no auth required)
- Base: `https://api.sleeper.app/v1`
- League ID: `1316225642072662016`
- Key endpoints:
  - `/league/{lid}` → league info
  - `/league/{lid}/rosters` → all 12 rosters
  - `/league/{lid}/traded_picks` → pick trade log
  - `/league/{lid}/matchups/{week}` → matchup scores for a given week
  - `/league/{lid}/transactions/{week}` → transactions for a given week
  - `/league/{lid}/drafts` → drafts list
  - `/draft/{draft_id}/picks` → picks for a draft
  - `/players/nfl` → full player database (~5MB, slow)
  - `/stats/nfl/regular/{year}/{week}` → actual player stats for a completed week
  - `/state/nfl` → current season + week; drives "is this the live season/week" decisions instead of hardcoded years
  - `/projections/nfl/regular/{year}/{week}` → projected player **stat lines** (NOT points — the `pts_ppr`/`pts_std`/`pts_half_ppr` fields it also returns are Sleeper's generic scoring and know nothing about this league; never display them. Score the raw line through `calcPts()`/`SDATA` instead). ~590 KB per week for all ~9,400 players, which is why the committed `projections-<year>.json` exists. **Corrected 2026-08-19** — this note previously said "no regular in path," which was wrong (or the API changed): that URL returns HTTP 200 with an empty `{}` for every player, always, silently. Confirmed live against multiple real players and multiple weeks, including a completed 2025 week, that `regular` in the path (matching the stats endpoint's format) is required to get real data.
- CORS note: Direct browser fetch may fail. Fallback proxies in order: `corsproxy.io`, `api.allorigins.win`

### Anthropic API
- The "Ask Claude" tab was removed from the UI (panel and icon tab are gone)
- `getTradeAI()` was also removed in the June 2026 Trade Evaluator overhaul
- **All of it was removed 2026-08-20.** `sendAI()`, `addMsg()`, `clearChat()`, `quickPrompt()`, `aiMessages`, `LEAGUE_CONTEXT`, `QUICK_PROMPTS`, the `.ai-*` CSS block and its four theme variables are gone. Verified first that `getTradeAI` had **zero** occurrences left, so the old "do not remove — `getTradeAI()` calls them" caveat was already false. No AI markup had existed for a while either; this was an orphaned browser-side Anthropic API caller with no UI and no key. Nothing calls into it — don't reintroduce it.

---

## REMOVED / HIDDEN ELEMENTS

- **Sidebar** (`.sidebar`) — **fully removed 2026-08-20.** Markup, `buildSidebar()`, `scrollToTeam()`, the boot call and the `.sidebar`/`.sb-label`/`.t-item`/`.t-av`/`.t-info`/`.ti-n`/`.ti-o` CSS are all gone. It had been `display:none` while still running a DOM-building pass on every page load, and `scrollToTeam` targeted `.tab[onclick*="rosters"]` — a selector the icon-nav rewrite had already broken.
- **Cache bar** (`.cache-bar`) — `display: none !important` inline style — the "Cached data · Last fetched Xm ago · Refresh" row is hidden. The DOM elements and IDs (`cache-dot`, `cache-status-txt`, `refresh-btn`) still exist in the HTML so `setCacheBar()` and `refreshData()` work correctly.
- **Sleeper bar** (`.sleeper-bar`) — removed from HTML. "Open in Sleeper" link moved to the header.

---

## KEY DESIGN DECISIONS (don't change without asking)

- **Distance-based PPR scoring** with TE premium (+0.5/rec). `SDATA` has **`rec: 0.0`** — corrected 2026-08-20, and this entry previously said the exact opposite ("has `rec: 1.0` (PPR). Do not set back to 0.0"), so don't trust a memory of the old rule. This IS a PPR league; it just pays for catches by *distance* (`rec_0_4` 0.5 / `rec_5_9` 0.75 / `rec_10_19` 1 / `rec_20_29` 1 / `rec_30_39` 1 / `rec_40p` 2) instead of a flat point each. Those buckets **are** the PPR — adding `rec: 1.0` on top pays for the same catch twice.
  **Evidence, so this doesn't get "fixed" back again:** Sleeper reports `rec: 0` for this league in all four seasons (2023, 2024, 2025, 2026 — checked via `previous_league_id` chain). Replaying 2025 Week 3 starters through `calcPts()` reproduces Sleeper's own team totals *exactly* at `rec: 0` (105.58 / 143.00 / 155.13 / 159.58) and overshoots by 23–40 points per team at `rec: 1.0`. The `1.0` was left over from an early KTC comparison, not a league rule. Effect of the fix: Puka Nacua's 2026 season projection went 467.5 → 346.8; every Est. Pts / Proj Pts figure on the site dropped accordingly.
- **`SDATA` is overlaid from the live league at runtime** — `applyLeagueScoring()` merges `/league/{LID}`'s `scoring_settings` over the hardcoded `SDATA`, cached in `localStorage['tol_scoring_v1']` and applied synchronously at parse time. The hardcoded block is now only an offline fallback, so a commissioner scoring change on Sleeper flows through without a code edit and `SDATA` can't silently drift again.
- **Trade Evaluator uses KTC Superflex + PPR + TE Premium** (`format=1&tep=1` → `superflexValues.tep.value`). Pick values are KTC raw at slider +25%; default 0% = 80% of KTC. 2026 picks excluded (draft complete). Player Values table builds from Sleeper rosters first for guaranteed ownership, then adds unrostered KTC entries.
- **Dark/light theme toggle** — persists via `localStorage['tol_theme']`
- **LocalStorage caching** — Sleeper roster data cached 6h; historical data permanent
- **CORS fallback chain** — direct → corsproxy.io → allorigins.win; never remove
- **Single-file architecture** — all HTML, CSS, JS in `index.html` inside `Sleeper FF/The Other League/` (the outer repo root has only a redirect stub)
- **Roster chips colored by position** — QB=purple, RB=green, WR=blue, TE=orange, K=gray, DEF=red. Color legend shown at top of Rosters panel using actual `.chip` elements. Number in parentheses after player name = age.
- **Position badge (`.cp`)** — the position label inside each `.chip` is styled as a small colored badge: DM Sans 600, 10px, `padding: 1px 4px`, `border-radius: 2px`, background from `--pos-XX-bg` CSS variables (semi-transparent, defined for both dark and light themes). Replaced Bebas Neue — do not revert.
- **Avg Age badges (`.bdg`)** — use DM Sans 600 at 10px. The override block near the end of `<style>` sets `font-family: 'DM Sans'` — this overrides the base `.bdg` rule. Replaced Bebas Neue — do not revert.
- **Rivalry records count every regular-season meeting since 2023** (Matt, 2026-10-07; this replaced the old "2025 forward only" rule). The rivalries became official in 2025 (`RIVALRY_START_YEAR`), so 2023 and 2024 rows carry a muted `.riv-pre` "pre-rivalry" tag, but those games DO count toward the card's All-Time Rivalry Record and points. The cards therefore agree exactly with the H2H explorer for the same pair (verified 6/6 on build day). Roster 11's pre-2026 games are Chris Jacobs's and show under Andrew with his `*`, per the roster-11 rule. Rivalry weeks: W4 and W13 (both 2025 and 2026). W14 is NOT a rivalry week — a prior mistake that was corrected.
- **2026 draft is linear, not snake** — rounds 2–4 follow the same order as round 1
- **Sidebar is gone entirely** — removed 2026-08-20, markup and JS and CSS. Do not add it back without explicit request.
- **Cache bar is permanently hidden** — hidden via inline `style="display:none"` on the div. The underlying elements still exist and `refreshData()` / `setCacheBar()` still work correctly — do not remove the DOM elements.
- **Every aggregate stat is regular season only — weeks 1–14.** Confirmed by Matt 2026-08-20 and it is a data-quality rule, not a presentation preference: weeks 15–17 are the playoff *and* consolation brackets, and roughly half those games are consolation matchups with nothing at stake, where managers routinely leave a stale or empty lineup. Averaging those in makes a manager look worse (or a blowout look bigger) for a game nobody was trying to win. `REG_WEEKS = 14` is the single constant; `buildAllTimeStats`, `buildH2HMap`, `buildMedianMap`, `buildH2HForYear` (default), `buildSeasonStandingsData` (default) and the live-standings week scan all honor it. **Any new code that walks `tol_matchups_*` must cap at `REG_WEEKS`.** The Scores tab is the deliberate exception — it is a browsable scoreboard, not an aggregate, and should keep showing W15–W17.
  If playoff stats are ever wanted they belong in a **separate** set, and they must be filtered to the *winners* bracket via `PLAYOFF_BRACKET_INFO` — an all-weeks-15-to-17 aggregate is exactly the noise this rule exists to keep out.
- **The nav is five tabs and that is a budget, not a snapshot.** Five at `width:20%` is exactly one mobile row; a sixth wraps it to two and undoes the 2026-08-21 consolidation. New surfaces become a **sub-view** of an existing tab. Every tab merge since has followed the same self-contained-divs pattern (`setRosterView` / `setCareersView` / `setMovesView`), and every retired hash got a `TAB_ALIASES` entry — do both.
- **Careers is All Time + Hall of Fame & Shame + one tab per season, and superlatives live in exactly one place.** All Time holds the career table and the All-Time Record Book; Hall of Fame & Shame holds the award grid; each year tab holds that season's standings and recap. The old `.career-status-bar` pill strip is gone; its 7 stats are cards in the grid now. Don't reintroduce a second surface for "league leader"-type stats — that split is exactly what this consolidated. Season standings were stacked under All Time until 2026-08-21; four tables in one scroll was a wall, and none of them had anywhere to put a write-up. **The payout cards moved to the same year tabs on the same day** — a season's money belongs next to that season's table, not on a separate tab, and putting them together is what surfaced the missing $15 (see `SEASON_PAYOUTS`).
- **The survivor pool is computed from the scoreboard, never hand-recorded.** The rule is
  deterministic and the scores are already on the page, so a hardcoded elimination list could only
  ever drift from the grid rendered directly beneath it. Same reasoning as the median game having
  one implementation shared by the Scores tab and the all-time engine. If a week's elimination
  ever looks wrong, the fix is in the *scores*, not in a manual override. See Phase 10.
- **A week's Scores page has two recap scopes and they stay separate** — one whole-league
  week-in-review at the top (`weekly-recaps-<year>.json`), and one write-up per game at the foot
  of its card (`matchup-commentary-<year>.json`). Different files, different lengths, different
  jobs. Don't collapse them into one.
- **Year standings default to Place ascending; the All Time career table defaults to Career Earnings descending.** Confirmed by Matt 2026-08-21. Both are sticky per table once a header is clicked — that is deliberate, don't reset them on tab switch.
- **Matchup commentary: 2025 is hybrid, 2026 forward is hand-written only** (Matt, 2026-08-21). Placement games (3rd, 5th) and the Consolation Final are in scope because they carry a reward; the rest of the consolation bracket gets nothing and renders no toggle. See Phase 8.
- **A manager's name is rendered through `ownerLink()`/`ridLink()`, never as bare text.** That is
  what makes every name on the site open a profile, and it is the thing a new render site will
  forget. If you add a surface that shows a manager's name, route it through the helper.
- **The profile is an overlay, not a route.** It opens over whatever you were reading and closes
  back to it, with the tab, scroll position and URL hash untouched. Don't convert it to a tab or a
  hash route — losing your place on the Scores tab is the exact failure it exists to avoid.
- **Award definitions live in `ownerAwardDefs()` only.** The Hall of Fame grid and the profile
  award standings both read it. Two lists is how the two surfaces drift.
- **\* Andrew Bova inherited roster 11 from Chris Jacobs in 2026.** Verified against the API: roster
  11's `owner_id` is `728293730280427520` ("CCJ") for 2023/24/25 and `467166827215056896` (Andrew)
  from 2026. `RM` maps roster 11 to Andrew for *every* season, so all of Chris's results already
  flowed into Andrew's totals before this was noticed. **That attribution was deliberately kept**
  (Matt's call, 2026-08-21) so the franchise history stays continuous — the star and the footnote
  on his profile are what make it honest. Do not silently re-split it; changing it would move
  career earnings, playoff berths and Hall of Fame standings. The marker is a plain `*` in
  `var(--muted)` at 60% opacity (Matt, 2026-08-21) — it appears beside his name in ~90 places, so
  anything louder read as decoration rather than a footnote.
- **Home panel has no quick-nav grid** — navigation is entirely via the icon nav and the logo home link
- **"Ask Claude" is fully gone** — panel, icon tab, JS and CSS all removed (the last of it 2026-08-20). The old note here claimed the JS "must remain because `getTradeAI()` calls them"; `getTradeAI()` had itself been removed in the June 2026 overhaul, so that was stale and kept ~20 KB of dead code alive for two months.

---

## LEAGUE CONTEXT SUMMARY

- 12 teams, dynasty format, Year 4 (2026 season — post-draft)
- Commissioner: Matt Bova — team "Show Me Your Penix"
- 2025 Champion: Jake Blackwell ("Nacua Matata") — had pick 1.12 in 2026 draft
- 2025 Consolation: Nick Merkel ("Breeces Peanut ButterCups") — had pick 1.13 in 2026 draft
- 2026 Rookie Draft: **Complete** — results pulled live from Sleeper API on Draft tab
- Contenders: Chris Bova ("Titsburg Feelers"), Jake Bogardus ("BoKnows723")
- Active traders: Chris Merkel, Nick Merkel
- 2027 rule change voted in: 1 WRRB_FLEX → WR/RB/TE FLEX (increases TE value)
- Full context in: `the-other-league-context.md`

---

## WHAT NOT TO DO

- Do not introduce React, Vue, npm, or any build tool
- Do not break the single-file structure
- Do not remove the CORS fallback chain
- Do not add back `getTradeAI()` or AI scoring dimensions to the Trade Evaluator — the June 2026 overhaul replaced them with KTC values intentionally
- Do not remove the `.cache-bar` DOM or its child IDs — they are used programmatically by `setCacheBar()` and `refreshData()`
- Do not revert the Arcade Neon palette/type (teal #21F5E4 · magenta #FF3DBE · purple #9A55FF on #06060C, Saira Condensed display) — see VISUAL THEME. The redesign lives in appended, banner-commented CSS layers at the end of `<style>`; style by class + variables.
- Do not use DM Mono for main content — it belongs only for intentional code/timestamp contexts
- Do not add the consolation winner card back to the home panel
- Do not put a text block back beside the header banner - it already reads "THE OTHER LEAGUE"
- Do not apply `drop-shadow()` to `.hdr-logo` while the banner is an opaque JPEG - see Logo Files
- Do not add the sidebar back without explicit request
- Do not add a sixth top-level nav tab — see the nav-budget rule under KEY DESIGN DECISIONS. Build it as a sub-view.
- Do not remove a `TAB_ALIASES` entry. They are the only thing keeping links already texted around the league from landing on a blank page.
- Do not put a secret, an API key or anything you would mind the league reading behind the Commissioner gate — it is a doorknob lock on a public site, and the whole file is public source.
- Do not remove the `commishStopTimer()` call in `showTab` — the monitor's poll would keep re-fetching every data file in the background for the life of the session.
- Do not give the Commissioner a nav tab. It is a panel with no button precisely so the nav stays at five; see the nav-budget rule.
- Do not restore the Rules panel, `buildScoring()` or `SLABELS` — deleted 2026-08-21 as a restatement of what Sleeper shows. `SDATA` is NOT part of that deletion; it feeds `calcPts()` and every point figure on the site.
