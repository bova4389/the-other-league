#!/usr/bin/env python3
"""
pull_kings_justice.py -- full-history data pull for the King's Justice
Sleeper league (a "chopped" / elimination league).

WHAT THIS DOES, IN PLAIN ENGLISH
--------------------------------
1. Starts at the current season's league on Sleeper and walks BACKWARD through
   `previous_league_id` to find every earlier season of the same league.
2. For each season it downloads: league settings, owners, rosters, draft picks,
   every week's scores, and every week's transactions (waivers/trades/adds).
3. Downloads Sleeper's big NFL player dictionary ONCE and caches it, so that
   every file it writes has real player names instead of numeric IDs.
4. Rebuilds the elimination history. Sleeper has no "eliminated" field, so we
   work it out: each week the lowest-scoring team that is still alive gets
   chopped, and the highest-scoring team that is still alive wins the $25.
   We then cross-check each elimination against the transaction log, because a
   chopped team's whole roster gets auto-dropped to waivers.
5. Writes clean JSON + CSV under kings_justice_data/, one folder per season.
6. Prints (and saves) a plain-English report at the end.

SAFE TO RE-RUN. Every API response is cached under scripts/.cache/. On a re-run
we only re-fetch things that could still change (the current season, and weeks
at or after the current NFL week). Finished seasons are read straight from the
cache, so a weekly in-season run costs a handful of calls instead of hundreds.

USAGE
-----
  python pull_kings_justice.py                    # normal run (use this weekly)
  python pull_kings_justice.py --refresh-all      # ignore cache, re-pull everything
  python pull_kings_justice.py --refresh-players  # just re-pull the player list
  python pull_kings_justice.py --out /some/dir    # write somewhere else

Needs one non-standard package:  pip install requests
"""

import argparse
import csv
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

# -- CONFIG -------------------------------------------------------------------

API = 'https://api.sleeper.app/v1'

# The current season's King's Justice league on Sleeper. When a new season
# starts, Sleeper makes a NEW league id -- put the new one here and the script
# will find every older season automatically via previous_league_id.
CURRENT_LEAGUE_ID = '1383926066564837376'

# Who "I" am, so the report can point out my own team.
MY_USERNAME = 'avobttam'

# Sleeper allows roughly 1000 calls/minute. We deliberately stay far below that
# (about 90/min) to be a good citizen -- this is a free, public, unauthenticated
# API and there is no hurry.
CALLS_PER_MINUTE = 90
MIN_SECONDS_BETWEEN_CALLS = 60.0 / CALLS_PER_MINUTE

# Sleeper weeks. The NFL regular season is 18 weeks; this league finishes well
# before that, but we sweep the full range and simply skip weeks with no data.
ALL_WEEKS = list(range(1, 19))

# How stale the cached player dictionary may get before we re-download it.
PLAYERS_CACHE_MAX_AGE_DAYS = 7

# When validating an elimination against the transaction log, what share of the
# chopped roster must show up as drops before we call it confirmed.
DROP_VALIDATION_THRESHOLD = 0.50

# Paths. The script lives in <project>/scripts/, so the project root is one up.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CACHE_DIR = os.path.join(SCRIPT_DIR, '.cache')
DEFAULT_OUT_DIR = os.path.join(PROJECT_ROOT, 'kings_justice_data')


# -- SMALL HELPERS ------------------------------------------------------------

def log(msg):
    """Print a progress line immediately (so a long run does not look frozen)."""
    print(msg, flush=True)


def write_json(path, data):
    """Save data as pretty-printed JSON, creating parent folders as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def read_json(path):
    """Load JSON from disk, or return None if the file is missing/corrupt."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (IOError, OSError, ValueError):
        return None


def epoch_ms_to_iso(ms):
    """Turn Sleeper's millisecond timestamps into a readable UTC string."""
    if not ms:
        return None
    try:
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat()
    except (ValueError, OverflowError, OSError):
        return None


# -- THE API CLIENT -----------------------------------------------------------

class Sleeper:
    """
    A polite, cached wrapper around Sleeper's public read-only API.

    Two jobs:
      - Throttle. We never fire calls faster than CALLS_PER_MINUTE.
      - Cache. Every response is written to scripts/.cache/ as JSON. On a later
        run we reuse the cached copy unless the caller says the data might have
        changed. This is what makes weekly re-runs cheap.
    """

    def __init__(self, refresh_all=False):
        self.refresh_all = refresh_all
        self.session = requests.Session()
        self.last_call_at = 0.0
        self.calls_made = 0
        self.cache_hits = 0
        self.errors = []

    def _throttle(self):
        """Sleep just long enough to stay under our self-imposed rate limit."""
        gap = time.time() - self.last_call_at
        if gap < MIN_SECONDS_BETWEEN_CALLS:
            time.sleep(MIN_SECONDS_BETWEEN_CALLS - gap)
        self.last_call_at = time.time()

    def get(self, path, cache_key=None, allow_cache=True):
        """
        Fetch <API>/<path>.

        cache_key   -- file name under .cache/ to store the answer in. If None,
                       the response is not cached at all.
        allow_cache -- set False for data that may still be changing (the live
                       week, the current season's rosters) so we always re-fetch.

        Returns the decoded JSON, or None when Sleeper has nothing (a 404, or a
        literal null body -- both are normal for weeks that never happened).
        """
        cache_path = os.path.join(CACHE_DIR, cache_key) if cache_key else None
        use_cache = (cache_path and allow_cache and not self.refresh_all
                     and os.path.exists(cache_path))
        if use_cache:
            cached = read_json(cache_path)
            if cached is not None:
                self.cache_hits += 1
                # We store misses as the string "__NULL__" so an empty week is
                # remembered too, instead of being re-requested every run.
                return None if cached == '__NULL__' else cached

        url = '{0}/{1}'.format(API, path.lstrip('/'))

        # Try a few times: transient network blips and Sleeper's occasional 429
        # are worth a retry, but a 404 is a real answer and we stop immediately.
        data = None
        for attempt in range(4):
            self._throttle()
            try:
                resp = self.session.get(url, timeout=30)
                self.calls_made += 1
                if resp.status_code == 404:
                    data = None
                    break
                if resp.status_code == 429:
                    # Rate limited. Back off progressively and try again.
                    time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                body = resp.text.strip()
                data = json.loads(body) if body and body != 'null' else None
                break
            except (requests.RequestException, ValueError) as exc:
                if attempt == 3:
                    self.errors.append('{0} -> {1}'.format(url, exc))
                    log('  ! giving up on {0}: {1}'.format(url, exc))
                    return None
                time.sleep(2 ** attempt)

        if cache_path:
            write_json(cache_path, '__NULL__' if data is None else data)
        return data


