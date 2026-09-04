"""
build_replacement_levels.py — builds replacement-levels.json

Phase 12 scores every asset in **points over replacement (PoR)**: what a player
produced, minus what a replacement-level player at his position produced over the
same span. Raw points are unusable as a trade score in a superflex league, because
whoever receives the quarterback wins every trade on volume alone.

  python scripts/build_replacement_levels.py      (run from the project root)

Output: replacement-levels.json (commit this to the repo)

  { "generated": "...", "ranks": {...}, "window": 5,
    "levels": { "2025": { "1": { "QB": 12.4, "RB": 5.1, ... } } } }

TWO THINGS HERE ARE EASY TO GET WRONG.

1. Replacement is computed **per position per week**, never per season. A season-level
   baseline quietly punishes anyone whose player had a bye or missed three games, because
   his zero weeks get measured against a full-season bar.

2. Replacement is computed over the **entire NFL player pool**, not over
   stats-history.json. stats-history.json holds only players this league has rostered,
   drafted or traded — a pool already filtered to fantasy-relevant players. Ranking within
   it would put the "replacement" bar far too high and make every real asset look
   replaceable.

The ranks below are MEASURED, not assumed. They come from counting the actual position
of every started player across 42 real league-weeks (2023-2025, weeks 1-14, the
`starters` array on /league/{lid}/matchups/{week}) — WR 55.6, RB 37.0, QB 22.2, TE 17.0
per league-week. Re-measure with scripts/measure_starter_mix.py if roster_positions
ever changes; do not hand-edit these.
"""
import argparse
import json
import os
import sys
import time
import urllib.request

BASE = 'https://api.sleeper.app/v1'
TOL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRST_SEASON = 2023
LAST_SEASON = 2026
MAX_WEEK = 17

# Replacement rank per position = (avg started league-wide) + 1. See docstring.
REPLACEMENT_RANKS = {'QB': 23, 'RB': 38, 'WR': 57, 'TE': 18}

# A single rank is a noisy weekly baseline — one boom game by the exact Nth player
# swings every PoR figure that week. Average a small band centred on N instead.
WINDOW = 5

POSITIONS = ('QB', 'RB', 'WR', 'TE')

# Mirrors SDATA in index.html. Distance-based PPR: `rec` itself is worth 0, the
# points come from the rec_<depth> buckets. TE premium is bonus_rec_te per catch.
SDATA = {
    "pass_yd": 0.04, "pass_td": 4.0, "pass_int": -2.0, "pass_2pt": 2.0,
    "pass_td_40p": 2.0, "pass_int_td": -1.0, "bonus_pass_yd_400": 2.0,
    "rush_yd": 0.1, "rush_td": 6.0, "rush_2pt": 2.0, "rush_40p": 1.0,
    "bonus_rush_yd_200": 2.0,
    "rec": 0.0, "rec_yd": 0.1, "rec_td": 6.0, "rec_2pt": 2.0,
    "rec_0_4": 0.5, "rec_5_9": 0.75, "rec_10_19": 1.0, "rec_20_29": 1.0,
    "rec_30_39": 1.0, "rec_40p": 2.0, "bonus_rec_yd_200": 2.0,
    "bonus_rec_te": 0.5,
    "kr_yd": 0.04, "pr_yd": 0.04, "fum_lost": -2.0,
}

_SCORED = [k for k in SDATA if k != 'bonus_rec_te']


def calc_pts(stats, pos):
    """Byte-for-byte equivalent of calcPts(stats,pos) in index.html."""
    if not stats:
        return 0.0
    pts = 0.0
    for k in _SCORED:
        v = stats.get(k)
        if v:
            pts += v * SDATA[k]
    if pos == 'TE' and stats.get('rec'):
        pts += stats['rec'] * SDATA['bonus_rec_te']
    return round(pts * 10) / 10


def fetch(path, retries=3):
    url = BASE + path
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise RuntimeError(f'Failed to fetch {url}: {e}')


