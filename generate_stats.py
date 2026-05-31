"""
generate_stats.py — one-time script to build stats-history.json
Fetches 2023-2025 season + weekly stats from the Sleeper API for all
historically-rostered players. Run from the repo root:
  python generate_stats.py
Output: stats-history.json (commit this to the repo)
"""
import json
import time
import urllib.request
import urllib.error

BASE = 'https://api.sleeper.app/v1'
LID_2026 = '1316225642072662016'

STAT_KEYS = [
    'gp',
    'pass_att','pass_cmp','pass_yd','pass_td','pass_int','pass_2pt','pass_td_40p',
    'rush_att','rush_yd','rush_td','rush_2pt','rush_40p',
    'rec','rec_yd','rec_td','rec_2pt',
    'rec_0_4','rec_5_9','rec_10_19','rec_20_29','rec_30_39','rec_40p',
    'kr_yd','pr_yd','fum_lost',
    'bonus_pass_yd_400','bonus_rush_yd_200','bonus_rec_yd_200',
]


def fetch(path, retries=3):
    url = BASE + path
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            if attempt < retries - 1:
                print(f'  retry ({attempt+1})...', end=' ')
                time.sleep(2)
            else:
                raise RuntimeError(f'Failed to fetch {url}: {e}')


def get_league_chain():
    ids = {}
    lid = LID_2026
    year = 2026
    while lid and year >= 2023:
        info = fetch(f'/league/{lid}')
        ids[year] = lid
        lid = info.get('previous_league_id')
        year -= 1
    return ids


def get_roster_players(lid):
    rosters = fetch(f'/league/{lid}/rosters')
    players = set()
    for r in rosters:
        for pid in (r.get('players') or []):
            players.add(str(pid))
    return players


def fetch_week_stats(year, week, player_ids):
    data = fetch(f'/stats/nfl/regular/{year}/{week}')
    result = {}
    for pid, stats in data.items():
        if str(pid) not in player_ids:
            continue
        filtered = {k: stats[k] for k in STAT_KEYS if stats.get(k)}
        if filtered:
            result[str(pid)] = filtered
    return result


def main():
    print('Fetching league ID chain...')
    league_ids = get_league_chain()
    print(f'  League IDs: {league_ids}')

    output = {'generated': '2026-05-30'}

    for year in [2025, 2024, 2023]:
        lid = league_ids.get(year)
        if not lid:
            print(f'\nSkipping {year} — no league ID found')
            continue
        print(f'\n=== {year} (league {lid}) ===')

        print('  Fetching roster player list...')
        player_ids = get_roster_players(lid)
        print(f'  {len(player_ids)} players found')

        season_agg = {}
        weeks_data = {}

        for week in range(1, 18):
            print(f'  Week {week:2d}... ', end='', flush=True)
            try:
                week_stats = fetch_week_stats(year, week, player_ids)
                weeks_data[str(week)] = week_stats
                for pid, stats in week_stats.items():
                    if pid not in season_agg:
                        season_agg[pid] = {}
                    for k, v in stats.items():
                        season_agg[pid][k] = round(season_agg[pid].get(k, 0) + v, 4)
                print(f'{len(week_stats)} players')
                time.sleep(0.35)
            except Exception as e:
                print(f'ERROR — {e}')
                weeks_data[str(week)] = {}

        output[str(year)] = {'season': season_agg, 'weeks': weeks_data}

    out_path = 'stats-history.json'
    print(f'\nWriting {out_path}...')
    raw = json.dumps(output, separators=(',', ':'))
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(raw)
    print(f'Done — {len(raw)/1024:.1f} KB')


if __name__ == '__main__':
    main()