# -- STEP 0: WHAT WEEK IS IT? -------------------------------------------------

def get_nfl_state(api):
    """
    Ask Sleeper what the NFL is currently doing. We use this to decide which
    weeks are finished (safe to cache forever) and which are still in flux.
    """
    state = api.get('state/nfl', cache_key='state_nfl.json', allow_cache=False) or {}
    return {
        'season': str(state.get('season') or ''),
        'week': int(state.get('week') or 0),
        'season_type': state.get('season_type'),
        'display_week': int(state.get('display_week') or 0),
    }


# -- STEP 1: FIND EVERY SEASON OF THIS LEAGUE ---------------------------------

def discover_league_chain(api, start_league_id):
    """
    Walk backward through previous_league_id to collect every season.

    Sleeper creates a brand new league id each year and links it to last year's
    via `previous_league_id`. Following that chain from the current season gives
    us the league's whole history.

    Returns a list of dicts, NEWEST season first.
    """
    chain = []
    seen = set()          # guards against a corrupt self-referencing chain
    league_id = start_league_id

    while league_id and league_id not in seen:
        seen.add(league_id)
        # Settings of a finished season never change, but this is one cheap call
        # per season, so we always take the live copy to catch mid-season edits.
        league = api.get('league/{0}'.format(league_id),
                         cache_key='league_{0}.json'.format(league_id),
                         allow_cache=False)
        if not league:
            log('  ! league {0} returned nothing -- stopping the walk'.format(league_id))
            break

        chain.append({
            'season': str(league.get('season')),
            'league_id': league_id,
            'name': league.get('name'),
            'status': league.get('status'),
            'previous_league_id': league.get('previous_league_id'),
            '_league': league,
        })
        log('  found season {0}: {1} ({2}) [{3}]'.format(
            league.get('season'), league.get('name'), league_id, league.get('status')))
        league_id = league.get('previous_league_id')

    return chain


# -- STEP 2: THE PLAYER DICTIONARY --------------------------------------------

def load_players(api, out_dir, force_refresh=False):
    """
    Get Sleeper's master NFL player list and trim it down to what we need.

    The raw feed is ~5 MB of every player Sleeper has ever known. We only want
    name, position and team, so we shrink it and save that. Sleeper explicitly
    asks callers not to hammer this endpoint, so we keep our copy for a week.
    """
    out_path = os.path.join(out_dir, 'players_lookup.json')

    if not force_refresh and os.path.exists(out_path):
        age_days = (time.time() - os.path.getmtime(out_path)) / 86400.0
        if age_days < PLAYERS_CACHE_MAX_AGE_DAYS:
            cached = read_json(out_path)
            if cached:
                log('  using cached player list ({0} players, {1:.1f} days old)'.format(
                    len(cached), age_days))
                return cached

    log('  downloading the full NFL player list (~5 MB, this takes a moment)...')
    raw = api.get('players/nfl', cache_key=None, allow_cache=False)
    if not raw:
        # If the download failed, fall back to whatever we already had rather
        # than losing every player name in the output.
        stale = read_json(out_path)
        if stale:
            log('  ! download failed -- falling back to the older cached list')
            return stale
        log('  ! could not load the player list; files will show raw IDs')
        return {}

    lookup = {}
    for pid, p in raw.items():
        if not isinstance(p, dict):
            continue
        full = p.get('full_name')
        if not full:
            # Team defenses (and a few oddities) have no full_name.
            first, last = p.get('first_name') or '', p.get('last_name') or ''
            full = (first + ' ' + last).strip() or pid
        lookup[pid] = {
            'full_name': full,
            'position': p.get('position'),
            'team': p.get('team'),
        }

    write_json(out_path, lookup)
    log('  saved {0} players to players_lookup.json'.format(len(lookup)))
    return lookup


def player_brief(players, pid):
    """A small {id, name, position, team} block to embed in output files."""
    rec = players.get(str(pid)) or {}
    return {
        'player_id': str(pid),
        'name': rec.get('full_name') or 'UNKNOWN ({0})'.format(pid),
        'position': rec.get('position'),
        'team': rec.get('team'),
    }


# -- STEP 3: OWNERS AND ROSTERS -----------------------------------------------

