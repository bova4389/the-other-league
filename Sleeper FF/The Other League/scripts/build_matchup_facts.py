#!/usr/bin/env python3
"""
build_matchup_facts.py — assemble a per-matchup fact sheet for a completed
season, to write Scores-tab commentary from.

Why this exists
---------------
index.html's fetchAllMatchups() trims each week down to
{roster_id, points, matchup_id, starters} before caching it. That is the right
call for the site — it keeps localStorage small — but it throws away
players_points and starters_points, which is exactly the detail that makes a
matchup write-up worth reading ("you left 31 on the bench and lost by 4").

This script goes back to the live Sleeper payload, which still has all of it,
pairs every starter's ACTUAL score against that week's PROJECTION scored
through this league's own rules, and writes a facts file. The facts file is an
offline working document — it is NOT shipped to the browser. The commentary
written from it (matchup-commentary-<year>.json) is what ships.

Scoring
-------
Projections are scored with a direct port of calcPts() from index.html, fed by
the league's own live scoring_settings rather than a hardcoded table, so this
can never drift out of sync with the site. Sleeper's own pts_ppr/pts_half_ppr
fields are ignored on purpose — they are generic scoring and know nothing
about this league's distance-PPR buckets or TE premium.

Actual scores are taken from Sleeper's players_points verbatim. They are the
authoritative record of what happened; recomputing them would only introduce
a way to be wrong.

The projections endpoint needs "regular" in the PATH:
    /projections/nfl/regular/{season}/{week}     ok - populated
    /projections/nfl/{season}/{week}             returns 200 with empty {}
See the same warning in fetch_projections.py. Don't "simplify" it back.

Usage:
  python scripts/build_matchup_facts.py --year 2025
  python scripts/build_matchup_facts.py --year 2025 --weeks 1,17
  python scripts/build_matchup_facts.py --year 2025 --out /some/path/facts.json
"""

import argparse
import json
import os
import statistics
import sys

import requests

API = 'https://api.sleeper.app/v1'
CURRENT_LID = '1316225642072662016'

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOL_ROOT = os.path.dirname(_SCRIPT_DIR)

REG_WEEKS = 14          # 1-14 regular season; 15-17 are the brackets
NAILBITER = 5.0         # margin under this is a nailbiter
BLOWOUT = 40.0          # margin over this is a blowout
NOTABLE_DELTA = 8.0     # proj-vs-actual gap worth calling out

# roster_id (1-12) -> owner name. Mirrors RM + TEAMS in index.html.
ROSTER_OWNER = {
    1: 'Matt Bova', 2: 'Jake Bogardus', 3: 'Jared Hayes', 4: 'Chris Bova',
    5: 'Nick Bova', 6: 'Erin Jacobs', 7: 'Jake Blackwell', 8: 'Chris Merkel',
    9: 'Mitch Blackwell', 10: 'Nick Merkel', 11: 'Andrew Bova',
    12: 'Duane Gillenwater',
}
OWNER_TEAM = {
    'Matt Bova': 'Show Me Your Penix', 'Jake Bogardus': 'BoKnows723',
    'Jared Hayes': 'SirWinsAlot', 'Chris Bova': 'Titsburg Feelers',
    'Nick Bova': 'Nabers in Paris', 'Erin Jacobs': 'eejacobs',
    'Jake Blackwell': 'Nacua Matata',
    'Chris Merkel': 'Your Team is the PITTsMAN',
    'Mitch Blackwell': 'i LOVE mendoza',
    'Nick Merkel': 'Breeces Peanut ButterCups',
    'Andrew Bova': 'Joshin Around',
    'Duane Gillenwater': 'Enter the Maye-Trix',
}

RIVALRY_WEEKS = {2025: [4, 13], 2026: [4, 13]}

# Mirrors LINEUP_SLOT_ELIGIBILITY in index.html.
SLOT_ELIGIBILITY = {
    'QB': ['QB'], 'RB': ['RB'], 'WR': ['WR'], 'TE': ['TE'],
    'FLEX': ['RB', 'WR', 'TE'], 'WRRB_FLEX': ['RB', 'WR'],
    'SUPER_FLEX': ['QB', 'RB', 'WR', 'TE'],
}

