#!/usr/bin/env python3
"""Fetch KTC dynasty values (SF+PPR+TEP) and write ktc-values.json to repo root."""

import json
import sys
import time
import requests

URL = "https://keeptradecut.com/dynasty-rankings?format=1&tep=1"
OUT = "ktc-values.json"


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


def main():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    print(f"Fetching {URL} ...")
    try:
        r = requests.get(URL, headers=headers, timeout=20)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"ERROR: request failed — {e}", file=sys.stderr)
        sys.exit(1)

    raw = bracket_extract(r.text, "var playersArray = ")
    if not raw:
        print("ERROR: playersArray not found in KTC HTML", file=sys.stderr)
        sys.exit(1)

    try:
        players = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERROR: failed to parse playersArray JSON — {e}", file=sys.stderr)
        sys.exit(1)

    values = {}
    for p in players:
        sf = (p.get("superflexValues") or {}).get("tep")
        if not sf or sf.get("value") is None:
            continue
        values[p["playerName"]] = {
            "value": sf["value"],
            "position": p.get("position", ""),
            "nflTeam": p.get("team", "FA"),
            "age": p.get("age", 0),
            "rank": sf.get("rank", 999),
            "trend": (p.get("superflexValues") or {}).get("overallTrend", 0),
        }

    if len(values) < 200:
        print(f"ERROR: only {len(values)} players parsed (expected 200+) — aborting", file=sys.stderr)
        sys.exit(1)

    out = {"values": values, "ts": int(time.time() * 1000)}
    with open(OUT, "w") as f:
        json.dump(out, f, separators=(",", ":"))

    print(f"✓ Wrote {len(values)} player values to {OUT}")


if __name__ == "__main__":
    main()