def build_owner_index(users, rosters):
    """
    Work out who owns which roster, and produce friendly labels.

    Sleeper keeps three different names for a person and any of them can be
    blank, so we settle on one "team_label" per roster and use it everywhere:
    the team name they set, else their display name, else their username.
    """
    users_by_id = {u.get('user_id'): u for u in (users or [])}

    owners = []
    for u in (users or []):
        meta = u.get('metadata') or {}
        owners.append({
            'user_id': u.get('user_id'),
            'username': u.get('display_name'),   # Sleeper's login handle
            'display_name': u.get('display_name'),
            'team_name': meta.get('team_name'),
            'avatar': u.get('avatar'),
            'is_commissioner': bool(u.get('is_owner')),
        })

    roster_to_owner = {}
    for r in (rosters or []):
        rid = r.get('roster_id')
        owner_id = r.get('owner_id')
        u = users_by_id.get(owner_id) or {}
        meta = u.get('metadata') or {}
        label = (meta.get('team_name') or u.get('display_name')
                 or 'Roster {0}'.format(rid))
        roster_to_owner[rid] = {
            'roster_id': rid,
            'owner_id': owner_id,
            'username': u.get('display_name'),
            'display_name': u.get('display_name'),
            'team_name': meta.get('team_name'),
            'team_label': label,
            # co_owners matter in leagues where two people share a team.
            'co_owners': r.get('co_owners') or [],
        }

    return owners, roster_to_owner


def label_for(roster_to_owner, rid):
    """Friendly team label for a roster id (used in every output file)."""
    rec = roster_to_owner.get(rid)
    return rec['team_label'] if rec else 'Roster {0}'.format(rid)


# -- STEP 4: PULL ONE SEASON --------------------------------------------------

def week_is_settled(season, week, nfl_state):
    """
    Can we trust the cached copy of this week forever?

    Yes if the season is already over, or if the week finished before the
    current NFL week. Anything at or after the live week may still change
    (stat corrections, late waivers), so we always re-fetch those.
    """
    if not nfl_state.get('season'):
        return False                              # unknown state -> take no chances
    if str(season) < str(nfl_state['season']):
        return True                               # a past season is frozen
    if str(season) > str(nfl_state['season']):
        return False                              # a future season has no data yet
    # Same season: a week is settled once the NFL has moved past it.
    return week < max(nfl_state.get('week', 0), nfl_state.get('display_week', 0))


def pull_season(api, season_info, players, nfl_state):
    """
    Download everything for a single season and return it as one dict.

    Nothing is written to disk here -- that happens later, after the
    elimination reconstruction has had a chance to add its own findings.
    """
    league_id = season_info['league_id']
    season = season_info['season']
    league = season_info['_league']
    log('\n=== Season {0} (league {1}) ==='.format(season, league_id))

    # -- owners and rosters ---------------------------------------------------
    # Both can change during a season (someone renames their team, a roster is
    # traded), so for the live season we always take a fresh copy.
    live = (str(season) == str(nfl_state.get('season')))
    users = api.get('league/{0}/users'.format(league_id),
                    cache_key='users_{0}.json'.format(league_id),
                    allow_cache=not live) or []
    rosters = api.get('league/{0}/rosters'.format(league_id),
                      cache_key='rosters_{0}.json'.format(league_id),
                      allow_cache=not live) or []
    owners, roster_to_owner = build_owner_index(users, rosters)
    log('  {0} owners, {1} rosters'.format(len(owners), len(rosters)))

    # Add player names to each roster so the file is readable on its own.
    rosters_out = []
    for r in rosters:
        rid = r.get('roster_id')
        settings = r.get('settings') or {}
        rosters_out.append({
            'roster_id': rid,
            'owner': roster_to_owner.get(rid, {}),
            'players': [player_brief(players, p) for p in (r.get('players') or [])],
            'starters': [player_brief(players, p) for p in (r.get('starters') or [])],
            'reserve': [player_brief(players, p) for p in (r.get('reserve') or [])],
            'taxi': [player_brief(players, p) for p in (r.get('taxi') or [])],
            # FAAB: Sleeper counts budget SPENT, so remaining = 1000 - spent.
            'faab_spent': settings.get('waiver_budget_used'),
            'faab_remaining': (
                (league.get('settings') or {}).get('waiver_budget', 0)
                - (settings.get('waiver_budget_used') or 0)
            ),
            'wins': settings.get('wins'),
            'losses': settings.get('losses'),
            'points_for': _pts(settings.get('fpts'), settings.get('fpts_decimal')),
            'points_against': _pts(settings.get('fpts_against'),
                                   settings.get('fpts_against_decimal')),
            'raw_settings': settings,
        })

    # -- drafts ---------------------------------------------------------------
    # A draft can be in progress right now, so never trust the cache for the
    # live season's picks.
    drafts = api.get('league/{0}/drafts'.format(league_id),
                     cache_key='drafts_{0}.json'.format(league_id),
                     allow_cache=not live) or []
    draft_results = []
    for d in drafts:
        draft_id = d.get('draft_id')
        picks = api.get('draft/{0}/picks'.format(draft_id),
                        cache_key='draftpicks_{0}.json'.format(draft_id),
                        allow_cache=not live) or []
        # slot_to_roster_id tells us which draft seat belongs to which team.
        slot_map = {str(k): v for k, v in (d.get('slot_to_roster_id') or {}).items()}
        pick_rows = []
        for p in picks:
            slot = str(p.get('draft_slot'))
            rid = p.get('roster_id') or slot_map.get(slot)
            meta = p.get('metadata') or {}
            pick_rows.append({
                'pick_no': p.get('pick_no'),
                'round': p.get('round'),
                'draft_slot': p.get('draft_slot'),
                'roster_id': rid,
                'team_label': label_for(roster_to_owner, rid),
                'picked_by_user_id': p.get('picked_by'),
                'player': player_brief(players, p.get('player_id')),
                # Sleeper stashes a name snapshot on the pick itself; handy if a
                # player later disappears from the master player list.
                'player_name_at_pick': (
                    (meta.get('first_name', '') + ' ' + meta.get('last_name', '')).strip()
                    or None),
                'is_keeper': p.get('is_keeper'),
            })
        draft_results.append({
            'draft_id': draft_id,
            'status': d.get('status'),
            'type': d.get('type'),
            'start_time': epoch_ms_to_iso(d.get('start_time')),
            'rounds': (d.get('settings') or {}).get('rounds'),
            'slot_to_roster_id': slot_map,
            'draft_order_user_ids': d.get('draft_order'),
            'pick_count': len(pick_rows),
            'picks': pick_rows,
        })
        log('  draft {0}: {1} picks [{2}]'.format(draft_id, len(pick_rows), d.get('status')))

    # -- weekly scores --------------------------------------------------------
    # In a chopped league there are no real matchups; what matters is each
    # roster's `points` for the week. We keep the raw per-week rows too, because
    # the elimination validator needs to know who was ON each roster that week.
    weekly_scores = []
    matchups_by_week = {}
    for wk in ALL_WEEKS:
        settled = week_is_settled(season, wk, nfl_state)
        rows = api.get('league/{0}/matchups/{1}'.format(league_id, wk),
                       cache_key='matchups_{0}_{1}.json'.format(league_id, wk),
                       allow_cache=settled)
        if not rows:
            continue                              # week never happened; skip quietly
        matchups_by_week[wk] = rows
        for m in rows:
            rid = m.get('roster_id')
            weekly_scores.append({
                'season': season,
                'week': wk,
                'roster_id': rid,
                'team_label': label_for(roster_to_owner, rid),
                'owner_id': (roster_to_owner.get(rid) or {}).get('owner_id'),
                'points': m.get('points'),
                'starters_count': len(m.get('starters') or []),
                'roster_size': len(m.get('players') or []),
            })
    played = sorted({w for w in matchups_by_week if week_was_played(matchups_by_week[w])})
    log('  weekly scores: {0} week(s) with data, {1} actually played {2}'.format(
        len(matchups_by_week), len(played), played))

    # -- transactions ---------------------------------------------------------
    transactions = []
    for wk in ALL_WEEKS:
        settled = week_is_settled(season, wk, nfl_state)
        rows = api.get('league/{0}/transactions/{1}'.format(league_id, wk),
                       cache_key='transactions_{0}_{1}.json'.format(league_id, wk),
                       allow_cache=settled)
        if not rows:
            continue
        for t in rows:
            transactions.append(normalise_transaction(t, wk, season, players,
                                                      roster_to_owner))
    log('  transactions: {0} total'.format(len(transactions)))

    return {
        'season': season,
        'league_id': league_id,
        'league': league,
        'users': users,
        'owners': owners,
        'roster_to_owner': roster_to_owner,
        'rosters_raw': rosters,
        'rosters_out': rosters_out,
        'draft_results': draft_results,
        'weekly_scores': weekly_scores,
        'matchups_by_week': matchups_by_week,
        'transactions': transactions,
    }


