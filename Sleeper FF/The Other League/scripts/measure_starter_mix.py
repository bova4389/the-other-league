"""
measure_starter_mix.py — measures the league's real positional starter mix

This is where REPLACEMENT_RANKS in build_replacement_levels.py comes from. It counts
the position of every player actually started, league-wide, across every completed
regular-season week, and reports the average per league-week. Replacement rank for a
position is that average + 1: the best player at that position who is NOT starting
anywhere in the league on a given week.

  python scripts/measure_starter_mix.py       (run from the project root)

Prints a table; writes nothing. Re-run and hand-update REPLACEMENT_RANKS in
build_replacement_levels.py if `roster_positions` ever changes — the flex slots make
the mix impossible to read off the settings alone. As of 2026-09-03 the league runs
1 QB / 2 RB / 2 WR / 1 TE / 1 FLEX / 3 WRRB_FLEX / 1 SUPER_FLEX = 11 starters, which
does not tell you how the 48 flex slots actually get filled. Measuring does.

Regular season only (weeks 1-14), matching REG_WEEKS in index.html — weeks 15-17 mix
the championship bracket with consolation games where lineups are often stale or unset,
which is precisely the wrong input for "what does a startable player look like".
"""
import json
import time
import urllib.request
from collections import Counter

BASE = 'https://api.sleeper.app/v1'
LID_2026 = '1316225642072662016'
REG_WEEKS = 14
POSITIONS = ('QB', 'RB', 'WR', 'TE')


def fetch(path, retries=3):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(BASE + path, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise RuntimeError(f'Failed to fetch {BASE + path}: {e}')


def main():
    print('Fetching player positions (~5 MB)...')
    pdb = fetch('/players/nfl')
    pos_of = {str(k): (v.get('position') or '') for k, v in pdb.items()}

    chain = []
    lid = LID_2026
    while lid:
        lg = fetch(f'/league/{lid}')
        chain.append((lg['season'], lid))
        lid = lg.get('previous_league_id')

    counts = Counter()
    league_weeks = 0
    for season, lid in chain:
        for wk in range(1, REG_WEEKS + 1):
            try:
                ms = fetch(f'/league/{lid}/matchups/{wk}')
            except Exception:
                continue
            if not ms:
                continue
            # An unplayed week is NOT an absent week: Sleeper returns all 17 weeks of
            # a future season as 12 rows with real matchup_ids, and managers set 2026
            # lineups months early — so `starters` is populated for weeks nobody has
            # played. Screening on starters alone pulled 14 phantom 2026 league-weeks
            # into the mix and moved WR from 55.6 to 53.7. Require actual points, the
            # same test weekWasPlayed() makes in index.html.
            if not any((m.get('points') or 0) > 0 for m in ms):
                continue
            starters = [s for m in ms for s in (m.get('starters') or []) if s and s != '0']
            if not starters:
                continue
            league_weeks += 1
            for s in starters:
                counts[pos_of.get(str(s), '?')] += 1
            time.sleep(0.15)

    print(f'\nMeasured over {league_weeks} league-weeks '
          f'({chain[-1][0]}-{chain[0][0]}, weeks 1-{REG_WEEKS})\n')
    print(f'{"Pos":5s} {"Started/league-week":>20s} {"Replacement rank":>18s}')
    for p in POSITIONS:
        avg = counts[p] / league_weeks if league_weeks else 0
        print(f'{p:5s} {avg:20.1f} {round(avg) + 1:18d}')
    other = {k: v for k, v in counts.items() if k not in POSITIONS}
    if other:
        print(f'\nStarted at other positions (not scored for PoR): {other}')


if __name__ == '__main__':
    main()
