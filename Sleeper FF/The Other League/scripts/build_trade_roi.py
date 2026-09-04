"""
build_trade_roi.py — builds trade-roi.json (Phase 12)

Expands every trade in league history into its assets, traces every traded draft
pick to the player actually selected with it, scores each asset in points over
replacement (PoR) from the trade date to now, and emits the empirical pick curve
that both Phase 12 views run on.

  python scripts/build_trade_roi.py              build and write
  python scripts/build_trade_roi.py --dry-run    report, write nothing
  python scripts/build_trade_roi.py --report     print the distributions used to
                                                 set the verdict/maturity thresholds

Output: trade-roi.json (commit this to the repo)

Reads the two committed data files rather than refetching stats:
  stats-history.json      per-week stat lines for every player the league has touched
  replacement-levels.json per-week replacement baseline per position

WHY THIS IS OFFLINE. Four seasons x 18 weeks of transactions, plus four drafts and
the 5 MB player database, is far too much to pull on page load, and the CORS proxy
chain is too fragile to depend on for a whole view.

PICK TRACING IS EXACT — DO NOT MAKE IT FUZZY.
A trade's draft_picks[] entry carries roster_id = the pick's ORIGINAL owner. Each
draft carries slot_to_roster_id mapping draft slot -> original owner. So
(season, round, original_owner) identifies exactly one pick, and that pick's
player_id is the player taken with it. Verified: 58/58 past picks resolve, 0 fail.
Do not reach for name matching, and do not compute a pick from pick_no — pick_no is
(round-1)*12 + draft_slot and is NOT contiguous, because each season has a lone
round-5 consolation bonus pick.
"""
import argparse
import json
import os
import statistics
import sys
import time
import urllib.request

BASE = 'https://api.sleeper.app/v1'
LID_2026 = '1316225642072662016'
FIRST_SEASON = 2023
MAX_WEEK = 17

# 2023 was the startup AUCTION (29 rounds, 348 picks), not a rookie draft.
# Rookie-draft analysis covers the linear 4-round drafts only.
ROOKIE_DRAFT_FIRST_SEASON = 2024

TOL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(TOL_ROOT, 'trade-roi.json')
STATS_PATH = os.path.join(TOL_ROOT, 'stats-history.json')
REPL_PATH = os.path.join(TOL_ROOT, 'replacement-levels.json')

SCORED_POSITIONS = ('QB', 'RB', 'WR', 'TE')

# A rookie "got a role" at 6+ scoreable weeks — roughly a third of a season.
ROLE_MIN_WEEKS = 6
# A rookie season counts as a "hit" at this PoR. Set where the data separates:
# the median rookie PoR in rounds 2, 3 and 4 is 0.0, so any real bar splits the
# genuine contributors from the majority who returned nothing.
HIT_POR = 50.0

# Pick bands for the draft-capital board. Round 1 is split because the top of it
# behaves completely differently from the back of it (83% hit rate at 1.01-1.06
# vs 67% at 1.07-1.12, and a far higher median).
PICK_BANDS = [('1.01-1.03', 1, 3), ('1.04-1.06', 4, 6), ('1.07-1.12', 7, 12),
              ('Round 2', 13, 24), ('Round 3', 25, 36), ('Round 4+', 37, 99)]

# Mirrors SDATA in index.html; parity with calcPts() is asserted by
# build_replacement_levels.py's check. Kept here so this script stands alone.
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


def coverage_gaps(stats, repl):
    """Every played week in stats-history that replacement-levels.json cannot score.

    THIS GUARD EXISTS BECAUSE THE FAILURE IT CATCHES IS COMPLETELY SILENT.
    `Engine.por` skips any week with no baseline (`base is None -> continue`), so a
    stats file that has run ahead of the baselines does not raise, does not warn,
    and does not produce a visibly wrong number — it produces a plausible-looking
    trade-roi.json in which those weeks simply never happened. In the live season
    that means every 2026 trade sits frozen at 0-0 all year while the page cheerfully
    reports it as scored. The two files must always be rebuilt in step, baselines
    first; this makes forgetting that a loud failure instead of a quiet one.
    """
    gaps = []
    for y in sorted(k for k in stats if k != 'generated'):
        weeks = set(stats[y].get('weeks', {}))
        have = set((repl.get('levels', {}).get(y) or {}))
        missing = sorted(weeks - have, key=int)
        if missing:
            gaps.append(f'{y}: stats has week(s) {missing} with no replacement baseline')
    return gaps


# ── league scaffolding ────────────────────────────────────────────────────────

def get_league_chain():
    """season(int) -> league_id. Keyed on each league's OWN season, never a counter."""
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