def _pts(whole, decimal):
    """Sleeper splits season point totals into whole + decimal parts."""
    if whole is None and decimal is None:
        return None
    return float(whole or 0) + float(decimal or 0) / 100.0


def normalise_transaction(t, week, season, players, roster_to_owner):
    """
    Flatten one Sleeper transaction into a readable row.

    The important, easy-to-miss detail for this league: Sleeper records a FAAB
    waiver claim as ONE transaction PER CLAIM, not one per player. A claim that
    lost the bidding is its own record with status "failed" and its own
    settings.waiver_bid. So losing bids ARE usually visible -- see
    build_bid_wars() below, which stitches the winners and losers back together
    per player. (The script measures this rather than assuming it, and the final
    report tells you exactly what your league's data contains.)
    """
    settings = t.get('settings') or {}
    adds = t.get('adds') or {}
    drops = t.get('drops') or {}

    def moves(mapping):
        out = []
        for pid, rid in (mapping or {}).items():
            row = player_brief(players, pid)
            row['roster_id'] = rid
            row['team_label'] = label_for(roster_to_owner, rid)
            out.append(row)
        return out

    return {
        'season': season,
        'week': week,
        'transaction_id': t.get('transaction_id'),
        'type': t.get('type'),                       # waiver | free_agent | trade
        'status': t.get('status'),                   # complete | failed
        'created': epoch_ms_to_iso(t.get('created')),
        'status_updated': epoch_ms_to_iso(t.get('status_updated')),
        'created_ms': t.get('created'),
        'roster_ids': t.get('roster_ids') or [],
        'team_labels': [label_for(roster_to_owner, r) for r in (t.get('roster_ids') or [])],
        'creator_user_id': t.get('creator'),
        'adds': moves(adds),
        'drops': moves(drops),
        'waiver_bid': settings.get('waiver_bid'),    # None for non-waiver moves
        'waiver_seq': settings.get('seq'),
        'draft_picks': t.get('draft_picks') or [],   # only populated on trades
        'waiver_budget_transfers': t.get('waiver_budget') or [],
        # Sleeper sometimes explains a failure here, e.g. "claimed by another owner".
        'notes': (t.get('metadata') or {}).get('notes'),
    }