# Bracket labels for W15-17, keyed year -> week -> "NameA|NameB" (sorted).
# Kept in sync with PLAYOFF_BRACKET_INFO in index.html.
PLAYOFF_BRACKET_INFO = {
    2025: {
        15: {
            'Jake Blackwell|Jared Hayes': 'Winners Bracket - Round 1',
            'Chris Merkel|Nick Bova': 'Winners Bracket - Round 1',
            'Matt Bova|Mitch Blackwell': 'Consolation - Round 1',
            'Erin Jacobs|Nick Merkel': 'Consolation - Round 1',
        },
        16: {
            'Jake Blackwell|Jake Bogardus': 'Winners Bracket - Semifinal',
            'Chris Bova|Nick Bova': 'Winners Bracket - Semifinal',
            'Chris Merkel|Jared Hayes': '5th Place Match',
            'Duane Gillenwater|Mitch Blackwell': 'Consolation - Semifinal',
            'Andrew Bova|Nick Merkel': 'Consolation - Semifinal',
            'Erin Jacobs|Matt Bova': 'Consolation',
        },
        17: {
            'Jake Blackwell|Nick Bova': 'Championship - 1st Place',
            'Chris Bova|Jake Bogardus': '3rd Place Match',
            'Mitch Blackwell|Nick Merkel': 'Consolation Final - 13th Pick',
            'Andrew Bova|Duane Gillenwater': 'Consolation',
        },
    },
}


def commented(label):
    """Does a bracket-labelled game get commentary?

    Regular-season games always do (label is None). In the brackets, the games
    that mattered are the winners bracket plus the three placement games that
    carry a reward: 3rd, 5th, and the consolation final -- which in this league
    is not a nothing game at all, it hands the winner the 1.13 rookie pick.
    A bare "Consolation" or "Consolation - Round 1/Semifinal" gets nothing.
    """
    if not label:
        return True
    keep = ('Winners Bracket', 'Championship', '3rd Place',
            '5th Place', 'Consolation Final')
    return any(k in label for k in keep)