def get_managers(league_ids):
    """season -> roster_id -> {user_id, name}.

    Per season, NOT once from 2026. Roster 11 was CCJ's for 2023-25 and Andrew
    Bova's from 2026, so a move must be credited to whoever actually made it.
    """
    out = {}
    for season, lid in sorted(league_ids.items()):
        users = {u['user_id']: u for u in fetch(f'/league/{lid}/users')}
        row = {}
        for r in fetch(f'/league/{lid}/rosters'):
            uid = r.get('owner_id')
            u = users.get(uid) or {}
            row[r['roster_id']] = {
                'user_id': uid,
                'name': u.get('display_name') or '?',
            }
        out[season] = row
    return out


def build_manager_index(managers):
    """user_id -> canonical identity. AGGREGATE ON user_id, NEVER ON DISPLAY NAME.

    Roster 9 is one human under two names — Mblack2889 in 2023/24, MJBlack from
    2025 — so a leaderboard keyed on the display name splits his draft record in
    half and ranks him twice. Roster 11 is the opposite trap and must NOT be
    merged: CCJ managed it 2023-25 and Andrew Bova from 2026, two different
    people on one roster_id, which is why every row carries the manager resolved
    for its own season rather than today's owner.

    `name` is the most recent display name; `names_seen` keeps the history so a
    view can caption an old row with the name that was current at the time.
    """
    idx = {}
    for season in sorted(managers):
        for rid, m in managers[season].items():
            uid = m.get('user_id')
            if not uid:
                continue
            e = idx.setdefault(uid, {'user_id': uid, 'name': None,
                                     'names_seen': [], 'rosters': [],
                                     'seasons': {}})
            e['name'] = m['name']                      # seasons ascend, last wins
            if m['name'] not in e['names_seen']:
                e['names_seen'].append(m['name'])
            if rid not in e['rosters']:
                e['rosters'].append(rid)
            e['seasons'][str(season)] = {'roster_id': rid, 'name': m['name']}
    return idx


def get_drafts(league_ids):
    """season -> {'slot_to_roster': {slot:rid}, 'picks': [...], 'type': str}."""
    out = {}
    for season, lid in sorted(league_ids.items()):
        for d in fetch(f'/league/{lid}/drafts'):
            picks = fetch(f"/draft/{d['draft_id']}/picks")
            full = fetch(f"/draft/{d['draft_id']}")
            out[int(full['season'])] = {
                'type': full.get('type'),
                'slot_to_roster': {int(k): v for k, v in
                                   (full.get('slot_to_roster_id') or {}).items()},
                'picks': picks,
            }
            time.sleep(0.2)
    return out


def get_trades(league_ids):
    """Every completed trade, newest league first, each tagged with its season."""
    out = []
    for season, lid in sorted(league_ids.items()):
        for wk in range(1, 19):   # week 0 is empty in every season of this league
            try:
                txns = fetch(f'/league/{lid}/transactions/{wk}')
            except Exception as e:
                raise RuntimeError(f'{season} wk{wk} transactions failed: {e}')
            for t in txns:
                if t.get('type') == 'trade' and t.get('status') == 'complete':
                    t['_season'] = season
                    out.append(t)
            time.sleep(0.1)
    out.sort(key=lambda t: t['created'])
    return out


# ── the PoR engine ────────────────────────────────────────────────────────────