# -- STEP 5: FAAB BID WARS ----------------------------------------------------

def build_bid_wars(transactions):
    """
    Group every waiver claim by the player being claimed, so you can see the
    whole auction for that player: who bid, how much, and who won.

    This is the file to look at for "what did the losing bids look like".
    """
    groups = defaultdict(list)
    for t in transactions:
        if t['type'] != 'waiver':
            continue
        for add in t['adds']:
            groups[(t['week'], add['player_id'])].append({
                'transaction_id': t['transaction_id'],
                'player_name': add['name'],
                'position': add['position'],
                'nfl_team': add['team'],
                'roster_id': add['roster_id'],
                'team_label': add['team_label'],
                'bid': t['waiver_bid'],
                'status': t['status'],
                'submitted': t['created'],
                'processed': t['status_updated'],
                'notes': t['notes'],
                'dropped_to_make_room': [d['name'] for d in t['drops']],
            })

    wars = []
    for (week, pid), bids in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        # Sort highest bid first so the auction reads top-down.
        bids.sort(key=lambda b: (b['bid'] is not None, b['bid'] or 0), reverse=True)
        winners = [b for b in bids if b['status'] == 'complete']
        losers = [b for b in bids if b['status'] != 'complete']
        wars.append({
            'week': week,
            'player_id': pid,
            'player_name': bids[0].get('player_name') if bids else None,
            'position': bids[0].get('position') if bids else None,
            'total_claims': len(bids),
            'winning_bid': winners[0]['bid'] if winners else None,
            'winning_team': winners[0]['team_label'] if winners else None,
            'losing_bid_count': len(losers),
            'all_bids': bids,
        })
    return wars


def bid_visibility_verdict(transactions):
    """
    Answer the question "does the API actually show me losing bids?" by
    counting what came back, rather than trusting documentation.
    """
    waivers = [t for t in transactions if t['type'] == 'waiver']
    failed = [t for t in waivers if t['status'] != 'complete']
    failed_with_bid = [t for t in failed if t['waiver_bid'] is not None]
    complete_with_bid = [t for t in waivers
                         if t['status'] == 'complete' and t['waiver_bid'] is not None]
    return {
        'waiver_transactions': len(waivers),
        'winning_claims_with_a_bid_amount': len(complete_with_bid),
        'failed_claims_returned': len(failed),
        'failed_claims_with_a_bid_amount': len(failed_with_bid),
        'losing_bids_visible': len(failed_with_bid) > 0,
    }


# -- STEP 6: REBUILDING THE ELIMINATIONS --------------------------------------

def week_was_played(rows):
    """
    Did this week actually happen?

    Sleeper happily returns a full set of rows scored 0.0 for a week that has
    not been played yet. If nobody scored anything, treat the week as empty.
    """
    return any((m.get('points') or 0) > 0 for m in (rows or []))


