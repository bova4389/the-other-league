#!/usr/bin/env python3
"""
build_season_facts.py -- assemble a SEASON-level fact sheet for a completed
season, to write the Careers-tab season recap from.

Companion to build_matchup_facts.py, which works one matchup at a time. This
one answers the season-shaped questions a recap needs: who led wire to wire,
who the median game rescued or robbed, which week broke the scoreboard, who
carried a roster, and how the bracket actually played out.

Same rules as the rest of the site:
  - Regular season is weeks 1-14. Weeks 15-17 are the brackets and are
    reported separately, never folded into a record.
  - A "win" in this league is two games a week: the opponent, and the league
    median. Records are reported as H2H, median, and the total of both.
  - An unplayed week comes back from Sleeper as twelve scored-zero rows.
    weekWasPlayed() guards against booking those as losses; ported here.

Output is an offline working document -- NOT a site asset, never committed.

Usage:
  python scripts/build_season_facts.py --year 2024 --out /tmp/season-2024.json
"""

import argparse
import json
import os
import statistics

import requests

API = 'https://api.sleeper.app/v1'
CURRENT_LID = '1316225642072662016'
REG_WEEKS = 14

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOL_ROOT = os.path.dirname(_SCRIPT_DIR)


def fetch(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def find_league_id(year):
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
        out[pid] = {'name': name or pid, 'pos': p.get('position') or '',
                    'team': p.get('team') or 'FA'}
    os.makedirs(cache_dir, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(out, f, separators=(',', ':'))
    return out


def week_was_played(week_data):
    """Ported from index.html. An unplayed week is 12 paired rows of 0.0."""
    if not week_data:
        return False
    return any((e.get('points') or 0) > 0 for e in week_data)


def week_median(week_data):
    vals = sorted((e.get('points') or 0.0) for e in week_data
                  if e.get('matchup_id') and e.get('points') is not None)
    if not vals:
        return None
    n = len(vals)
    return (vals[n // 2 - 1] + vals[n // 2]) / 2 if n % 2 == 0 else vals[n // 2]


def build(year, out_path, cache_dir):
    lid, league = find_league_id(year)
    print(f'{year} league: {lid}')
    players = load_players(cache_dir)

    users = {u['user_id']: u for u in fetch(f'{API}/league/{lid}/users')}
    rosters = fetch(f'{API}/league/{lid}/rosters')

    # roster_id -> owner, resolved PER YEAR off the API rather than assuming
    # this year's roster ids match the current league's.
    owner_of = {}
    team_of = {}
    for r in rosters:
        uid = r.get('owner_id')
        u = users.get(uid, {})
        owner_of[r['roster_id']] = (u.get('display_name') or uid
                                    or f"roster{r['roster_id']}")
        md = u.get('metadata') or {}
        team_of[r['roster_id']] = md.get('team_name') or owner_of[r['roster_id']]
    print('  roster map: ' + ', '.join(
        f'{k}={v}' for k, v in sorted(owner_of.items())))

    weekly = {}
    for wk in range(1, 18):
        data = fetch(f'{API}/league/{lid}/matchups/{wk}')
        if week_was_played(data):
            weekly[wk] = data

    per = {rid: {'owner': owner_of[rid], 'team': team_of[rid],
                 'scores': {}, 'h2h_w': 0, 'h2h_l': 0, 'h2h_t': 0,
                 'med_w': 0, 'med_l': 0, 'pf': 0.0, 'pa': 0.0,
                 'crowns': 0, 'duds': 0, 'lucky_w': 0, 'unlucky_l': 0,
                 'results': []} for rid in owner_of}

    season = {'year': year, 'league_id': lid, 'weeks': {}, 'bracket_weeks': {}}

    for wk in sorted(weekly):
        data = weekly[wk]
        med = week_median(data)
        by_mid = {}
        for e in data:
            if e.get('matchup_id') is None:
                continue
            by_mid.setdefault(e['matchup_id'], []).append(e)
        scored = [(e['roster_id'], e.get('points') or 0.0) for e in data
                  if e.get('matchup_id') is not None]
        scored.sort(key=lambda x: -x[1])
        wk_rec = {'week': wk, 'median': round(med, 2) if med else None,
                  'high': {'owner': owner_of[scored[0][0]],
                           'pts': round(scored[0][1], 2)},
                  'low': {'owner': owner_of[scored[-1][0]],
                          'pts': round(scored[-1][1], 2)},
                  'games': []}
        for mid, pair in by_mid.items():
            if len(pair) != 2:
                continue
            a, b = pair
            ap, bp = a.get('points') or 0.0, b.get('points') or 0.0
            hi, lo = (a, b) if ap >= bp else (b, a)
            wk_rec['games'].append({
                'matchup_id': mid,
                'winner': owner_of[hi['roster_id']],
                'loser': owner_of[lo['roster_id']],
                'w_pts': round(max(ap, bp), 2), 'l_pts': round(min(ap, bp), 2),
                'margin': round(abs(ap - bp), 2),
                'total': round(ap + bp, 2),
            })
        if wk <= REG_WEEKS:
            season['weeks'][wk] = wk_rec
        else:
            season['bracket_weeks'][wk] = wk_rec
            continue

        # regular-season accumulation
        for rid, pts in scored:
            per[rid]['scores'][wk] = round(pts, 2)
        per[scored[0][0]]['crowns'] += 1
        per[scored[-1][0]]['duds'] += 1
        for mid, pair in by_mid.items():
            if len(pair) != 2:
                continue
            a, b = pair
            ap, bp = a.get('points') or 0.0, b.get('points') or 0.0
            ra, rb = a['roster_id'], b['roster_id']
            per[ra]['pf'] += ap
            per[ra]['pa'] += bp
            per[rb]['pf'] += bp
            per[rb]['pa'] += ap
            if ap > bp:
                per[ra]['h2h_w'] += 1
                per[rb]['h2h_l'] += 1
                res_a, res_b = 'W', 'L'
            elif bp > ap:
                per[rb]['h2h_w'] += 1
                per[ra]['h2h_l'] += 1
                res_a, res_b = 'L', 'W'
            else:
                per[ra]['h2h_t'] += 1
                per[rb]['h2h_t'] += 1
                res_a = res_b = 'T'
            per[ra]['results'].append({'week': wk, 'res': res_a,
                                       'pts': round(ap, 2),
                                       'opp': owner_of[rb],
                                       'opp_pts': round(bp, 2)})
            per[rb]['results'].append({'week': wk, 'res': res_b,
                                       'pts': round(bp, 2),
                                       'opp': owner_of[ra],
                                       'opp_pts': round(ap, 2)})
            # luck: won with a below-median score / lost with an above-median one
            if med is not None:
                if ap > bp and ap <= med:
                    per[ra]['lucky_w'] += 1
                if bp > ap and bp <= med:
                    per[rb]['lucky_w'] += 1
                if ap < bp and ap > med:
                    per[ra]['unlucky_l'] += 1
                if bp < ap and bp > med:
                    per[rb]['unlucky_l'] += 1
        if med is not None:
            for rid, pts in scored:
                if pts > med:
                    per[rid]['med_w'] += 1
                else:
                    per[rid]['med_l'] += 1

    # season-long per-owner rollups
    table = []
    for rid, p in per.items():
        sc = list(p['scores'].values())
        if not sc:
            continue
        streak_w = streak_l = cur_w = cur_l = 0
        for r in sorted(p['results'], key=lambda x: x['week']):
            if r['res'] == 'W':
                cur_w += 1
                cur_l = 0
            elif r['res'] == 'L':
                cur_l += 1
                cur_w = 0
            streak_w = max(streak_w, cur_w)
            streak_l = max(streak_l, cur_l)
        tie = f"-{p['h2h_t']}" if p['h2h_t'] else ''
        table.append({
            'roster_id': rid, 'owner': p['owner'], 'team': p['team'],
            'h2h': f"{p['h2h_w']}-{p['h2h_l']}{tie}",
            'median': f"{p['med_w']}-{p['med_l']}",
            'total_w': p['h2h_w'] + p['med_w'],
            'total_l': p['h2h_l'] + p['med_l'],
            'pf': round(p['pf'], 2), 'pa': round(p['pa'], 2),
            'ppg': round(p['pf'] / len(sc), 2),
            'high': round(max(sc), 2), 'low': round(min(sc), 2),
            'stdev': round(statistics.pstdev(sc), 2) if len(sc) > 1 else 0,
            'crowns': p['crowns'], 'duds': p['duds'],
            'lucky_w': p['lucky_w'], 'unlucky_l': p['unlucky_l'],
            'longest_win_streak': streak_w, 'longest_lose_streak': streak_l,
            'week_scores': p['scores'],
            'game_log': sorted(p['results'], key=lambda x: x['week']),
        })
    table.sort(key=lambda r: (-(r['total_w']), -r['pf']))
    for i, r in enumerate(table):
        r['reg_seed'] = i + 1
    season['standings'] = table

    # season extremes, regular season only
    all_games = [dict(g, week=wk) for wk, w in season['weeks'].items()
                 for g in w['games']]
    week_rows = [{'owner': r['owner'], 'pts': v, 'week': w}
                 for r in table for w, v in r['week_scores'].items()]
    season['extremes'] = {
        'highest_week': sorted(week_rows, key=lambda x: -x['pts'])[:6],
        'lowest_week': sorted(week_rows, key=lambda x: x['pts'])[:6],
        'biggest_blowout': sorted(all_games, key=lambda g: -g['margin'])[:5],
        'closest': sorted(all_games, key=lambda g: g['margin'])[:5],
        'highest_total': sorted(all_games, key=lambda g: -g['total'])[:3],
        'lowest_total': sorted(all_games, key=lambda g: g['total'])[:3],
    }

    # who carried whom: season starter points by player, per roster
    carry = {rid: {} for rid in owner_of}
    single = []
    for wk, data in weekly.items():
        if wk > REG_WEEKS:
            continue
        for e in data:
            rid = e['roster_id']
            sp = e.get('starters_points') or []
            st = e.get('starters') or []
            for pid, pts in zip(st, sp):
                if not pid or pid == '0':
                    continue
                carry[rid][pid] = carry[rid].get(pid, 0.0) + (pts or 0.0)
                single.append({'owner': owner_of[rid], 'week': wk,
                               'player': players.get(pid, {}).get('name', pid),
                               'pos': players.get(pid, {}).get('pos', ''),
                               'pts': round(pts or 0.0, 2)})
    season['top_starters'] = {}
    for rid, m in carry.items():
        top = sorted(m.items(), key=lambda kv: -kv[1])[:6]
        season['top_starters'][owner_of[rid]] = [
            {'player': players.get(pid, {}).get('name', pid),
             'pos': players.get(pid, {}).get('pos', ''),
             'pts': round(v, 2)} for pid, v in top]
    season['best_single_player_weeks'] = sorted(
        single, key=lambda x: -x['pts'])[:20]
    league_wide = []
    for rid, m in carry.items():
        for pid, v in m.items():
            league_wide.append({'owner': owner_of[rid],
                                'player': players.get(pid, {}).get('name', pid),
                                'pos': players.get(pid, {}).get('pos', ''),
                                'pts': round(v, 2)})
    season['top_starters_league'] = sorted(
        league_wide, key=lambda x: -x['pts'])[:25]

    # transactions
    tx = {'trades': [], 'counts': {}}
    for wk in range(1, 19):
        try:
            data = fetch(f'{API}/league/{lid}/transactions/{wk}')
        except Exception:
            continue
        for t in data or []:
            if t.get('status') != 'complete':
                continue
            typ = t.get('type')
            for rid in t.get('roster_ids') or []:
                own = owner_of.get(rid)
                if not own:
                    continue
                tx['counts'].setdefault(own, {'trade': 0, 'waiver': 0,
                                              'free_agent': 0})
                if typ in tx['counts'][own]:
                    tx['counts'][own][typ] += 1
            if typ == 'trade':
                adds = t.get('adds') or {}
                tx['trades'].append({
                    'week': wk,
                    'owners': [owner_of.get(r) for r in (t.get('roster_ids') or [])],
                    'adds': [{'player': players.get(pid, {}).get('name', pid),
                              'pos': players.get(pid, {}).get('pos', ''),
                              'to': owner_of.get(rid)}
                             for pid, rid in adds.items()],
                    'picks': [{'season': p.get('season'), 'round': p.get('round'),
                               'from': owner_of.get(p.get('previous_owner_id')),
                               'to': owner_of.get(p.get('owner_id'))}
                              for p in (t.get('draft_picks') or [])],
                })
    season['transactions'] = tx

    # rookie draft for the season
    try:
        drafts = fetch(f'{API}/league/{lid}/drafts')
        if drafts:
            did = drafts[0]['draft_id']
            picks = fetch(f'{API}/draft/{did}/picks')
            season['draft'] = [
                {'pick': p.get('pick_no'), 'round': p.get('round'),
                 'player': players.get(str(p.get('player_id')), {}).get(
                     'name', p.get('player_id')),
                 'pos': players.get(str(p.get('player_id')), {}).get('pos', ''),
                 'by': owner_of.get(p.get('roster_id'))}
                for p in picks][:36]
    except Exception as e:
        season['draft'] = f'unavailable: {e}'

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(season, f, indent=1)
    print(f'wrote {out_path}')

    # console summary
    print(f'\n{year} REGULAR SEASON (wks 1-{REG_WEEKS})')
    hdr = (f"{'seed':>4} {'owner':<20} {'total':>7} {'h2h':>7} {'med':>7} "
           f"{'PF':>8} {'PA':>8} {'ppg':>7} {'hi':>7} {'lo':>7} "
           f"{'crn':>4} {'dud':>4} {'lky':>4} {'unl':>4}")
    print(hdr)
    for r in table:
        rec = f"{r['total_w']}-{r['total_l']}"
        print(f"{r['reg_seed']:>4} {r['owner']:<20} {rec:>7} "
              f"{r['h2h']:>7} {r['median']:>7} {r['pf']:>8.1f} {r['pa']:>8.1f} "
              f"{r['ppg']:>7.1f} {r['high']:>7.1f} {r['low']:>7.1f} "
              f"{r['crowns']:>4} {r['duds']:>4} {r['lucky_w']:>4} "
              f"{r['unlucky_l']:>4}")
    print('\nBRACKET')
    for wk in sorted(season['bracket_weeks']):
        print(f"  W{wk}")
        for g in season['bracket_weeks'][wk]['games']:
            print(f"    {g['winner']} {g['w_pts']} def {g['loser']} {g['l_pts']}"
                  f"  (by {g['margin']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--year', type=int, required=True)
    ap.add_argument('--out')
    ap.add_argument('--cache-dir', default=os.path.join(_SCRIPT_DIR, '.cache'))
    a = ap.parse_args()
    out = a.out or os.path.join(_SCRIPT_DIR, f'season-facts-{a.year}.json')
    build(a.year, out, a.cache_dir)


if __name__ == '__main__':
    main()