class Engine:
    def __init__(self, stats, repl, positions, names):
        self.stats = stats
        self.repl = repl['levels']
        self.pos = positions
        self.names = names
        self.years = sorted(int(y) for y in stats if y != 'generated')
        self._pools = {}

    def played_weeks(self, year, week_from):
        """Weeks of `year` at or after week_from that actually have data."""
        y = str(year)
        if y not in self.stats:
            return []
        return sorted((int(w) for w in self.stats[y]['weeks'] if int(w) >= week_from))

    def opportunity(self, pid, year):
        """Was this player actually given a chance in `year`, separate from whether
        he was any good with it.

        This exists because "rounds 3 and 4 never get a shot" turned out to be true
        in outcome but wrong in mechanism. Measured across the 2024+2025 classes,
        only 3/24 and 4/24 late-round picks never recorded a scoreable week, and
        most had at least one week above replacement — they were on the field. The
        real gap is VOLUME: round 1 averages 171 touches, rounds 3-4 average 42-46.
        A manager whose pick landed behind a starter and got 40 touches did not make
        the same mistake as one whose pick got 200 touches and was bad with them,
        and a single PoR number cannot tell those apart.

        `touches` is deliberately position-appropriate rather than one formula:
        attempts for a QB, carries + catches for everyone else. We have no target
        data, so receptions stand in for opportunity at WR/TE.
        """
        pos = self.pos.get(str(pid))
        if pos not in SCORED_POSITIONS:
            return None
        y = str(year)
        if y not in self.stats:
            return None
        dressed = used = startable = 0
        touches = 0.0
        ylevels = self.repl.get(y, {})
        for w, wd in self.stats[y]['weeks'].items():
            line = wd.get(str(pid))
            if not line:
                continue
            dressed += 1
            if not [k for k in line if k != 'gp']:
                continue           # dressed, did nothing scoreable
            used += 1
            if pos == 'QB':
                touches += line.get('pass_att', 0) + line.get('rush_att', 0)
            else:
                touches += line.get('rush_att', 0) + line.get('rec', 0)
            base = (ylevels.get(str(w)) or {}).get(pos)
            if base is not None and calc_pts(line, pos) > base:
                startable += 1
        return {'weeks_dressed': dressed, 'weeks_used': used,
                'weeks_startable': startable, 'touches': round(touches, 1),
                'usage_pct': self.usage_percentile(pos, year, touches),
                'got_role': used >= ROLE_MIN_WEEKS}

    def usage_percentile(self, pos, year, touches):
        """Where this touch count sits among everyone at the same position that year.

        RAW TOUCHES ARE NOT COMPARABLE ACROSS POSITIONS and reporting them pooled
        is actively misleading: the 1.01-1.03 band came out at 384 "touches" versus
        75 for 1.04-1.06, which looked like the top three picks getting five times
        the opportunity. They were not — the top band happened to hold Caleb
        Williams, Jayden Daniels and Cameron Ward, and a QB's pass attempts dwarf a
        running back's carries. A percentile within position is the comparable
        figure, so use usage_pct for any cross-band claim and keep raw touches only
        for a single player's own card.
        """
        pool = self._usage_pool(pos, year)
        if not pool:
            return None
        below = sum(1 for t in pool if t < touches)
        return round(below / len(pool), 3)

    def _usage_pool(self, pos, year):
        key = (pos, year)
        if key in self._pools:
            return self._pools[key]
        y = str(year)
        agg = {}
        for wd in self.stats.get(y, {}).get('weeks', {}).values():
            for pid, line in wd.items():
                if self.pos.get(str(pid)) != pos:
                    continue
                if not [k for k in line if k != 'gp']:
                    continue
                if pos == 'QB':
                    agg[pid] = agg.get(pid, 0) + line.get('pass_att', 0) + line.get('rush_att', 0)
                else:
                    agg[pid] = agg.get(pid, 0) + line.get('rush_att', 0) + line.get('rec', 0)
        self._pools[key] = sorted(agg.values())
        return self._pools[key]

    def por(self, pid, start_year, start_week):
        """Cumulative points over replacement from (start_year, start_week) to now.

        A week counts only when the player has a stat line carrying more than a
        bare `gp`. A player who was active but recorded nothing scoreable was not
        being started, and charging him a full replacement week would measure the
        manager's bench, not the asset. Weeks he missed contribute nothing —
        availability is already captured, because this is a cumulative sum and a
        player who misses six games simply accrues six fewer weeks of credit.

        `por` IS FLOORED AT ZERO; `por_signed` keeps the real number.
        This is not cosmetic and must not be "tidied" away. 31% of traded assets
        run negative, some past -60 (Cade Stover -78 as a 4th-round rookie TE,
        Mecole Hardman -65). Nobody ever started those players — a rostered asset's
        true floor is zero, because a manager benches a bust rather than paying a
        replacement-level penalty for him every week. Scoring the raw negative made
        DUMPING a bust register as a +65 win for the team that gave him away, which
        inverts the entire question the page asks. Signed values are kept for
        display (a "BUST" tag reads off por_signed), never for the trade margin.
        """
        pos = self.pos.get(str(pid))
        if pos not in SCORED_POSITIONS:
            return None            # K/DEF/unknown — no baseline exists, don't invent one
        total = 0.0
        weeks = 0
        raw = 0.0
        for year in self.years:
            if year < start_year:
                continue
            wk_from = start_week if year == start_year else 1
            ylevels = self.repl.get(str(year), {})
            for w in self.played_weeks(year, wk_from):
                line = self.stats[str(year)]['weeks'][str(w)].get(str(pid))
                if not line:
                    continue
                if not [k for k in line if k != 'gp']:
                    continue       # dressed, did nothing scoreable
                base = (ylevels.get(str(w)) or {}).get(pos)
                if base is None:
                    continue
                pts = calc_pts(line, pos)
                total += pts - base
                raw += pts
                weeks += 1
        return {'por': round(max(0.0, total), 1), 'por_signed': round(total, 1),
                'raw': round(raw, 1), 'weeks': weeks,
                'position': pos, 'name': self.names.get(str(pid), '?')}


# ── pick tracing + curve ──────────────────────────────────────────────────────

def resolve_pick(drafts, season, rnd, orig_roster):
    """(season, round, original owner) -> the pick actually made. Exact, not fuzzy."""
    d = drafts.get(int(season))
    if not d:
        return None
    for p in d['picks']:
        if p['round'] == rnd and d['slot_to_roster'].get(p['draft_slot']) == orig_roster:
            return p
    return None