def reconstruct_eliminations(season_data):
    """
    Work out, week by week, who got chopped and who won the weekly high score.

    THE LOGIC
    ---------
    Start with every roster "alive". For each week that was actually played:
      - look ONLY at teams still alive (a team chopped in week 3 has an empty
        roster and will score ~0 in week 4; including it would wrongly chop
        somebody every week from then on)
      - lowest score  -> ELIMINATED this week
      - highest score -> WEEKLY HIGH, wins $25
    Stop once two teams are left; the next played week is the final, and the
    higher score there takes 1st place.

    Everything that looks off -- a tie at the bottom, a live team scoring zero,
    an elimination the transaction log does not back up -- is recorded in
    `flags` so it can be eyeballed by hand instead of silently trusted.
    """
    roster_to_owner = season_data['roster_to_owner']
    matchups_by_week = season_data['matchups_by_week']
    transactions = season_data['transactions']

    # Index the drops so the validator can ask "what did roster N drop in week W".
    drops_by_roster_week = defaultdict(set)
    for t in transactions:
        if t['status'] != 'complete':
            continue
        for d in t['drops']:
            drops_by_roster_week[(d['roster_id'], t['week'])].add(d['player_id'])

    alive = set(roster_to_owner.keys())
    if not alive:
        alive = {m.get('roster_id') for rows in matchups_by_week.values() for m in rows}

    weeks_table = []
    elimination_order = []      # oldest elimination first
    flags = []
    champion = runner_up = None
    final_week = None

    for wk in sorted(matchups_by_week.keys()):
        rows = matchups_by_week[wk]
        if not week_was_played(rows):
            continue

        # Scores for teams that are still in it.
        scores = {m.get('roster_id'): (m.get('points') or 0.0)
                  for m in rows if m.get('roster_id') in alive}
        if not scores:
            continue

        low_score = min(scores.values())
        high_score = max(scores.values())
        lowest = sorted(r for r, p in scores.items() if p == low_score)
        highest = sorted(r for r, p in scores.items() if p == high_score)

        week_flags = []
        if len(lowest) > 1:
            week_flags.append(
                'TIE for lowest score at {0:.2f} between {1} -- the chop is a guess'.format(
                    low_score, ', '.join(label_for(roster_to_owner, r) for r in lowest)))
        if len(highest) > 1:
            week_flags.append(
                'TIE for highest score at {0:.2f} between {1}'.format(
                    high_score, ', '.join(label_for(roster_to_owner, r) for r in highest)))
        if low_score == 0:
            week_flags.append(
                'A still-alive team scored 0.00 -- likely missing data, not a real chop')

        # -- the final week: two teams left, the winner takes the title --------
        if len(alive) <= 2:
            final_week = wk
            ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
            champion = ranked[0][0]
            runner_up = ranked[1][0] if len(ranked) > 1 else None
            weeks_table.append({
                'week': wk,
                'is_final': True,
                'eliminated_roster_id': runner_up,
                'eliminated_team': label_for(roster_to_owner, runner_up) if runner_up else None,
                'eliminated_score': round(scores.get(runner_up, 0.0), 2) if runner_up else None,
                'weekly_high_roster_id': highest[0],
                'weekly_high_team': label_for(roster_to_owner, highest[0]),
                'weekly_high_score': round(high_score, 2),
                'teams_alive_at_start': len(alive),
                'elimination_confirmed_by_drops': None,
                'flags': week_flags,
            })
            if runner_up:
                elimination_order.append(runner_up)
            flags.extend('Week {0}: {1}'.format(wk, f) for f in week_flags)
            break

        chopped = lowest[0]

        # -- cross-check against the transaction log --------------------------
        # A chopped team's whole roster is auto-dropped. If we see that block of
        # drops from the same roster in this week or the next, the chop is real.
        roster_players = set()
        for m in rows:
            if m.get('roster_id') == chopped:
                roster_players = {str(p) for p in (m.get('players') or [])}
        dropped = (drops_by_roster_week.get((chopped, wk), set())
                   | drops_by_roster_week.get((chopped, wk + 1), set()))
        matched = roster_players & dropped
        share = (len(matched) / len(roster_players)) if roster_players else None

        if share is None:
            confirmed = None
            week_flags.append('No roster snapshot for the chopped team; cannot validate')
        elif share >= DROP_VALIDATION_THRESHOLD:
            confirmed = True
        else:
            confirmed = False
            week_flags.append(
                'Only {0} of {1} of the chopped roster shows up as drops in weeks {2}-{3} '
                '({4:.0%}) -- verify this chop by hand'.format(
                    len(matched), len(roster_players), wk, wk + 1, share))

        weeks_table.append({
            'week': wk,
            'is_final': False,
            'eliminated_roster_id': chopped,
            'eliminated_team': label_for(roster_to_owner, chopped),
            'eliminated_score': round(low_score, 2),
            'weekly_high_roster_id': highest[0],
            'weekly_high_team': label_for(roster_to_owner, highest[0]),
            'weekly_high_score': round(high_score, 2),
            'teams_alive_at_start': len(alive),
            'elimination_confirmed_by_drops': confirmed,
            'drop_validation': {
                'roster_size_that_week': len(roster_players),
                'players_dropped_after': len(matched),
                'match_share': round(share, 3) if share is not None else None,
            },
            'flags': week_flags,
        })

        flags.extend('Week {0}: {1}'.format(wk, f) for f in week_flags)
        elimination_order.append(chopped)
        alive.discard(chopped)

    # -- final standings ------------------------------------------------------
    # 1st and 2nd come from the final week. After that, placement is simply the
    # reverse of the chop order: the last team chopped finished 3rd, and so on.
    standings = []
    if champion:
        standings.append({'place': 1, 'roster_id': champion,
                          'team': label_for(roster_to_owner, champion),
                          'result': 'Champion -- $350'})
    if runner_up:
        standings.append({'place': 2, 'roster_id': runner_up,
                          'team': label_for(roster_to_owner, runner_up),
                          'result': 'Runner-up -- $150'})

    others = [r for r in elimination_order if r not in (champion, runner_up)]
    place = len(standings) + 1
    for rid in reversed(others):
        elim_week = next((w['week'] for w in weeks_table
                          if w['eliminated_roster_id'] == rid), None)
        standings.append({'place': place, 'roster_id': rid,
                          'team': label_for(roster_to_owner, rid),
                          'result': 'Chopped week {0}'.format(elim_week)})
        place += 1

    # Anyone never chopped and not in the final means the season is unfinished.
    still_alive = [r for r in alive if r not in (champion, runner_up)]
    for rid in sorted(still_alive):
        standings.append({'place': None, 'roster_id': rid,
                          'team': label_for(roster_to_owner, rid),
                          'result': 'Still alive (season in progress)'})

    # Weekly-high winnings, which is real money in this league.
    high_score_tally = defaultdict(int)
    for w in weeks_table:
        if w['weekly_high_roster_id'] is not None:
            high_score_tally[w['weekly_high_roster_id']] += 1
    payouts = [{
        'roster_id': rid,
        'team': label_for(roster_to_owner, rid),
        'weekly_high_wins': n,
        'weekly_high_earnings': n * 25,
    } for rid, n in sorted(high_score_tally.items(), key=lambda kv: -kv[1])]

    return {
        'season': season_data['season'],
        'weeks': weeks_table,
        'final_week': final_week,
        'champion_roster_id': champion,
        'runner_up_roster_id': runner_up,
        'final_standings': standings,
        'elimination_order_roster_ids': elimination_order,
        'weekly_high_payouts': payouts,
        'season_complete': champion is not None,
        'flags': flags,
    }


# -- STEP 7: WRITING THE OUTPUT -----------------------------------------------

