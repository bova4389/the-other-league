#!/usr/bin/env python3
"""Fetch KTC dynasty values (SF+PPR+TEP) and write ktc-values.json to the TOL folder.

Two passes:
  1. TOP-500 — keeptradecut.com/dynasty-rankings embeds `var playersArray`,
     which is capped at exactly 500 players no matter what page/filter params
     you pass (verified 2026-08-20: ?page=0/1/2 all return the same 500, and
     the trade-calculator page's arrays are capped the same way). There is no
     public JSON API.
  2. DEEP LOOKUP — anyone this league actually rosters who missed that cut.
     KTC still tracks them, just below rank 500 (Zach Ertz was rank 475 on the
     TEP scale, Austin Ekeler 761), and each has an individual player page with
     a full `var player = {...}` blob. Slugs come from sitemap-dynasty.xml.

Pass 2 exists because pass 1's cutoff silently mis-graded rosters: an unmatched
player is EXCLUDED from his team's total rather than counted, so the managers
hoarding washed veterans were getting a free pass on the Bench Dead Weight flag
instead of being punished for it. See CLAUDE.md Phase 6.
"""

import json
import os
import re
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

RANKINGS_URL = "https://keeptradecut.com/dynasty-rankings?format=1&tep=1"
SITEMAP_URL = "https://keeptradecut.com/sitemap-dynasty.xml"
PLAYER_URL = "https://keeptradecut.com/dynasty-rankings/players/{slug}"

SLEEPER = "https://api.sleeper.app/v1"
LEAGUE_ID = "1316225642072662016"  # must match LID in index.html