def rookie_pick_rows(drafts, engine, managers):
    """Every rookie-draft pick, with the rookie-year PoR it produced."""
    rows = []
    for season in sorted(drafts):
        if season < ROOKIE_DRAFT_FIRST_SEASON:
            continue                       # 2023 was the startup auction
        d = drafts[season]
        for p in d['picks']:
            pid = p.get('player_id')
            orig = d['slot_to_roster'].get(p['draft_slot'])
            taken_by = p['roster_id']
            m = managers.get(season, {}).get(taken_by, {})
            r = engine.por(pid, season, 1) if pid else None
            meta = p.get('metadata') or {}
            rows.append({
                'season': season,
                'round': p['round'],
                'slot': p['draft_slot'],
                'pick_no': p['pick_no'],
                'player_id': str(pid) if pid else None,
                'player': f"{meta.get('first_name','')} {meta.get('last_name','')}".strip() or None,
                'position': meta.get('position'),
                'original_roster': orig,
                'drafted_by_roster': taken_by,
                'drafted_by': m.get('name'),
                'drafted_by_uid': m.get('user_id'),
                # Rookie-year PoR is the like-for-like basis: every class has one,
                # so a 2024 pick can't out-rank a 2025 pick purely on extra time.
                'rookie_por': (r or {}).get('por'),
                'rookie_por_signed': (r or {}).get('por_signed'),
                'rookie_weeks': (r or {}).get('weeks'),
                'scoreable': r is not None,
                'opportunity': engine.opportunity(pid, season) if pid else None,
            })
    return rows


def class_factors(rows, live_season):
    """season -> how strong that rookie class was, relative to the average class.

    The 2024 class produced 2.39x the total PoR of 2025 (2506 vs 1048), and round 1
    alone averaged 135.8 against 56.9 — both measured over one rookie season each,
    so that is genuine class quality and not one class having had longer to
    accumulate. A pooled expectation curve therefore hands a structural edge to
    whoever happened to hold picks in the strong year. Scaling each class's
    expectation by its own output removes that: a manager is measured against the
    class he actually drafted in.
    """
    per = {}
    for r in rows:
        if r['season'] >= live_season or r['rookie_por'] is None:
            continue
        per.setdefault(r['season'], []).append(r['rookie_por'])
    if not per:
        return {}
    overall = statistics.mean([v for vs in per.values() for v in vs])
    if overall <= 0:
        return {s: 1.0 for s in per}
    return {s: round(statistics.mean(v) / overall, 3) for s, v in per.items()}


def build_draft_capital(rows, live_season):
    """What a pick at each slot band actually buys — opportunity AND production.

    This is the answer to "are late picks bad, or just never used?" Report both
    sides so the two are never confused again.
    """
    out = []
    for label, lo, hi in PICK_BANDS:
        v = [r for r in rows
             if r['season'] < live_season and r['rookie_por'] is not None
             and lo <= r['pick_no'] <= hi]
        if not v:
            continue
        por = sorted(r['rookie_por'] for r in v)
        opp = [r['opportunity'] for r in v if r['opportunity']]
        n = len(v)
        out.append({
            'band': label, 'from_pick': lo, 'to_pick': hi, 'n': n,
            'hits': sum(1 for p in por if p >= HIT_POR),
            'hit_rate': round(sum(1 for p in por if p >= HIT_POR) / n, 3),
            'avg_por': round(statistics.mean(por), 1),
            'median_por': round(statistics.median(por), 1),
            'best_por': por[-1], 'worst_por': por[0],
            # usage_pct, not raw touches — see Engine.usage_percentile for why
            # pooling QB attempts with RB carries made the top band look 5x busier.
            'avg_usage_pct': round(statistics.mean(
                [o['usage_pct'] for o in opp if o['usage_pct'] is not None]), 3)
                if any(o['usage_pct'] is not None for o in opp) else None,
            'avg_touches': round(statistics.mean([o['touches'] for o in opp]), 0) if opp else None,
            'avg_weeks_used': round(statistics.mean([o['weeks_used'] for o in opp]), 1) if opp else None,
            'never_used': sum(1 for o in opp if o['weeks_used'] == 0),
            'got_role': sum(1 for o in opp if o['got_role']),
            'got_role_rate': round(sum(1 for o in opp if o['got_role']) / len(opp), 3) if opp else None,
            # Conditional on actually being used — separates a bad landing spot
            # from a bad evaluation.
            'avg_por_given_role': round(statistics.mean(
                [r['rookie_por'] for r in v
                 if r['opportunity'] and r['opportunity']['got_role']]), 1)
                if any(r['opportunity'] and r['opportunity']['got_role'] for r in v) else None,
        })
    return out