def write_season_files(out_dir, season_data, summary, bid_wars, bid_verdict):
    """Write one folder of clean, self-describing files for this season."""
    season = season_data['season']
    d = os.path.join(out_dir, str(season))
    league = season_data['league']

    write_json(os.path.join(d, 'league_settings.json'), {
        'season': season,
        'league_id': season_data['league_id'],
        'name': league.get('name'),
        'status': league.get('status'),
        'sport': league.get('sport'),
        'season_type': league.get('season_type'),
        'total_rosters': league.get('total_rosters'),
        'previous_league_id': league.get('previous_league_id'),
        'roster_positions': league.get('roster_positions'),
        'scoring_settings': league.get('scoring_settings'),
        'settings': league.get('settings'),
        'metadata': league.get('metadata'),
    })

    write_json(os.path.join(d, 'owners.json'), season_data['owners'])
    write_json(os.path.join(d, 'rosters.json'), season_data['rosters_out'])
    write_json(os.path.join(d, 'draft_results.json'), season_data['draft_results'])
    write_json(os.path.join(d, 'weekly_scores.json'), season_data['weekly_scores'])
    write_json(os.path.join(d, 'transactions_all_weeks.json'), season_data['transactions'])
    write_json(os.path.join(d, 'waiver_bids.json'), {
        'how_to_read_this': (
            'One entry per player claimed on waivers per week. all_bids lists every '
            'claim Sleeper returned for that player, winning and losing, highest first. '
            'status "complete" won the player; anything else lost.'),
        'losing_bid_visibility': bid_verdict,
        'bid_wars': bid_wars,
    })
    write_json(os.path.join(d, 'season_summary.json'), summary)

    # A flat CSV of the week-by-week story, easy to paste into a chat or a sheet.
    csv_path = os.path.join(d, 'season_summary.csv')
    os.makedirs(d, exist_ok=True)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['Week', 'Eliminated Team', 'Eliminated Score',
                    'Weekly High Team', 'Weekly High Score',
                    'Teams Alive At Start', 'Elimination Confirmed By Drops',
                    'Is Final Week', 'Flags'])
        for row in summary['weeks']:
            w.writerow([
                row['week'],
                row['eliminated_team'] or '',
                row['eliminated_score'] if row['eliminated_score'] is not None else '',
                row['weekly_high_team'] or '',
                row['weekly_high_score'] if row['weekly_high_score'] is not None else '',
                row['teams_alive_at_start'],
                {True: 'yes', False: 'NO', None: 'n/a'}[row['elimination_confirmed_by_drops']],
                'yes' if row['is_final'] else '',
                ' | '.join(row['flags']),
            ])

    log('  wrote {0}'.format(d))


def find_new_owners(seasons):
    """
    Which owners are new this year?

    Compare the current season's user_ids against every user_id that has ever
    appeared in an earlier season. Anyone with no history is a new face.
    """
    if not seasons:
        return {'new_owners': [], 'note': 'no seasons found'}

    current = seasons[0]                          # chain is newest-first
    prior_ids = set()
    for s in seasons[1:]:
        prior_ids.update(o['user_id'] for o in s['owners'])

    new = [o for o in current['owners'] if o['user_id'] not in prior_ids]
    returning = [o for o in current['owners'] if o['user_id'] in prior_ids]

    return {
        'current_season': current['season'],
        'seasons_compared_against': [s['season'] for s in seasons[1:]],
        'new_owner_count': len(new),
        'new_owners': [{
            'user_id': o['user_id'],
            'username': o['username'],
            'team_name': o['team_name'],
        } for o in new],
        'returning_owner_count': len(returning),
        'returning_owners': [{
            'user_id': o['user_id'],
            'username': o['username'],
            'team_name': o['team_name'],
        } for o in returning],
    }


# -- STEP 8: THE PLAIN-ENGLISH REPORT -----------------------------------------