# Don't hammer KTC if something upstream goes wrong and every player suddenly
# looks unmatched — bail out loudly instead of firing 300 requests.
MAX_DEEP_LOOKUPS = 40
DEEP_LOOKUP_DELAY = 0.6

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(_SCRIPT_DIR, "..", "ktc-values.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Mirrors KTC_NAME_ALIASES in index.html — keep the two in sync. Normalized
# Sleeper name -> exact KTC playerName.
ALIASES = {
    "chig okonkwo": "Chigoziem Okonkwo",
    "kenny gainwell": "Kenneth Gainwell",
}


def bracket_extract(text, marker):
    """Extract a JSON array/object starting after `marker` using bracket counting."""
    start = text.find(marker)
    if start == -1:
        return None
    idx = start + len(marker)
    depth = 0
    for i in range(idx, len(text)):
        c = text[i]
        if c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1
            if depth == 0:
                return text[idx : i + 1]
    return None


def norm(n):
    """Match index.html's normalizeName(): lowercase, drop apostrophes/periods."""
    return re.sub(r"\s+", " ", re.sub(r"['‘’ʼ`.]", "", n.lower())).strip()


def strip_suffix(n):
    return re.sub(r"\s+(Jr\.?|Sr\.?|IV|III|II|V)$", "", n, flags=re.I).strip()


def squash(n):
    """Aggressive key for slug matching — letters and digits only.

    Slugs flatten punctuation in a way normalizeName() does not: KTC's slug for
    De'Von Achane is `de-von-achane-1398`, which normalizes to "de von achane"
    while the player name normalizes to "devon achane". Squashing both to
    "devonachane" is the only thing that lines them up.
    """
    return re.sub(r"[^a-z0-9]", "", n.lower())


def sf_value(entry):
    """SUPERFLEX + TE-premium value, matching the ?format=1&tep=1 rankings view."""
    sf = entry.get("superflexValues") or {}
    tep = sf.get("tep") or {}
    if tep.get("value") is not None:
        return tep.get("value"), tep.get("rank", 999)
    if sf.get("value") is not None:
        return sf.get("value"), sf.get("rank", 999)
    return None, None


def fetch_top_500():
    print("[1/2] Fetching %s ..." % RANKINGS_URL)
    r = requests.get(RANKINGS_URL, headers=HEADERS, timeout=20)
    r.raise_for_status()
    raw = bracket_extract(r.text, "var playersArray = ")
    if not raw:
        print("ERROR: playersArray not found in KTC HTML", file=sys.stderr)
        sys.exit(1)
    players = json.loads(raw)

    values = {}
    for p in players:
        val, rank = sf_value(p)
        if val is None:
            continue
        values[p["playerName"]] = {
            "value": val,
            "position": p.get("position", ""),
            "nflTeam": p.get("team", "FA"),
            "age": p.get("age", 0),
            "rank": rank,
            "trend": (p.get("superflexValues") or {}).get("overallTrend", 0),
        }
    print("      %d players from the ranked top-500 array" % len(values))
    return values


def rostered_players():
    """Every non-K/DEF player on a TOL roster, as {name: position}."""
    rosters = requests.get(SLEEPER + "/league/" + LEAGUE_ID + "/rosters", timeout=30).json()
    pool = requests.get(SLEEPER + "/players/nfl", timeout=90).json()
    out = {}
    for r in rosters:
        for pid in r.get("players") or []:
            p = pool.get(str(pid))
            if not p or not p.get("position") or p["position"] in ("K", "DEF"):
                continue
            name = p.get("full_name") or (
                (p.get("first_name") or "") + " " + (p.get("last_name") or "")
            ).strip()
            if name:
                out[name] = p["position"]
    return out


def find_unmatched(values, rostered):
    """Rostered names with no alias/exact/normalized/suffix-stripped hit — mirrors getKTCEntryFuzzy()."""
    keys = [k for k in values if not re.match(r"^\d{4}", k)]
    by_norm = {norm(k): k for k in keys}
    by_stripped = {norm(strip_suffix(k)): k for k in keys}
    missing = []
    for name in rostered:
        n = norm(name)
        if ALIASES.get(n) in values:
            continue
        if name in values or n in by_norm or norm(strip_suffix(name)) in by_stripped:
            continue
        missing.append(name)
    return sorted(missing)


def slug_index():
    """squashed name -> slug, from KTC's dynasty sitemap."""
    r = requests.get(SITEMAP_URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    idx = {}
    for url in re.findall(r"<loc>([^<]+/players/[^<]+)</loc>", r.text):
        slug = url.rsplit("/", 1)[1]
        base = re.sub(r"-\d+$", "", slug)  # drop the trailing playerID
        idx.setdefault(squash(base), slug)
    return idx


def fetch_player(slug):
    r = requests.get(PLAYER_URL.format(slug=slug), headers=HEADERS, timeout=25)
    if r.status_code != 200:
        return None
    raw = bracket_extract(r.text, "var player = ")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def deep_lookup(values, missing):
    """Resolve below-the-cut players one page at a time. Returns names still unresolved."""
    if not missing:
        print("[2/2] Every rostered player matched in the top 500 — no deep lookup needed")
        return []

    print("[2/2] %d rostered player(s) missed the top-500 cut — deep lookup" % len(missing))
    if len(missing) > MAX_DEEP_LOOKUPS:
        print(
            "ERROR: %d unmatched exceeds MAX_DEEP_LOOKUPS (%d). That is far more than the "
            "handful of fading veterans this pass is for — something upstream is broken "
            "(name format change?). Refusing to mass-request KTC."
            % (len(missing), MAX_DEEP_LOOKUPS),
            file=sys.stderr,
        )
        sys.exit(1)

    idx = slug_index()
    unresolved = []
    for name in missing:
        slug = idx.get(squash(name)) or idx.get(squash(strip_suffix(name)))
        if not slug:
            print("      . %s: not in KTC's pool at all (no player page) — leaving unmatched" % name)
            unresolved.append(name)
            continue
        entry = fetch_player(slug)
        time.sleep(DEEP_LOOKUP_DELAY)
        if not entry:
            print("      . %s: player page %s unreadable — leaving unmatched" % (name, slug))
            unresolved.append(name)
            continue
        val, rank = sf_value(entry)
        if val is None:
            print("      . %s: page has no superflex value — leaving unmatched" % name)
            unresolved.append(name)
            continue
        values[entry["playerName"]] = {
            "value": val,
            "position": entry.get("position", ""),
            "nflTeam": entry.get("team", "FA"),
            "age": entry.get("age", 0),
            "rank": rank,
            "trend": (entry.get("superflexValues") or {}).get("overallTrend", 0),
            "deep": True,
        }
        print("      + %s: %s (rank %s)" % (entry["playerName"], val, rank))
    return unresolved


def main():
    try:
        values = fetch_top_500()
    except requests.RequestException as e:
        print("ERROR: rankings request failed — %s" % e, file=sys.stderr)
        sys.exit(1)

    if len(values) < 200:
        print("ERROR: only %d players parsed (expected 200+) — aborting" % len(values), file=sys.stderr)
        sys.exit(1)

    # The deep pass is best-effort: a Sleeper hiccup or a KTC layout change
    # must never cost us the top-500 values we already have in hand.
    unresolved = []
    try:
        unresolved = deep_lookup(values, find_unmatched(values, rostered_players()))
    except SystemExit:
        raise
    except Exception as e:
        print("WARN: deep lookup failed (%s) — writing top-500 values only" % e, file=sys.stderr)

    out = {"values": values, "ts": int(time.time() * 1000), "unresolved": unresolved}
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))

    deep = sum(1 for v in values.values() if v.get("deep"))
    print("\nWrote %d player values (%d via deep lookup) to %s" % (len(values), deep, OUT))
    if unresolved:
        print("  %d genuinely untracked by KTC: %s" % (len(unresolved), ", ".join(unresolved)))


if __name__ == "__main__":
    main()