def build_pick_curve(rows, live_season):
    """slot -> expected rookie-year PoR, from this league's own completed classes.

    Fitted as a monotone-decreasing smoothing over pick_no rather than a raw
    per-slot average: only two classes have played, so a raw slot average is the
    mean of two observations and is noise. See the sample-size note in CLAUDE.md.
    """
    played = [r for r in rows if r['season'] < live_season and r['rookie_por'] is not None]
    by_pick = {}
    for r in played:
        by_pick.setdefault(r['pick_no'], []).append(r['rookie_por'])

    if not by_pick:
        return {'by_pick': {}, 'by_round': {}, 'n': 0}

    # Smooth with a centred window over pick order, then enforce monotonicity so
    # a noisy pair at pick 9 can't make pick 9 "worth more" than pick 3.
    picks = sorted(by_pick)
    smoothed = {}
    for pk in picks:
        window = [v for q in picks if abs(q - pk) <= 6 for v in by_pick[q]]
        smoothed[pk] = statistics.mean(window)
    running = None
    for pk in picks:
        if running is None or smoothed[pk] < running:
            running = smoothed[pk]
        smoothed[pk] = round(running, 1)

    # Round averages price the future picks that have no slot yet, so they get the
    # same monotone clamp as by_pick. Raw, they came out
    # {1: 96.3, 2: 29.6, 3: 4.6, 4: 14.0, 5: 42.2} — round 5 is TWO picks (Trey
    # Benson, Jaxson Dart) and round 4 is carried by Bucky Irving. Left alone, a
    # traded 2027 4th would be priced above a 2027 3rd.
    grouped = {}
    for r in played:
        grouped.setdefault(r['round'], []).append(r['rookie_por'])
    by_round, running = {}, None
    for k in sorted(grouped):
        v = statistics.mean(grouped[k])
        running = v if running is None else min(running, v)
        by_round[k] = round(running, 1)

    return {'by_pick': smoothed, 'by_round': by_round, 'n': len(played),
            'classes': sorted({r['season'] for r in played})}


def expected_for_pick(curve, pick_no=None, rnd=None):
    """Expected rookie-year PoR. Keys survive a JSON round-trip as strings, so
    every lookup tries both forms rather than silently returning None."""
    def get(d, k):
        if k is None:
            return None
        return d.get(k, d.get(str(k)))
    v = get(curve['by_pick'], pick_no)
    if v is None:
        v = get(curve['by_round'], rnd)
    return v


# ── trades ────────────────────────────────────────────────────────────────────

def trade_start(txn, season_start_week=1):
    """(year, week) from which a trade's assets start accruing.

    `leg` is the week the trade processed. An offseason trade carries leg 1 and
    should accrue from week 1. An in-season trade accrues from the FOLLOWING week:
    the week it landed in was already partly played, and crediting it would hand a
    manager points scored before he owned the player.
    """
    leg = txn.get('leg') or 1
    return (txn['_season'], 1 if leg <= 1 else leg + 1)


REVERSAL_WINDOW_MS = 48 * 3600 * 1000


def asset_flows(txn):
    """Every asset this trade moved, as (key, from_roster, to_roster)."""
    flows = set()
    drops = txn.get('drops') or {}
    for pid, to_rid in (txn.get('adds') or {}).items():
        flows.add((f'p{pid}', drops.get(pid), to_rid))
    for p in (txn.get('draft_picks') or []):
        flows.add((f"d{p['season']}.{p['round']}.{p['roster_id']}",
                   p.get('previous_owner_id'), p.get('owner_id')))
    return frozenset(flows)


def find_reversals(trades):
    """transaction_id -> the id of the trade that undid it (both directions).

    Two of this league's 52 trades are a pair: Ja'Marr Chase moved from roster 10
    to roster 8 and straight back 17 minutes later, the same 2025 3rd going the
    other way each time. They are genuinely separate transactions with distinct
    ids, so nothing upstream deduplicates them — but scoring both halves publishes
    two mirror-image ROBBERY verdicts and tells the league that two managers each
    robbed the other on the same afternoon. A reversed trade gets no verdict.
    """
    rev = {}
    for i, a in enumerate(trades):
        fa = asset_flows(a)
        if not fa:
            continue
        mirror = frozenset((k, to, frm) for k, frm, to in fa)
        for b in trades[i + 1:]:
            if b['created'] - a['created'] > REVERSAL_WINDOW_MS:
                break                      # trades are sorted by created
            if set(a.get('roster_ids') or []) != set(b.get('roster_ids') or []):
                continue
            if asset_flows(b) == mirror:
                rev[a['transaction_id']] = b['transaction_id']
                rev[b['transaction_id']] = a['transaction_id']
                break
    return rev