def fetch(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def find_league_id(year):
    """Walk previous_league_id back from the current league to `year`."""
    lid = CURRENT_LID
    seen = {}
    for _ in range(10):
        lg = fetch(f'{API}/league/{lid}')
        seen[int(lg['season'])] = lid
        if int(lg['season']) == year:
            return lid, lg
        prev = lg.get('previous_league_id')
        if not prev:
            break
        lid = prev
    raise SystemExit(f'ERROR: no league found for {year} (saw {sorted(seen)})')


def load_players(cache_dir):
    """player_id -> {name, position}. Cached; the dump is ~5 MB."""
    path = os.path.join(cache_dir, 'players_nfl.json')
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    print('Fetching player metadata (~5 MB, once) ...')
    raw = fetch(f'{API}/players/nfl')
    out = {}
    for pid, p in raw.items():
        name = p.get('full_name') or ' '.join(
            x for x in [p.get('first_name'), p.get('last_name')] if x)
        out[pid] = {
            'name': name or pid,
            'pos': p.get('position') or '',
            'team': p.get('team') or 'FA',
        }
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    return out


def make_calc_pts(scoring):
    """Port of calcPts() from index.html, bound to the league's own scoring."""
    s = scoring

    def g(k):
        v = s.get(k)
        return v if isinstance(v, (int, float)) else 0.0

    plain = [
        'pass_yd', 'pass_td', 'pass_int', 'pass_2pt', 'pass_td_40p',
        'pass_int_td', 'bonus_pass_yd_400',
        'rush_yd', 'rush_td', 'rush_2pt', 'rush_40p', 'bonus_rush_yd_200',
        'rec', 'rec_yd', 'rec_td', 'rec_2pt',
        'rec_0_4', 'rec_5_9', 'rec_10_19', 'rec_20_29', 'rec_30_39', 'rec_40p',
        'bonus_rec_yd_200', 'kr_yd', 'pr_yd', 'fum_lost',
    ]
    weights = [(k, g(k)) for k in plain]
    te_bonus = g('bonus_rec_te')

    def calc(stats, pos):
        if not stats:
            return 0.0
        pts = 0.0
        for k, w in weights:
            if w:
                v = stats.get(k)
                if isinstance(v, (int, float)):
                    pts += v * w
        if pos == 'TE' and te_bonus:
            v = stats.get('rec')
            if isinstance(v, (int, float)):
                pts += v * te_bonus
        return round(pts, 2)

    return calc


def optimal_lineup(pids, points, players, slots):
    """Greedy optimal-lineup solve. Port of computeOptimalLineup().

    Fills the most position-restrictive slots first so a scarce single-position
    starter never loses their spot to a more flexible slot filled out of order.
    Returns (total, [(slot, pid)]).
    """
    order = sorted(
        [sl for sl in slots if sl in SLOT_ELIGIBILITY],
        key=lambda sl: len(SLOT_ELIGIBILITY[sl]))
    used = set()
    total = 0.0
    picks = []
    for sl in order:
        elig = SLOT_ELIGIBILITY[sl]
        best, best_pts = None, None
        for pid in pids:
            if pid in used:
                continue
            if players.get(pid, {}).get('pos') not in elig:
                continue
            p = points.get(pid, 0.0)
            if best_pts is None or p > best_pts:
                best, best_pts = pid, p
        if best is not None:
            used.add(best)
            total += best_pts or 0.0
            picks.append((sl, best))
    return round(total, 2), picks


def best_legal_swap(entry_starters, bench, points, players, slots):
    """The single bench-for-starter swap that gains the most points.

    Returns {gain, in_pid, out_pid, slot} or None. Only considers swaps that
    are positionally legal for the slot the starter actually occupied.

    Caveat: Sleeper's historical matchup payload gives one flat `players` list
    with no taxi/IR split, and the /rosters endpoint only reports CURRENT
    state, so a retroactive taxi player is indistinguishable from a bench
    player here. In practice that barely matters -- an IR player scores 0 and
    never surfaces as the best swap.
    """
    slot_list = [sl for sl in slots if sl in SLOT_ELIGIBILITY]
    best = None
    for idx, out_pid in enumerate(entry_starters):
        if idx >= len(slot_list):
            break
        slot = slot_list[idx]
        elig = SLOT_ELIGIBILITY[slot]
        out_pts = points.get(out_pid, 0.0)
        for in_pid in bench:
            if players.get(in_pid, {}).get('pos') not in elig:
                continue
            gain = points.get(in_pid, 0.0) - out_pts
            if gain > 0 and (best is None or gain > best['gain']):
                best = {'gain': round(gain, 2), 'in_pid': in_pid,
                        'out_pid': out_pid, 'slot': slot}
    return best


def pos_group_totals(pids, points, players):
    out = {'QB': 0.0, 'RB': 0.0, 'WR': 0.0, 'TE': 0.0}
    for pid in pids:
        pos = players.get(pid, {}).get('pos')
        if pos in out:
            out[pos] += points.get(pid, 0.0)
    return {k: round(v, 2) for k, v in out.items()}


def build(year, weeks_filter, out_path, cache_dir):
    lid, league = find_league_id(year)
    print(f'{year} league: {lid}')
    scoring = league.get('scoring_settings') or {}
    if not isinstance(scoring.get('rec_yd'), (int, float)):
        raise SystemExit('ERROR: league scoring_settings look wrong - aborting')
    calc_pts = make_calc_pts(scoring)
    slots = [s for s in (league.get('roster_positions') or []) if s != 'BN']
    print(f'  scoring: rec={scoring.get("rec")} '
          f'bonus_rec_te={scoring.get("bonus_rec_te")}  slots={len(slots)}')

    players = load_players(cache_dir)

    weeks = weeks_filter or list(range(1, 18))
    bracket_year = PLAYOFF_BRACKET_INFO.get(year, {})

    # Running context that only makes sense walked in week order, so always
    # walk 1..17 even when only writing out a subset.
    records = {rid: {'w': 0, 'l': 0} for rid in ROSTER_OWNER}
    streaks = {rid: {'kind': None, 'len': 0} for rid in ROSTER_OWNER}
    h2h = {}
    season_scores = {rid: [] for rid in ROSTER_OWNER}

    out = {'season': year, 'league_id': lid, 'matchups': {}}
    skipped = 0

    for wk in range(1, 18):
        try:
            raw = fetch(f'{API}/league/{lid}/matchups/{wk}')
        except requests.RequestException as e:
            print(f'  week {wk:>2}: fetch failed - {e}', file=sys.stderr)
            continue
        pairs = {}
        for e in raw or []:
            if e.get('matchup_id'):
                pairs.setdefault(e['matchup_id'], []).append(e)
        pairs = {k: v for k, v in pairs.items() if len(v) == 2}
        played = [p for p in pairs.values()
                  if any((x.get('points') or 0) > 0 for x in p)]
        if not played:
            print(f'  week {wk:>2}: not played - skipping')
            continue

        proj_raw = {}
        try:
            proj_raw = fetch(f'{API}/projections/nfl/regular/{year}/{wk}') or {}
        except requests.RequestException:
            print(f'  week {wk:>2}: projections unavailable', file=sys.stderr)
        proj_pts = {}
        for pid, st in proj_raw.items():
            if not isinstance(st, dict):
                continue
            pos = players.get(pid, {}).get('pos')
            if pos not in ('QB', 'RB', 'WR', 'TE'):
                continue
            v = calc_pts(st, pos)
            if v:
                proj_pts[pid] = v

        # League median for the week -- this is a median league, so every team
        # plays two games: their opponent, and the field.
        all_scores = sorted((e.get('points') or 0.0)
                            for p in played for e in p)
        median = statistics.median(all_scores) if all_scores else 0.0

        # Sleeper's projections run optimistic, and by a DIFFERENT amount each
        # week (2025 ranged from -29.6 in W1 to +7.4 in W5 league-wide). So a
        # raw "underperformed by 25" is worthless -- in week 1 that was simply
        # average. Every proj-vs-actual claim has to be net of the week's own
        # bias, which is the median of all twelve teams' deltas.
        week_deltas = []
        for p in played:
            for e in p:
                st = [str(x) for x in (e.get('starters') or []) if x and x != '0']
                pt = sum(proj_pts.get(pid, 0.0) for pid in st)
                if pt:
                    week_deltas.append((e.get('points') or 0.0) - pt)
        proj_bias = round(statistics.median(week_deltas), 2) if week_deltas else 0.0

        wrote = 0
        for mid, pair in sorted(pairs.items()):
            if not any((x.get('points') or 0) > 0 for x in pair):
                continue
            a, b = pair
            # Stable ordering: higher score first, so "a" is always the winner.
            if (b.get('points') or 0) > (a.get('points') or 0):
                a, b = b, a

            names = sorted([ROSTER_OWNER[a['roster_id']],
                            ROSTER_OWNER[b['roster_id']]])
            label = bracket_year.get(wk, {}).get('|'.join(names))
            is_playoff = wk > REG_WEEKS

            sides = []
            for e in (a, b):
                rid = e['roster_id']
                pts = round(e.get('points') or 0.0, 2)
                starters = [str(x) for x in (e.get('starters') or []) if x and x != '0']
                allp = [str(x) for x in (e.get('players') or [])]
                actual = {str(k): (v or 0.0)
                          for k, v in (e.get('players_points') or {}).items()}
                bench = [p for p in allp if p not in set(starters)]

                lineup = []
                for pid in starters:
                    act = round(actual.get(pid, 0.0), 2)
                    pr = proj_pts.get(pid)
                    meta = players.get(pid, {})
                    row = {'pid': pid, 'name': meta.get('name', pid),
                           'pos': meta.get('pos', ''), 'nfl': meta.get('team', ''),
                           'actual': act}
                    if pr is not None:
                        row['proj'] = round(pr, 2)
                        row['delta'] = round(act - pr, 2)
                    lineup.append(row)

                scored = [r for r in lineup if 'delta' in r]
                over = max(scored, key=lambda r: r['delta']) if scored else None
                under = min(scored, key=lambda r: r['delta']) if scored else None
                proj_total = round(sum(r['proj'] for r in scored), 2)

                bench_rows = []
                for pid in bench:
                    meta = players.get(pid, {})
                    bench_rows.append({
                        'pid': pid, 'name': meta.get('name', pid),
                        'pos': meta.get('pos', ''),
                        'actual': round(actual.get(pid, 0.0), 2)})
                bench_rows.sort(key=lambda r: -r['actual'])

                opt_total, _ = optimal_lineup(
                    starters + bench, actual, players, slots)
                swap = best_legal_swap(starters, bench, actual, players, slots)
                if swap:
                    swap['in_name'] = players.get(swap['in_pid'], {}).get('name')
                    swap['out_name'] = players.get(swap['out_pid'], {}).get('name')

                rec = records[rid]
                sides.append({
                    'roster_id': rid,
                    'owner': ROSTER_OWNER[rid],
                    'team': OWNER_TEAM[ROSTER_OWNER[rid]],
                    'points': pts,
                    'proj_total': proj_total,
                    'proj_delta': round(pts - proj_total, 2),
                    # The number to actually quote: this team's miss net of how
                    # far off everyone was that week.
                    'proj_delta_adj': round(pts - proj_total - proj_bias, 2),
                    'beat_median': pts > median,
                    'record_before': f"{rec['w']}-{rec['l']}",
                    'streak_before': (f"{streaks[rid]['kind']}{streaks[rid]['len']}"
                                      if streaks[rid]['kind'] else None),
                    'season_high_so_far': (
                        bool(season_scores[rid]) and pts > max(season_scores[rid])),
                    'season_low_so_far': (
                        bool(season_scores[rid]) and pts < min(season_scores[rid])),
                    'lineup': lineup,
                    'top_overperformer': over,
                    'top_underperformer': under,
                    'zeroes': [r['name'] for r in lineup if r['actual'] == 0],
                    'bench_total': round(sum(r['actual'] for r in bench_rows), 2),
                    'bench_best': bench_rows[0] if bench_rows else None,
                    'optimal_total': opt_total,
                    'left_on_table': round(opt_total - pts, 2),
                    'best_swap': swap,
                    'pos_groups': pos_group_totals(starters, actual, players),
                })

            margin = round(sides[0]['points'] - sides[1]['points'], 2)
            key = f'{wk}|{mid}'
            loser = sides[1]
            bench_decided = bool(
                loser['best_swap'] and loser['best_swap']['gain'] > margin)
            upset = (sides[1]['proj_total'] > sides[0]['proj_total']
                     and sides[0]['proj_total'] > 0)

            ha, hb = sides[0]['roster_id'], sides[1]['roster_id']
            hk = tuple(sorted([ha, hb]))
            prior = h2h.get(hk, {ha: 0, hb: 0})

            rec_out = {
                'week': wk, 'matchup_id': mid,
                'bracket_label': label,
                'is_playoff': is_playoff,
                'gets_commentary': commented(label),
                'rivalry_week': wk in RIVALRY_WEEKS.get(year, []),
                'winner': sides[0]['owner'],
                'loser': sides[1]['owner'],
                'margin': margin,
                'margin_class': ('nailbiter' if margin < NAILBITER
                                 else 'blowout' if margin > BLOWOUT
                                 else 'normal'),
                'combined': round(sides[0]['points'] + sides[1]['points'], 2),
                'week_median': round(median, 2),
                'week_proj_bias': proj_bias,
                'winner_beat_median': sides[0]['beat_median'],
                'loser_beat_median': sides[1]['beat_median'],
                'lucky_win': not sides[0]['beat_median'],
                'unlucky_loss': sides[1]['beat_median'],
                'upset': upset,
                'bench_decided': bench_decided,
                'h2h_before': {sides[0]['owner']: prior.get(ha, 0),
                               sides[1]['owner']: prior.get(hb, 0)},
                'sides': sides,
            }

            if not weeks_filter or wk in weeks_filter:
                if rec_out['gets_commentary']:
                    out['matchups'][key] = rec_out
                    wrote += 1
                else:
                    skipped += 1

            # advance running context. Records follow the site's own
            # convention -- "Total W-L" in the career table is H2H PLUS the
            # median game, because this league plays two games a week. Only
            # weeks 1-14 count toward it (REG_WEEKS rule); bracket games are
            # not part of anyone's record.
            for i, e in enumerate((a, b)):
                rid = e['roster_id']
                won = i == 0
                if wk <= REG_WEEKS:
                    records[rid]['w' if won else 'l'] += 1
                    beat_med = (e.get('points') or 0.0) > median
                    records[rid]['w' if beat_med else 'l'] += 1
                kind = 'W' if won else 'L'
                if streaks[rid]['kind'] == kind:
                    streaks[rid]['len'] += 1
                else:
                    streaks[rid] = {'kind': kind, 'len': 1}
                season_scores[rid].append(round(e.get('points') or 0.0, 2))
            h2h.setdefault(hk, {ha: 0, hb: 0})
            h2h[hk][ha] = h2h[hk].get(ha, 0) + 1

        print(f'  week {wk:>2}: {len(pairs)} matchups, {wrote} written, '
              f'median {median:.2f}')

    with open(out_path, 'w') as f:
        json.dump(out, f, indent=1)
    print(f'\nOK - wrote {out_path}')
    print(f'   {len(out["matchups"])} matchups with facts, '
          f'{skipped} skipped as no-stakes consolation')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', type=int, required=True)
    ap.add_argument('--weeks', default=None,
                    help='comma-separated subset, e.g. 1,17')
    ap.add_argument('--out', default=None)
    ap.add_argument('--cache-dir', default=None,
                    help='where to cache the players dump (default: system temp)')
    args = ap.parse_args()

    weeks = None
    if args.weeks:
        weeks = [int(w) for w in args.weeks.split(',') if w.strip()]

    cache_dir = args.cache_dir or os.path.join(
        os.environ.get('TEMP') or '/tmp', 'tol-facts-cache')
    out_path = args.out or os.path.join(
        cache_dir, f'matchup-facts-{args.year}.json')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    build(args.year, weeks, out_path, cache_dir)


if __name__ == '__main__':
    main()