def build_report(seasons, summaries, new_owners, bid_verdicts, api, out_dir):
    """Assemble the human-readable wrap-up that prints at the end of a run."""
    lines = []
    add = lines.append

    add('=' * 72)
    add("KING'S JUSTICE DATA PULL -- SUMMARY")
    add('Run at {0}'.format(datetime.now(timezone.utc).isoformat(timespec='seconds')))
    add('=' * 72)
    add('')

    # 1. seasons
    add('SEASONS FOUND: {0}'.format(len(seasons)))
    for s in seasons:
        add('  - {0}  league {1}  "{2}"  [{3}]'.format(
            s['season'], s['league_id'], s['league'].get('name'), s['league'].get('status')))
    add('')

    # 2. per-season outcome
    add('SEASON OUTCOMES')
    for s in seasons:
        sm = summaries[s['season']]
        if sm['season_complete']:
            champ = next((x['team'] for x in sm['final_standings'] if x['place'] == 1), '?')
            second = next((x['team'] for x in sm['final_standings'] if x['place'] == 2), '?')
            add('  {0}: won by {1}; runner-up {2} (final was week {3})'.format(
                s['season'], champ, second, sm['final_week']))
        else:
            done = len(sm['weeks'])
            alive = [x['team'] for x in sm['final_standings'] if x['place'] is None]
            add('  {0}: IN PROGRESS -- {1} week(s) scored, {2} team(s) still alive'.format(
                s['season'], done, len(alive)))
    add('')

    # 3. validation flags
    add('WEEKS THAT DID NOT VALIDATE CLEANLY')
    any_flags = False
    for s in seasons:
        sm = summaries[s['season']]
        if sm['flags']:
            any_flags = True
            add('  {0}:'.format(s['season']))
            for f in sm['flags']:
                add('    - {0}'.format(f))
    if not any_flags:
        add('  None. Every chop matched the lowest score AND showed up as a block of')
        add('  drops in the transaction log right afterwards.')
    add('')

    # 4. the FAAB question
    add('CAN WE SEE LOSING FAAB BIDS?')
    total_waivers = sum(v['waiver_transactions'] for v in bid_verdicts.values())
    total_failed = sum(v['failed_claims_with_a_bid_amount'] for v in bid_verdicts.values())
    if total_waivers == 0:
        add('  No waiver transactions came back at all, so there is nothing to judge')
        add('  yet. Re-run once the season has some waiver activity.')
    elif total_failed > 0:
        add('  YES. Sleeper returns each losing claim as its own transaction record with')
        add('  status "failed" and its own settings.waiver_bid, so the full auction is')
        add('  visible. Across all seasons: {0} waiver claims, {1} of them losing bids'.format(
            total_waivers, total_failed))
        add('  with an amount attached. See waiver_bids.json in each season folder --')
        add('  it groups every claim per player so you can read the bidding top-down.')
    else:
        add('  NO -- and this is the caveat you asked me to flag. {0} waiver claims came'.format(
            total_waivers))
        add('  back, but NOT ONE of them had status "failed" with a bid amount. That means')
        add('  this league only exposes the WINNING claim per player, so losing bids are')
        add('  not retrievable from the public API. To get them you would need either the')
        add('  commissioner\'s in-app transaction log, or Sleeper\'s private/GraphQL API')
        add('  with a logged-in session. Flagging clearly rather than guessing.')
    for season, v in sorted(bid_verdicts.items(), reverse=True):
        add('    {0}: {1} waiver claims, {2} winning w/ bid, {3} failed, {4} failed w/ bid'.format(
            season, v['waiver_transactions'], v['winning_claims_with_a_bid_amount'],
            v['failed_claims_returned'], v['failed_claims_with_a_bid_amount']))
    add('')

    # 5. new owners
    compared = new_owners.get('seasons_compared_against') or []
    if not compared:
        add('NEW OWNERS THIS SEASON: cannot tell')
        add('  Only one season exists in the chain, so there is no history to compare')
        add('  against and every owner trivially looks new. Listing them anyway:')
        for o in new_owners.get('new_owners', []):
            add('    - {0}'.format(o['username']))
    else:
        add('NEW OWNERS THIS SEASON: {0} (compared against {1})'.format(
            new_owners.get('new_owner_count', 0), ', '.join(compared)))
        for o in new_owners.get('new_owners', []):
            add('  - {0}{1}'.format(
                o['username'],
                ' (team: {0})'.format(o['team_name']) if o['team_name'] else ''))
        if not new_owners.get('new_owners'):
            add('  Nobody new -- every current owner appears in at least one prior season.')
        add('  Returning owners: {0}'.format(new_owners.get('returning_owner_count', 0)))
    add('')

    add('API CALLS THIS RUN: {0} live, {1} served from cache'.format(
        api.calls_made, api.cache_hits))
    if api.errors:
        add('ERRORS ({0}):'.format(len(api.errors)))
        for e in api.errors[:10]:
            add('  - {0}'.format(e))
    add('')
    add('Everything written to: {0}'.format(out_dir))
    add('=' * 72)

    return '\n'.join(lines)


# -- MAIN ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Pull the King's Justice league history from Sleeper.")
    parser.add_argument('--league-id', default=CURRENT_LEAGUE_ID,
                        help='current season league id (default: %(default)s)')
    parser.add_argument('--out', default=DEFAULT_OUT_DIR,
                        help='output folder (default: %(default)s)')
    parser.add_argument('--refresh-all', action='store_true',
                        help='ignore every cached response and re-pull from scratch')
    parser.add_argument('--refresh-players', action='store_true',
                        help='force a fresh download of the NFL player list')
    args = parser.parse_args()

    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)

    api = Sleeper(refresh_all=args.refresh_all)

    log("Pulling the King's Justice league from Sleeper")
    log('Output folder: {0}'.format(out_dir))
    log('')

    # What week is it? This decides what we can safely serve from cache.
    nfl_state = get_nfl_state(api)
    log('NFL state: season {0}, week {1} ({2})'.format(
        nfl_state['season'], nfl_state['week'], nfl_state['season_type']))

    # 1. every season of this league
    log('\nWalking the league chain backwards...')
    chain = discover_league_chain(api, args.league_id)
    if not chain:
        log('ERROR: could not read the starting league. Check the league id and '
            'your internet connection.')
        return 1
    write_json(os.path.join(out_dir, 'league_chain.json'), [{
        'season': c['season'], 'league_id': c['league_id'],
        'name': c['name'], 'status': c['status'],
        'previous_league_id': c['previous_league_id'],
    } for c in chain])

    # 2. the player dictionary, once, shared by every season
    log('\nLoading the NFL player list...')
    players = load_players(api, out_dir, force_refresh=args.refresh_players)

    # 3. pull each season, then rebuild its elimination history
    seasons, summaries, bid_verdicts = [], {}, {}
    for season_info in chain:
        data = pull_season(api, season_info, players, nfl_state)
        summary = reconstruct_eliminations(data)
        wars = build_bid_wars(data['transactions'])
        verdict = bid_visibility_verdict(data['transactions'])

        write_season_files(out_dir, data, summary, wars, verdict)
        seasons.append(data)
        summaries[data['season']] = summary
        bid_verdicts[data['season']] = verdict

    # 4. who is new this year
    new_owners = find_new_owners(seasons)
    write_json(os.path.join(out_dir, 'new_owners.json'), new_owners)

    # 5. the wrap-up
    report = build_report(seasons, summaries, new_owners, bid_verdicts, api, out_dir)
    with open(os.path.join(out_dir, 'pipeline_report.txt'), 'w', encoding='utf-8') as f:
        f.write(report + '\n')
    log('\n' + report)
    return 0


if __name__ == '__main__':
    sys.exit(main())