def build_trades(trades, drafts, engine, managers, curve, live_season):
    reversals = find_reversals(trades)
    out = []
    for t in trades:
        season, start_week = trade_start(t)
        sides = {rid: {'roster_id': rid,
                       'manager': managers.get(season, {}).get(rid, {}).get('name'),
                       'manager_uid': managers.get(season, {}).get(rid, {}).get('user_id'),
                       'players': [], 'picks': [], 'faab': 0,
                       'por': 0.0, 'projected_por': 0.0}
                 for rid in t.get('roster_ids', [])}

        for pid, rid in (t.get('adds') or {}).items():
            if rid not in sides:
                continue
            r = engine.por(pid, season, start_week)
            sides[rid]['players'].append({
                'player_id': str(pid),
                'name': engine.names.get(str(pid), '?'),
                'position': engine.pos.get(str(pid)),
                'por': (r or {}).get('por'),
                'por_signed': (r or {}).get('por_signed'),
                'raw': (r or {}).get('raw'),
                'weeks': (r or {}).get('weeks'),
                'scoreable': r is not None,
            })
            if r:
                sides[rid]['por'] += r['por']

        unsettled_pick = False
        for p in (t.get('draft_picks') or []):
            rid = p.get('owner_id')
            if rid not in sides:
                continue
            pk_season, rnd, orig = int(p['season']), p['round'], p['roster_id']
            made = resolve_pick(drafts, pk_season, rnd, orig)
            entry = {'season': pk_season, 'round': rnd, 'original_roster': orig,
                     'original_manager': managers.get(min(pk_season, live_season), {})
                                                 .get(orig, {}).get('name')}
            if made:
                pid = made.get('player_id')
                r = engine.por(pid, max(pk_season, season),
                               start_week if pk_season <= season else 1) if pid else None
                meta = made.get('metadata') or {}
                entry.update({
                    'resolved': True,
                    'pick_no': made['pick_no'], 'slot': made['draft_slot'],
                    'player_id': str(pid) if pid else None,
                    'player': f"{meta.get('first_name','')} {meta.get('last_name','')}".strip() or None,
                    'position': meta.get('position'),
                    'por': (r or {}).get('por'),
                    'por_signed': (r or {}).get('por_signed'),
                    'weeks': (r or {}).get('weeks'),
                })
                if r:
                    sides[rid]['por'] += r['por']
            else:
                # A pick for a draft that has not happened. It cannot have produced
                # anything, so it gets an EXPECTED value for context only and forces
                # the trade unsettled — see the maturity gate.
                unsettled_pick = True
                exp = expected_for_pick(curve, rnd=rnd)
                entry.update({'resolved': False, 'projected_por': exp})
                if exp:
                    sides[rid]['projected_por'] += exp
            sides[rid]['picks'].append(entry)

        for fb in (t.get('waiver_budget') or []):
            # Displayed, never scored — 2 trades in league history moved FAAB and
            # there is no defensible FAAB->points conversion at that sample size.
            if fb.get('receiver') in sides:
                sides[fb['receiver']]['faab'] += fb.get('amount', 0)

        for s in sides.values():
            s['por'] = round(s['por'], 1)
            s['projected_por'] = round(s['projected_por'], 1)

        weeks_elapsed = max((a.get('weeks') or 0)
                            for s in sides.values()
                            for a in list(s['players']) + list(s['picks'])) if sides else 0

        out.append({
            'transaction_id': t['transaction_id'],
            'created': t['created'],
            'date': time.strftime('%Y-%m-%d', time.localtime(t['created'] / 1000)),
            'season': season,
            'leg': t.get('leg'),
            'start_week': start_week,
            'sides': list(sides.values()),
            'has_unsettled_pick': unsettled_pick,
            'max_asset_weeks': weeks_elapsed,
            'reversed_by': reversals.get(t['transaction_id']),
        })
    return out


# ── verdicts + maturity ───────────────────────────────────────────────────────
#
# Both sets of numbers below were chosen against the real distribution of this
# league's 52 trades, not picked in the abstract. Absolute |margin| percentiles
# came out p25=0, p50=27, p75=93, p90=166, p100=346.

MATURITY_MIN_WEEKS = 8      # ~half a season of production from the busiest asset
VERDICT_EDGE = 25           # just under the median margin
VERDICT_CLEAR = 75          # ~p75
VERDICT_ROBBERY = 150       # ~p90
ROBBERY_RATIO = 3.0         # winner must also have >=3x the loser's return


