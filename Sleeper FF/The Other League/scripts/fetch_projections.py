#!/usr/bin/env python3
"""
fetch_projections.py — pull Sleeper's rest-of-season projections and write
projections-<year>.json to the TOL folder.

Why this exists
---------------
index.html used to pull all 17 weeks of projections straight from Sleeper on
every visit to the Stats tab. That endpoint returns ~590 KB per week for all
~9,400 NFL players, so the page was downloading roughly 10 MB before it could
render a single row — brutal on mobile.

This script does the same fetch once a day in CI, throws away every player who
has no meaningful projection and every stat key this league doesn't score, and
commits the result. The site loads that file the same way it already loads
ktc-values.json, and falls back to the live API if the file is missing or
stale, so nothing breaks if this bot stops running.

IMPORTANT — the endpoint needs "regular" in the PATH:
    /projections/nfl/regular/{season}/{week}     ✓ populated
    /projections/nfl/{season}/{week}?season_type=regular   ✗ HTTP 200, all empty
The second form returns 200 with an empty {} for every real player, which is
why this was silently broken for so long. Don't "simplify" it back.

Usage:
  python scripts/fetch_projections.py              # current season, weeks 1-17
  python scripts/fetch_projections.py --year 2027
  python scripts/fetch_projections.py --dry-run    # report, write nothing
"""

import argparse
import json
import os
import sys
import time

import requests

# Windows consoles and redirected output default to cp1252, which cannot encode
# the arrows and check marks this script prints, so a hand-run or a Task Scheduler
# run died on its first status line. GitHub Actions is UTF-8 and was unaffected,
# which is why this went unnoticed. Keep this above any print().
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

API = 'https://api.sleeper.app/v1'
WEEKS = list(range(1, 18))

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOL_ROOT = os.path.dirname(_SCRIPT_DIR)

# Only the keys calcPts() in index.html actually scores. Everything else Sleeper
# returns (adp_dd_ppr, cmp_pct, pts_ppr, the whole IDP block...) is dead weight.
STAT_KEYS = [
    'gp',
    'pass_att', 'pass_cmp', 'pass_yd', 'pass_td', 'pass_int', 'pass_2pt',
    'pass_td_40p', 'pass_int_td', 'bonus_pass_yd_400',
    'rush_att', 'rush_yd', 'rush_td', 'rush_2pt', 'rush_40p', 'bonus_rush_yd_200',
    'rec', 'rec_yd', 'rec_td', 'rec_2pt',
    'rec_0_4', 'rec_5_9', 'rec_10_19', 'rec_20_29', 'rec_30_39', 'rec_40p',
    'bonus_rec_yd_200',
    'kr_yd', 'pr_yd', 'fum_lost',
]

# Skill positions only — this league starts QB/RB/WR/TE and nothing else.
KEEP_POSITIONS = {'QB', 'RB', 'WR', 'TE'}


def fetch(url):
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f'ERROR: {url} — {e}', file=sys.stderr)
        return None


def current_season():
    state = fetch(f'{API}/state/nfl')
    if not state:
        return None
    return int(state.get('season') or 0) or None


def load_positions():
    """player_id -> position, from Sleeper's players dump (~5 MB, fetched once)."""
    print('Fetching player metadata ...')
    players = fetch(f'{API}/players/nfl')
    if not players:
        print('ERROR: could not load player metadata', file=sys.stderr)
        sys.exit(1)
    return {pid: (p.get('position') or '') for pid, p in players.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', type=int, default=None,
                    help='season to fetch (default: current season from Sleeper)')
    ap.add_argument('--dry-run', action='store_true',
                    help='print what would be written without writing it')
    args = ap.parse_args()

    year = args.year or current_season()
    if not year:
        print('ERROR: could not determine the season', file=sys.stderr)
        sys.exit(1)

    positions = load_positions()

    weeks = {}
    kept_total = 0
    for w in WEEKS:
        raw = fetch(f'{API}/projections/nfl/regular/{year}/{w}')
        if raw is None:
            print(f'  week {w:>2}: request failed — skipping', file=sys.stderr)
            continue

        week_out = {}
        for pid, stats in (raw or {}).items():
            if not isinstance(stats, dict):
                continue
            if positions.get(pid) not in KEEP_POSITIONS:
                continue
            trimmed = {}
            for k in STAT_KEYS:
                v = stats.get(k)
                if isinstance(v, (int, float)) and v:
                    trimmed[k] = round(float(v), 2)
            # Sleeper hands back a stub ({"adp_dd_ppr": 1000.0}) for players with
            # no real projection, and a bare {"gp": 1.0} for players who have a
            # game but no projected production. Keep anyone with at least one
            # stat THIS LEAGUE scores.
            #
            # Deliberately NOT filtered on pts_ppr: that's Sleeper's generic
            # scoring, which weighs things differently than this league does
            # (flat PPR, no distance buckets, no return yards). Using it as the
            # gate would let Sleeper decide who matters to us — and would drop,
            # say, a pure return specialist who scores here via kr_yd/pr_yd at
            # 0.04/yd but rounds to nothing under generic PPR.
            if any(k != 'gp' for k in trimmed):
                week_out[pid] = trimmed

        if week_out:
            weeks[str(w)] = week_out
            kept_total += len(week_out)
        print(f'  week {w:>2}: {len(week_out):>4} players kept (of {len(raw or {})})')

    if not weeks:
        print('ERROR: no projection data for any week — aborting without writing',
              file=sys.stderr)
        sys.exit(1)

    # Sanity floor: a healthy full-season pull is 800+ players in week 1. Bail
    # rather than commit a gutted file over a good one.
    wk1 = len(weeks.get('1', {}))
    if wk1 and wk1 < 200:
        print(f'ERROR: week 1 only had {wk1} players (expected 200+) — aborting',
              file=sys.stderr)
        sys.exit(1)

    out = {
        'season': year,
        'weeks': weeks,
        'ts': int(time.time() * 1000),
    }

    dest = os.path.join(TOL_ROOT, f'projections-{year}.json')
    if args.dry_run:
        size = len(json.dumps(out, separators=(',', ':')))
        print(f'\n[dry run] would write {dest} - {len(weeks)} weeks, '
              f'{kept_total} player-weeks, {size/1024:.0f} KB')
        return

    with open(dest, 'w') as f:
        json.dump(out, f, separators=(',', ':'))

    size = os.path.getsize(dest)
    print(f'\nOK - wrote {dest} - {len(weeks)} weeks, {kept_total} player-weeks, '
          f'{size/1024:.0f} KB')


if __name__ == '__main__':
    main()
