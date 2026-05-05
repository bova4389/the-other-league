# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Workspace Structure

Two independent projects live here. Each has its own detailed CLAUDE.md — read it before working on that project.

| Project | Path | CLAUDE.md |
|---------|------|-----------|
| Majors Golf Pool | `Majors Golf Pool/` | [`Majors Golf Pool/CLAUDE.md`](Majors Golf Pool/CLAUDE.md) |
| Sleeper Fantasy Football | `Sleeper FF/The Other League/` | [`Sleeper FF/The Other League/CLAUDE.md`](Sleeper FF/The Other League/CLAUDE.md) |

## Shared Conventions

Both projects are **static HTML / Vanilla JS** sites hosted on GitHub Pages. No npm, no Node, no build step. All dependencies load from CDN `<script>` tags. Never introduce a build tool.

## Git Setup

These are **two separate git repositories**:

- `Majors Golf Pool/` has its own `.git` and remote: `https://github.com/bova4389/the-majors-golf.git` — commit and push from inside that directory.
- The outer workspace repo tracks everything else (Sleeper FF, root files). Remote: `https://github.com/bova4389/the-other-league`

Never `git add Majors Golf Pool/` from the outer repo — it will be treated as a submodule and its files will not be tracked.

## Project States (as of May 2026)

**Majors Golf Pool** — PGA Championship 2026 is the next live tournament (ESPN event ID `401811947`, starts May 11). All four 2025 major scoreboards are fully hardcoded. Masters 2025 and PGA Championship 2025 pool standings (Total, R1–R4, Payouts) are fully hardcoded in `standings.js`. U.S. Open 2025 and The Open 2025 scoreboards are hardcoded but their pool standings are not yet entered. Each scoreboard function resets its table state on every year switch so the 2026 tab always shows "Scoreboard not yet available."

**Sleeper FF / The Other League** — Active development project. The working file is `the-other-league-FINAL.html` (3200+ lines); `index.html` is an 8-line stub. Full feature set for roster management, trade evaluation (with live KTC values), draft picks, and standings. See its CLAUDE.md for the complete function and data reference.