def grade_trade(t):
    """Verdict for a trade, or a reason it is being withheld.

    The relative ROBBERY_RATIO gate exists so a blowout where BOTH sides got real
    value is a CLEAR WIN rather than a robbery — a 390-vs-107 trade is lopsided,
    but the loser still got a starter, and calling that a robbery devalues the
    label for the trades where someone genuinely got nothing.
    """
    if t.get('reversed_by'):
        return {'verdict': None, 'withheld': 'REVERSED',
                'note': 'Traded back within 48 hours — nothing was won.'}
    if t['has_unsettled_pick']:
        return {'verdict': None, 'withheld': 'TOO EARLY TO CALL',
                'note': 'Still holds a pick that has not been drafted yet.'}
    if t['max_asset_weeks'] < MATURITY_MIN_WEEKS:
        return {'verdict': None, 'withheld': 'TOO EARLY TO CALL',
                'note': f"Only {t['max_asset_weeks']} scored week(s) so far."}
    if len(t['sides']) != 2:
        return {'verdict': None, 'withheld': 'MULTI-TEAM',
                'note': 'More than two teams involved.'}

    a, b = t['sides']
    margin = round(abs(a['por'] - b['por']), 1)
    win, lose = (a, b) if a['por'] >= b['por'] else (b, a)
    ratio = win['por'] / max(lose['por'], 1.0)

    if margin >= VERDICT_ROBBERY and ratio >= ROBBERY_RATIO:
        v = 'ROBBERY'
    elif margin >= VERDICT_CLEAR:
        v = 'CLEAR WIN'
    elif margin >= VERDICT_EDGE:
        v = 'EDGE'
    else:
        v = 'DEAD EVEN'
    return {'verdict': v, 'withheld': None, 'margin': margin,
            'winner_roster': None if v == 'DEAD EVEN' else win['roster_id'],
            'winner': None if v == 'DEAD EVEN' else win['manager']}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report', action='store_true',
                    help='print distributions used to set thresholds')
    args = ap.parse_args()

    for p in (STATS_PATH, REPL_PATH):
        if not os.path.exists(p):
            print(f'ERROR: {p} is missing. Run generate_stats.py and '
                  f'scripts/build_replacement_levels.py first.')
            return 1

    print('Loading committed data files...')
    stats = json.load(open(STATS_PATH, encoding='utf-8'))
    repl = json.load(open(REPL_PATH, encoding='utf-8'))
    print(f"  stats-history: {sorted(k for k in stats if k!='generated')}")
    print(f"  replacement:   {sorted(repl['levels'])}  ranks {repl['ranks']}")

    gaps = coverage_gaps(stats, repl)
    if gaps:
        print('\nABORTED — replacement-levels.json does not cover every played week:')
        for g in gaps:
            print(f'  - {g}')
        print('\nEvery uncovered week is SILENTLY SKIPPED by Engine.por (base is None ->')
        print('continue), so this would have published a file where those weeks scored')
        print('zero for everyone, with no error anywhere. Run')
        print('  python scripts/build_replacement_levels.py')
        print('first, then re-run this. Nothing written.')
        return 1

    print('Fetching player database (~5 MB)...')
    pdb = fetch('/players/nfl')
    positions = {str(k): (v.get('position') or '') for k, v in pdb.items()}
    names = {str(k): (v.get('full_name')
                      or f"{v.get('first_name','')} {v.get('last_name','')}".strip())
             for k, v in pdb.items()}

    live_season = int(fetch('/state/nfl')['season'])
    print(f'Live season: {live_season}')

    league_ids = get_league_chain()
    print(f'League chain: {dict(sorted(league_ids.items()))}')
    managers = get_managers(league_ids)
    drafts = get_drafts(league_ids)
    trades = get_trades(league_ids)
    print(f'Trades: {len(trades)}')

    engine = Engine(stats, repl, positions, names)

    rookies = rookie_pick_rows(drafts, engine, managers)
    curve = build_pick_curve(rookies, live_season)
    factors = class_factors(rookies, live_season)
    print(f'Class strength factors: {factors}')
    # Each pick carries the expectation it should actually be judged against.
    for r in rookies:
        exp = expected_for_pick(curve, r['pick_no'], r['round'])
        r['expected_por'] = exp
        f = factors.get(r['season'])
        r['expected_por_class_adj'] = round(exp * f, 1) if (exp is not None and f) else exp
    print(f"Pick curve: {curve['n']} completed picks from classes {curve.get('classes')}")

    trade_rows = build_trades(trades, drafts, engine, managers, curve, live_season)
    for t in trade_rows:
        t['grade'] = grade_trade(t)

    out = {
        'thresholds': {
            'maturity_min_weeks': MATURITY_MIN_WEEKS,
            'edge': VERDICT_EDGE, 'clear': VERDICT_CLEAR,
            'robbery': VERDICT_ROBBERY, 'robbery_ratio': ROBBERY_RATIO,
        },
        'generated': time.strftime('%Y-%m-%d'),
        'live_season': live_season,
        'replacement_ranks': repl['ranks'],
        'rookie_draft_first_season': ROOKIE_DRAFT_FIRST_SEASON,
        'managers': {str(k): {str(rk): rv for rk, rv in v.items()}
                     for k, v in managers.items()},
        # Aggregate every leaderboard on manager_index keys (user_id), never on
        # display name — see build_manager_index for the two traps.
        'manager_index': build_manager_index(managers),
        'pick_curve': curve,
        'class_factors': factors,
        'draft_capital': build_draft_capital(rookies, live_season),
        'role_min_weeks': ROLE_MIN_WEEKS,
        'hit_por': HIT_POR,
        'trades': trade_rows,
        'rookie_picks': rookies,
    }

    if args.report:
        report(trade_rows, rookies, curve, out['draft_capital'], factors)

    if unchanged_but_for_stamp(OUT_PATH, out):
        print('')
        print('No change beyond the date stamp — leaving the file alone.')
        return 0

    raw = json.dumps(out, separators=(',', ':'))
    if args.dry_run:
        print(f'\n--dry-run: would write {len(raw)/1024:.1f} KB to {OUT_PATH}')
        return 0
    write_atomic(OUT_PATH, raw)
    print(f'\nWrote {OUT_PATH} — {len(raw)/1024:.1f} KB')
    return 0