def write_atomic(path, text):
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
        with open(os.path.join(TOL_ROOT, 'replacement-levels.json'), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def current_season():
    try:
        return int(fetch('/state/nfl')['season'])
    except Exception:
        return LAST_SEASON


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--live-only', action='store_true',
                    help='rebuild only the in-progress season; copy completed years through')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    existing = load_existing()
    prior = existing.get('levels', {})

    print('Fetching player positions (~5 MB)...')
    pdb = fetch('/players/nfl')
    pos_of = {str(k): (v.get('position') or '') for k, v in pdb.items()}
    print(f'  {len(pos_of)} players')

    if args.live_only:
        live = current_season()
        years = [live]
        print(f'--live-only: rebuilding {live}; copying through {sorted(prior)}')
    else:
        years = list(range(FIRST_SEASON, LAST_SEASON + 1))

    levels = {k: v for k, v in prior.items()} if args.live_only else {}
    for year in years:
        year_out = {}
        print(f'\n=== {year} ===')
        for week in range(1, MAX_WEEK + 1):
            try:
                data = fetch(f'/stats/nfl/regular/{year}/{week}')
            except Exception as e:
                print(f'  Week {week:2d}  ERROR — {e}')
                continue
            if not data:
                print(f'  Week {week:2d}  no data — omitted')
                continue

            by_pos = {p: [] for p in POSITIONS}
            for pid, stats in data.items():
                p = pos_of.get(str(pid))
                if p in by_pos:
                    by_pos[p].append(calc_pts(stats, p))

            if not any(by_pos.values()):
                print(f'  Week {week:2d}  no scored production — omitted')
                continue

            wk = {}
            for p in POSITIONS:
                scores = sorted(by_pos[p], reverse=True)
                n = REPLACEMENT_RANKS[p]
                lo = max(0, n - 1 - WINDOW // 2)
                band = scores[lo:lo + WINDOW]
                # A short week (fewer ranked players than the band) still gets a
                # baseline from whatever is there rather than silently becoming 0.
                wk[p] = round(sum(band) / len(band), 2) if band else 0.0
            year_out[str(week)] = wk
            print('  Week {:2d}  '.format(week)
                  + '  '.join(f'{p} {wk[p]:5.1f}' for p in POSITIONS))
            time.sleep(0.35)

        if year_out:
            levels[str(year)] = year_out
        elif str(year) in levels:
            print(f'  {year} produced nothing this run — keeping the existing entry')
        else:
            print(f'  {year} has no played weeks yet — omitted')

    # Same gate as generate_stats.py: an unattended weekly job must never publish a
    # thinner file than the one it replaces. Any uncovered week is silently skipped
    # downstream by build_trade_roi.py rather than raising, so a quiet loss here
    # becomes a page full of zeros with nothing to trace it back to.
    problems = []
    for y in sorted(prior):
        if y not in levels:
            problems.append(f'{y}: present in the existing file, absent from this run')
            continue
        lost = sorted(set(prior[y]) - set(levels[y]), key=int)
        if lost:
            problems.append(f'{y}: this run is missing week(s) {lost}')
    if problems:
        print('\nABORTED — the rebuild would lose baselines:')
        for p_ in problems:
            print(f'  - {p_}')
        print('Nothing written. Existing replacement-levels.json is untouched.')
        return 1

    out = {
        'generated': time.strftime('%Y-%m-%d'),
        'ranks': REPLACEMENT_RANKS,
        'window': WINDOW,
        'note': 'Weekly points-over-replacement baselines, league scoring (SDATA). '
                'Ranks measured from actual started-lineup position mix, 2023-2025.',
        'levels': levels,
    }
    path = os.path.join(TOL_ROOT, 'replacement-levels.json')
    if unchanged_but_for_stamp(path, out):
        print('')
        print('No change beyond the date stamp — leaving the file alone.')
        return 0
    raw = json.dumps(out, separators=(',', ':'))
    if args.dry_run:
        print(f'\n--dry-run: would write {len(raw)/1024:.1f} KB to {path}')
        return 0
    write_atomic(path, raw)
    print(f'\nWrote {path} — {len(raw) / 1024:.1f} KB')
    for y in sorted(levels):
        wks = levels[y]
        for p in POSITIONS:
            vals = [wks[w][p] for w in wks]
            print(f'  {y} {p}: mean {sum(vals) / len(vals):5.2f}  '
                  f'min {min(vals):5.2f}  max {max(vals):5.2f}  ({len(vals)} weeks)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
