"""
generate_stats.py — builds stats-history.json

Fetches season + weekly stats from the Sleeper API for every player this league
has ever cared about, across every season in the league chain.

  python generate_stats.py                 full rebuild (all seasons)
  python generate_stats.py --live-only     rebuild ONLY the in-progress season
  python generate_stats.py --dry-run       report what would change, write nothing

Output: stats-history.json (commit this to the repo)

Runs unattended every Tuesday in-season via .github/workflows/tuesday-update.yml.
Paths resolve from __file__, so it does not care what directory it is invoked from.

THE PLAYER UNIVERSE IS THE WHOLE POINT OF THIS SCRIPT.
Until 2026-09-03 this seeded its player list from `/league/{lid}/rosters` alone —
i.e. only players rostered at the moment it happened to run. Anyone who was traded,
busted and got dropped simply vanished, and any feature that scored a player's
production read those players as zero rather than as missing. That silently
flattered whoever traded a bust away, which is exactly backward for the Phase 12
trade-ROI work. The universe is now the union of:

  (a) every player in every trade, in every season
  (b) every player ever taken in any of this league's drafts
  (c) every player on any roster in any season

Do not narrow this back to (c).

WHY --live-only EXISTS. A weekly unattended job that rebuilds all four seasons
re-fetches ~51 weeks of stats that can never change, and a single transient API
failure on any one of them would drop that week from a committed data file. In
--live-only mode completed seasons are copied through from the existing file
untouched and only the in-progress season is refetched. The bot uses this mode.
Either way `check_no_data_loss()` refuses to write an output that loses a season,
loses a week, or loses a meaningful number of players.

An in-progress season is handled by OMITTING empty weeks rather than writing `{}`.
`fetchWeekStats()` in index.html treats the mere presence of a week key as data and
never falls back to the live API — and it savePerm()s the result forever — so a
written-out empty week would pin every player in the live season to zero points.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error

# Windows consoles and redirected output default to cp1252, which cannot encode
# the arrows and check marks this script prints, so a hand-run or a Task Scheduler
# run died on its first status line. GitHub Actions is UTF-8 and was unaffected,
# which is why this went unnoticed. Keep this above any print().
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://api.sleeper.app/v1'
LID_2026 = '1316225642072662016'
FIRST_SEASON = 2023
MAX_WEEK = 17

TOL_ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(TOL_ROOT, 'stats-history.json')

# Refuse to publish a rebuild that loses this share of a season's players.
MAX_PLAYER_LOSS_PCT = 5.0

# Mirrors calcPts() in index.html. `pass_int_td` (pick-six thrown, -1) was missing
# here until 2026-09-03 while calcPts read it, so the site could never score it.
STAT_KEYS = [
    'gp',
    'pass_att', 'pass_cmp', 'pass_yd', 'pass_td', 'pass_int', 'pass_2pt',
    'pass_td_40p', 'pass_int_td',
    'rush_att', 'rush_yd', 'rush_td', 'rush_2pt', 'rush_40p',
    'rec', 'rec_yd', 'rec_td', 'rec_2pt',
    'rec_0_4', 'rec_5_9', 'rec_10_19', 'rec_20_29', 'rec_30_39', 'rec_40p',
    'kr_yd', 'pr_yd', 'fum_lost',
    'bonus_pass_yd_400', 'bonus_rush_yd_200', 'bonus_rec_yd_200',
]


def fetch(path, retries=3):
    url = BASE + path
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                print(f'  retry ({attempt + 1})...', end=' ')
                time.sleep(2)
            else:
                raise RuntimeError(f'Failed to fetch {url}: {e}')


def current_season():
    try:
        return int(fetch('/state/nfl')['season'])
    except Exception as e:
        print(f'  WARN: /state/nfl failed ({e}) — falling back to the 2026 league')
        return int(fetch(f'/league/{LID_2026}')['season'])


def get_league_chain():
    """season (int) -> league_id, walking previous_league_id back from the newest.

    Keyed and terminated on each league's OWN season, never on a loop counter. The
    counter version truncated the chain any time the newest league was not the season
    it was called with — which silently shrank the player universe (it dropped the
    2023 league's rosters) and would have quietly published a thinner file.
    """
    ids = {}
    lid = LID_2026
    while lid:
        info = fetch(f'/league/{lid}')
        season = int(info['season'])
        if season < FIRST_SEASON:
            break
        ids[season] = lid
        lid = info.get('previous_league_id')
    return ids


def build_universe(league_ids):
    """Union of everyone who has ever been rostered, drafted or traded here."""
    universe = set()
    counts = {}

    rostered = set()
    for year, lid in sorted(league_ids.items()):
        for r in fetch(f'/league/{lid}/rosters'):
            for pid in (r.get('players') or []):
                rostered.add(str(pid))
    counts['rostered'] = len(rostered)
    universe |= rostered

    drafted = set()
    for year, lid in sorted(league_ids.items()):
        for d in fetch(f'/league/{lid}/drafts'):
            for p in fetch(f"/draft/{d['draft_id']}/picks"):
                if p.get('player_id'):
                    drafted.add(str(p['player_id']))
            time.sleep(0.2)
    counts['drafted'] = len(drafted)
    counts['drafted_new'] = len(drafted - universe)
    universe |= drafted

    traded = set()
    for year, lid in sorted(league_ids.items()):
        # Week 0 is empty in every season of this league; weeks 1-18 hold
        # everything, with offseason trades landing in week 1 of the new league.
        for wk in range(1, 19):
            try:
                txns = fetch(f'/league/{lid}/transactions/{wk}')
            except Exception as e:
                print(f'  WARN: {year} wk{wk} transactions failed — {e}')
                continue
            for t in txns:
                if t.get('type') != 'trade' or t.get('status') != 'complete':
                    continue
                traded.update(str(p) for p in (t.get('adds') or {}))
                traded.update(str(p) for p in (t.get('drops') or {}))
            time.sleep(0.1)
    counts['traded'] = len(traded)
    counts['traded_new'] = len(traded - universe)
    universe |= traded

    return universe, counts


def fetch_week_stats(year, week, universe):
    data = fetch(f'/stats/nfl/regular/{year}/{week}')
    result = {}
    for pid, stats in (data or {}).items():
        if str(pid) not in universe:
            continue
        filtered = {k: stats[k] for k in STAT_KEYS if stats.get(k)}
        if filtered:
            result[str(pid)] = filtered
    return result


def build_season(year, universe):
    """Returns {'season':..., 'weeks':...} or None if the year has no played weeks."""
    season_agg = {}
    weeks_data = {}
    failed = []

    for week in range(1, MAX_WEEK + 1):
        print(f'  Week {week:2d}... ', end='', flush=True)
        try:
            week_stats = fetch_week_stats(year, week, universe)
        except Exception as e:
            print(f'ERROR — {e}')
            failed.append(week)
            continue

        if not week_stats:
            # Unplayed (or unreported) week. Omit it — see module docstring.
            print('no data — omitted')
            continue

        weeks_data[str(week)] = week_stats
        for pid, stats in week_stats.items():
            season_agg.setdefault(pid, {})
            for k, v in stats.items():
                season_agg[pid][k] = round(season_agg[pid].get(k, 0) + v, 4)
        print(f'{len(week_stats)} players')
        time.sleep(0.35)

    if failed:
        # Never let a flaky request quietly delete a week from a committed file.
        raise RuntimeError(
            f'{year}: weeks {failed} failed to fetch. Refusing to build a season '
            f'that would be missing them. Re-run when the API is healthy.')

    if not season_agg:
        return None
    return {'season': season_agg, 'weeks': weeks_data}


def check_no_data_loss(existing, new):
    """Hard gate before writing. Returns a list of problems (empty == safe)."""
    problems = []
    warnings = []
    for year in sorted(k for k in existing if k != 'generated'):
        if year not in new:
            problems.append(f'{year}: present in the existing file, absent from the rebuild')
            continue
        lost_weeks = sorted(set(existing[year]['weeks']) - set(new[year]['weeks']), key=int)
        if lost_weeks:
            problems.append(f'{year}: rebuild is missing week(s) {lost_weeks}')
        was, now = len(existing[year]['season']), len(new[year]['season'])
        if now < was:
            pct = (was - now) / was * 100
            msg = f'{year}: player count fell {was} -> {now} ({pct:.1f}%)'
            (problems if pct > MAX_PLAYER_LOSS_PCT else warnings).append(msg)
    for w in warnings:
        print(f'  WARN: {w}')
    return problems


def write_atomic(path, text):
    """Never open(path,'w') this file — a mid-write crash would leave a 1MB+
    committed data file truncated to nothing."""
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='') as f:
        f.write(text)
    os.replace(tmp, path)


def unchanged_but_for_stamp(path, payload):
    """True when the only thing that would change on disk is the `generated` date.

    These builders run unattended every Tuesday, year round. Without this the bot
    rewrites a 1.3 MB data file and pushes a commit whose entire content is a
    one-character date bump, every week of the offseason — which buries the weeks
    where something actually happened. Skipping the write keeps the git log
    meaningful: a commit here means the numbers moved.
    """
    try:
        with open(path, encoding='utf-8') as f:
            old = json.load(f)
    except Exception:
        return False
    # Round-trip the payload first so both sides carry JSON's string keys. An
    # in-memory dict keyed by int (pick_curve.by_pick) sorts numerically while the
    # same data loaded back from disk sorts lexicographically ("1","10","11",..,"2"),
    # so without this the compare reports a change on every single run and the
    # skip never fires.
    fresh = json.loads(json.dumps(payload))
    a = {k: v for k, v in old.items() if k != 'generated'}
    b = {k: v for k, v in fresh.items() if k != 'generated'}
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def load_existing():
    try:
        with open(OUT_PATH, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--live-only', action='store_true',
                    help='rebuild only the in-progress season; copy completed seasons through')
    ap.add_argument('--dry-run', action='store_true',
                    help='report what would change, write nothing')
    args = ap.parse_args()

    existing = load_existing()
    live = current_season()
    print(f'Current NFL season: {live}')

    print('Fetching league ID chain...')
    league_ids = get_league_chain()
    print(f'  {dict(sorted(league_ids.items()))}')

    print('\nBuilding player universe...')
    universe, counts = build_universe(league_ids)
    print(f"  rostered (any season) : {counts['rostered']}")
    print(f"  drafted               : {counts['drafted']}  (+{counts['drafted_new']} new)")
    print(f"  traded                : {counts['traded']}  (+{counts['traded_new']} new)")
    print(f'  UNIVERSE              : {len(universe)}')

    if args.live_only:
        targets = [live] if live in league_ids else []
        if not targets:
            print(f'\nNothing to do — {live} is not in the league chain.')
            return 0
        print(f'\n--live-only: rebuilding {live}; '
              f'copying through {sorted(k for k in existing if k != "generated")}')
    else:
        targets = sorted(league_ids, reverse=True)

    output = {'generated': time.strftime('%Y-%m-%d')}
    if args.live_only:
        for k, v in existing.items():
            if k != 'generated':
                output[k] = v

    for year in targets:
        print(f'\n=== {year} (league {league_ids[year]}) ===')
        try:
            built = build_season(year, universe)
        except RuntimeError as e:
            print(f'\nABORTED: {e}')
            return 1

        if built is None:
            print(f'  {year} has no played weeks yet — omitting the year entirely')
            output.pop(str(year), None)
            continue
        output[str(year)] = built

    problems = check_no_data_loss(existing, output)
    if problems:
        print('\nABORTED — the rebuild would lose data:')
        for p in problems:
            print(f'  - {p}')
        print('Nothing written. Existing stats-history.json is untouched.')
        return 1

    years = sorted(k for k in output if k != 'generated')
    print('\nResult:')
    for y in years:
        was = len(existing.get(y, {}).get('season', {}))
        now = len(output[y]['season'])
        delta = f'  ({now - was:+d})' if was and now != was else ''
        print(f'  {y}: {now} players, {len(output[y]["weeks"])} weeks{delta}')
    for y in sorted(k for k in existing if k != 'generated'):
        if y not in output:
            print(f'  {y}: dropped (no played weeks)')

    if unchanged_but_for_stamp(OUT_PATH, output):
        print('')
        print('No change beyond the date stamp — leaving the file alone.')
        return 0

    raw = json.dumps(output, separators=(',', ':'))
    if args.dry_run:
        print(f'\n--dry-run: would write {len(raw) / 1024:.1f} KB to {OUT_PATH}')
        return 0

    write_atomic(OUT_PATH, raw)
    print(f'\nWrote {OUT_PATH} — {len(raw) / 1024:.1f} KB')
    return 0


if __name__ == '__main__':
    sys.exit(main())