def report(trade_rows, rookies, curve, capital=None, factors=None):
    print('\n' + '=' * 72)
    print('DISTRIBUTIONS — used to set the verdict and maturity thresholds')
    print('=' * 72)

    margins, totals = [], []
    for t in trade_rows:
        if len(t['sides']) != 2:
            continue
        a, b = t['sides']
        margins.append(abs(a['por'] - b['por']))
        totals.append(max(abs(a['por']), abs(b['por'])))
    margins.sort()
    print(f'\n2-side trades: {len(margins)}')
    if margins:
        qs = [0, 10, 25, 50, 75, 90, 100]
        print('  |margin| percentiles: ' + '  '.join(
            f'p{q}={margins[min(len(margins)-1, int(q/100*len(margins)))]:.0f}' for q in qs))

    wk = sorted(t['max_asset_weeks'] for t in trade_rows)
    print('  max_asset_weeks percentiles: ' + '  '.join(
        f'p{q}={wk[min(len(wk)-1,int(q/100*len(wk)))]}' for q in [0, 10, 25, 50, 75, 100]))
    print(f"  trades holding an undrafted pick: "
          f"{sum(1 for t in trade_rows if t['has_unsettled_pick'])}")
    print(f"  trades with 0 asset weeks: {sum(1 for t in trade_rows if not t['max_asset_weeks'])}")
    print(f"  reversed trades (traded back inside 48h): "
          f"{sum(1 for t in trade_rows if t.get('reversed_by'))}")

    graded = [t for t in trade_rows if t.get('grade', {}).get('verdict')]
    counts, withheld = {}, {}
    for t in trade_rows:
        g = t.get('grade', {})
        if g.get('verdict'):
            counts[g['verdict']] = counts.get(g['verdict'], 0) + 1
        else:
            withheld[g.get('withheld')] = withheld.get(g.get('withheld'), 0) + 1
    print(f'\n  graded {len(graded)} of {len(trade_rows)}')
    print(f'    verdicts: {counts}')
    print(f'    withheld: {withheld}')
    print('\n  biggest graded margins:')
    for t in sorted(graded, key=lambda x: -x['grade']['margin'])[:6]:
        g = t['grade']
        print(f"    {t['date']}  {g['verdict']:<9} margin {g['margin']:6.1f}  "
              f"winner {g['winner']}")

    print(f"\nPick curve ({curve['n']} picks, classes {curve.get('classes')}):")
    bp = curve['by_pick']
    for pk in sorted(bp, key=lambda x: int(x))[:14]:
        print(f'   pick {pk:>3}  expected rookie-year PoR {bp[pk]:7.1f}')
    print(f'  by round: {curve["by_round"]}')

    played = [r for r in rookies if r['rookie_weeks']]
    print(f'\nRookie picks that actually played a scoreable week: '
          f'{len(played)} of {len(rookies)}')
    neg = [r for r in played if (r.get('rookie_por_signed') or 0) < 0]
    print(f'  of those, negative before the zero floor: {len(neg)}')
    best = sorted(played, key=lambda r: -(r['rookie_por'] or 0))[:8]
    print('  best rookie years:')
    for r in best:
        print(f"   {r['season']} {r['round']}.{r['slot']:<2} {str(r['player'])[:22]:22s} "
              f"{str(r['position']):3s} {r['rookie_por']:7.1f}  ({r['drafted_by']})")

    if factors:
        print(f'\nClass strength (mean rookie PoR vs the average class): {factors}')
    if capital:
        print('\nDRAFT CAPITAL — what a pick at each band actually buys')
        print(f"  {'band':11s} {'n':>3} {'hit%':>6} {'medPoR':>8} {'usage':>7} "
              f"{'wksUsed':>8} {'neverUsed':>10} {'gotRole':>8} {'PoR|role':>9}")
        for b in capital:
            up = f"{b['avg_usage_pct']*100:.0f}%" if b['avg_usage_pct'] is not None else '-'
            print(f"  {b['band']:11s} {b['n']:>3} {b['hit_rate']*100:5.0f}% "
                  f"{b['median_por']:8.1f} {up:>7} {b['avg_weeks_used']:8.1f} "
                  f"{b['never_used']:>5}/{b['n']:<4} {b['got_role']:>3}/{b['n']:<4} "
                  f"{str(b['avg_por_given_role']):>9}")
        print('  usage = percentile among same-position players that season; raw')
        print('  touches are NOT comparable across positions (QB attempts vs RB carries).')


if __name__ == '__main__':
    sys.exit(main())
