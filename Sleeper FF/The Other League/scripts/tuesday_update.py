#!/usr/bin/env python3
"""
tuesday_update.py — The Other League weekly H2H records updater.

Runs every Tuesday after Monday Night Football. Fetches the most recently
completed NFL week's matchup results from the Sleeper API and updates
h2h-records.md with new head-to-head records.

Usage:
  python scripts/tuesday_update.py                # auto-detect current week
  python scripts/tuesday_update.py --week 5       # force a specific week
  python scripts/tuesday_update.py --dry-run      # print output without writing
  python scripts/tuesday_update.py --force        # re-process an already-applied week
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

import requests

# ── CONFIG ─────────────────────────────────────────────────────────────────────

LEAGUE_ID = '1316225642072662016'   # 2026 TOL league on Sleeper
YEAR = 2026
REGULAR_SEASON_WEEKS = list(range(1, 15))  # weeks 1–14 only; 15–17 are playoffs

# Paths relative to TOL folder (script lives in scripts/, TOL root is one level up)
TOL_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H2H_FILE   = os.path.join(TOL_ROOT, 'h2h-records.md')
STATE_FILE = os.path.join(TOL_ROOT, 'scripts', 'bot_state.json')

# roster_id (1–12) → display name — mirrors RM + TEAMS in index.html
ROSTER_NAMES = {
    1:  'Matt Bova',
    2:  'Jake Bogardus',
    3:  'Jared Hayes',
    4:  'Chris Bova',
    5:  'Nick Bova',
    6:  'Erin Jacobs',
    7:  'Jake Blackwell',
    8:  'Chris Merkel',
    9:  'Mitch Blackwell',
    10: 'Nick Merkel',
    11: 'Andrew Bova',
    12: 'Duane Gillenwater',
}

ALL_OWNERS = sorted(ROSTER_NAMES.values())

# Total regular-season games through 2025 (used in file header)
HISTORICAL_GAMES = 252  # 2023 (84) + 2024 (84) + 2025 (84)

# ── SLEEPER API ────────────────────────────────────────────────────────────────

def fetch(url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f'ERROR fetching {url}: {e}')
        sys.exit(1)


def get_current_nfl_week():
    """Ask the Sleeper state API what the current NFL week is."""
    state = fetch('https://api.sleeper.app/v1/state/nfl')
    week        = state.get('week', 0)
    season      = state.get('season')
    season_type = state.get('season_type', 'off')
    print(f'Sleeper state → season={season}, week={week}, type={season_type}')
    if season_type != 'regular':
        print(f"WARNING: Season type is '{season_type}'. Script is intended for regular season use.")
    return week


def fetch_matchups(week):
    """Fetch raw matchup list for a given week from the Sleeper league."""
    url = f'https://api.sleeper.app/v1/league/{LEAGUE_ID}/matchups/{week}'
    data = fetch(url)
    if not data:
        print(f'ERROR: No matchup data returned for week {week}.')
        sys.exit(1)
    return data


def parse_matchups(raw_matchups, week):
    """
    Convert the raw Sleeper matchup list into resolved (winner, loser, w_pts, l_pts) tuples.
    Returns an empty list and exits if no points data is found (games not yet played).
    """
    # Sanity check — if all points are 0/null the week hasn't been played yet
    total_pts = sum((e.get('points') or 0) for e in raw_matchups)
    if total_pts == 0:
        print(f'ERROR: Week {week} has no points data — games may not have been played yet.')
        sys.exit(1)

    # Group entries by matchup_id (each id = one game, exactly 2 teams)
    groups = defaultdict(list)
    for entry in raw_matchups:
        mid = entry.get('matchup_id')
        if mid:
            groups[mid].append(entry)

    results = []
    for mid, pair in sorted(groups.items()):
        if len(pair) != 2:
            print(f'WARNING: matchup_id {mid} has {len(pair)} entries (expected 2). Skipping.')
            continue

        a, b = pair
        a_pts  = a.get('points') or 0
        b_pts  = b.get('points') or 0
        a_name = ROSTER_NAMES.get(a['roster_id'])
        b_name = ROSTER_NAMES.get(b['roster_id'])

        if not a_name or not b_name:
            print(f'WARNING: Unknown roster ID in matchup {mid}. Skipping.')
            continue

        if a_pts == b_pts:
            print(f'TIE: {a_name} vs {b_name} both at {a_pts:.2f} — skipping (should be extremely rare).')
            continue

        if a_pts > b_pts:
            results.append((a_name, b_name, a_pts, b_pts))
        else:
            results.append((b_name, a_name, b_pts, a_pts))

    return results

# ── STATE FILE ─────────────────────────────────────────────────────────────────

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {'applied_weeks': []}


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
        f.write('\n')

# ── H2H RECORDS FILE — PARSE ───────────────────────────────────────────────────

def parse_h2h_file():
    """
    Read h2h-records.md and return a nested dict:
      { owner_name → { opponent_name → [wins, losses] } }
    """
    with open(H2H_FILE, encoding='utf-8') as f:
        content = f.read()

    h2h = {owner: {} for owner in ALL_OWNERS}

    # Split on "### " section headers — sections[0] is the preamble/standings, skip it
    sections = re.split(r'\n###\s+', content)

    for section in sections[1:]:
        lines = section.splitlines()
        if not lines:
            continue

        # First line is "Name — W-L all-time"
        header_match = re.match(r'(.+?)\s+—\s+\d+-\d+\s+all-time', lines[0])
        if not header_match:
            continue
        owner = header_match.group(1).strip()
        if owner not in h2h:
            print(f'WARNING: Unknown owner "{owner}" in h2h-records.md — skipping section.')
            continue

        for line in lines[1:]:
            line = line.strip()
            # Only process data rows (starts with |, not header or separator rows)
            if not line.startswith('|') or line.startswith('|---') or 'Opponent' in line:
                continue
            parts = [p.strip() for p in line.split('|')]
            # parts: ['', opponent, 'W-L', 'result', '']
            if len(parts) < 4:
                continue
            opponent   = parts[1]
            record_str = parts[2]
            if not opponent or '-' not in record_str:
                continue
            if opponent not in ALL_OWNERS:
                continue
            try:
                w, l = map(int, record_str.split('-', 1))
                h2h[owner][opponent] = [w, l]
            except ValueError:
                pass

    return h2h

# ── H2H RECORDS — UPDATE ───────────────────────────────────────────────────────

def apply_results(h2h, results):
    """Apply a list of (winner, loser, ...) matchup results to the h2h dict."""
    for winner, loser, *_ in results:
        # winner's perspective: add a win vs loser
        h2h[winner].setdefault(loser, [0, 0])
        h2h[winner][loser][0] += 1

        # loser's perspective: add a loss vs winner
        h2h[loser].setdefault(winner, [0, 0])
        h2h[loser][winner][1] += 1

# ── H2H RECORDS FILE — GENERATE ───────────────────────────────────────────────

def total_record(h2h, owner):
    """Return (wins, losses) totals for an owner across all opponents."""
    w = sum(r[0] for r in h2h[owner].values())
    l = sum(r[1] for r in h2h[owner].values())
    return w, l


def result_label(wins, losses):
    if wins > losses: return 'W'
    if losses > wins: return 'L'
    return '—'


def generate_h2h_md(h2h, applied_weeks):
    """Regenerate the complete h2h-records.md content from the h2h data structure."""

    max_week    = max(applied_weeks) if applied_weeks else 0
    new_games   = len(applied_weeks) * 6   # 6 games per week
    total_games = HISTORICAL_GAMES + new_games

    if max_week > 0:
        week_note = f', {YEAR} (through Wk {max_week})'
    else:
        week_note = ''

    lines = [
        '# All-Time H2H Records — The Other League',
        f'*Regular Season Weeks 1–14 · 2023, 2024, 2025{week_note} · {total_games} total games*',
        '*Note: Roster 11 was managed by CCJ (Chris Jacobs) for 2023–2025. Andrew Bova took over that roster in 2026 and inherited these records.*',
        '',
        '---',
        '',
        '## Overall Standings',
        '',
        '| Rank | Owner | W-L | Notes |',
        '|------|-------|-----|-------|',
    ]

    # Sort by wins desc, then losses asc for tiebreaker
    standings = sorted(ALL_OWNERS, key=lambda o: (-total_record(h2h, o)[0], total_record(h2h, o)[1]))

    # Standard competition ranking (1, 2, 2, 2, 5, ...)
    display_rank = 1
    for i, owner in enumerate(standings):
        w, l = total_record(h2h, owner)
        if i > 0:
            pw, pl = total_record(h2h, standings[i - 1])
            if (w, l) != (pw, pl):
                display_rank = i + 1   # skip ranks consumed by the tie block
        lines.append(f'| {display_rank} | {owner} | {w}-{l} | |')

    lines += ['', '---', '']

    # Per-owner sections
    for owner in standings:
        w, l = total_record(h2h, owner)
        lines.append(f'### {owner} — {w}-{l} all-time')
        lines.append('| Opponent | Record | Result |')
        lines.append('|----------|--------|--------|')

        # Sort opponents by total games played desc, then alphabetically
        opps = sorted(
            h2h[owner].items(),
            key=lambda kv: (-(kv[1][0] + kv[1][1]), kv[0])
        )
        for opp, (ow, ol) in opps:
            lines.append(f'| {opp} | {ow}-{ol} | {result_label(ow, ol)} |')

        lines += ['', '---', '']

    return '\n'.join(lines)

# ── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Update h2h-records.md with the latest completed NFL week results.'
    )
    parser.add_argument('--week',    type=int, help='Force a specific NFL week number')
    parser.add_argument('--dry-run', action='store_true', help='Print output without writing files')
    parser.add_argument('--force',   action='store_true', help='Re-process even if week already applied')
    args = parser.parse_args()

    print('=' * 60)
    print('  The Other League — Tuesday Update Script')
    print('=' * 60)

    # 1. Determine which week to process
    if args.week:
        week = args.week
        print(f'Forced week: {week}')
    else:
        week = get_current_nfl_week()
        print(f'Auto-detected week: {week}')

    if week not in REGULAR_SEASON_WEEKS:
        print(f'\nWeek {week} is outside the regular season (weeks 1–14). Nothing to update.')
        if week >= 14:
            print('\n⚠  REMINDER: Regular season complete.')
            print('   Once 2026 playoff brackets are set, update PLAYOFF_BRACKET_INFO[2026]')
            print('   in index.html (look for the PLAYOFF_BRACKET_INFO constant).')
        sys.exit(0)

    # 2. Check if already applied
    state   = load_state()
    applied = state.get('applied_weeks', [])

    if week in applied and not args.force:
        print(f'\nWeek {week} has already been applied. Use --force to re-process.')
        sys.exit(0)

    # 3. Fetch and parse matchup data
    print(f'\nFetching Sleeper matchups for week {week}...')
    raw_matchups = fetch_matchups(week)
    results      = parse_matchups(raw_matchups, week)

    if not results:
        print('ERROR: No valid matchup results found.')
        sys.exit(1)

    print(f'\nWeek {week} results ({len(results)} games):')
    for winner, loser, w_pts, l_pts in results:
        print(f'  {winner:<20} def.  {loser:<20}  ({w_pts:.2f} – {l_pts:.2f})')

    if week == 14:
        print('\n⚠  REMINDER: Week 14 complete — regular season over.')
        print('   Once 2026 playoff brackets are set, update PLAYOFF_BRACKET_INFO[2026] in index.html.')

    # 4. Parse current h2h-records.md
    print(f'\nParsing current {H2H_FILE}...')
    if not os.path.exists(H2H_FILE):
        print(f'ERROR: {H2H_FILE} not found.')
        sys.exit(1)
    h2h = parse_h2h_file()

    # 5. Apply new results
    apply_results(h2h, results)

    # 6. Generate updated content
    new_applied = sorted(set(applied + [week]))
    new_content = generate_h2h_md(h2h, new_applied)

    if args.dry_run:
        print('\n--- DRY RUN: first 60 lines of updated h2h-records.md ---')
        for line in new_content.splitlines()[:60]:
            print(line)
        print('...')
        print('\nDry run complete — no files written.')
        return

    # 7. Write files
    with open(H2H_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f'\n✓ Updated {H2H_FILE}')

    state['applied_weeks'] = new_applied
    save_state(state)
    print(f'✓ Updated bot_state.json  (applied weeks so far: {new_applied})')

    print(f'\n✅  Week {week} processing complete!')


if __name__ == '__main__':
    main()
