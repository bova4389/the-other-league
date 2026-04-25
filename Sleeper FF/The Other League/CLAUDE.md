# CLAUDE.md — The Other League Dynasty Dashboard

## WHAT THIS PROJECT IS

A personal fantasy football dashboard for "The Other League" — a 12-team dynasty league on the Sleeper platform. The site pulls live data from the Sleeper public API and the Anthropic API to display rosters, league history, draft picks, scoring rules, rivalries, and an AI analysis layer.

**Owner:** Matt Bova (commissioner). Built for personal use during development; eventually shared with league mates.

---

## PROJECT STRUCTURE

This is a **static HTML/JavaScript project** — no framework, no build step, no package manager. All files are plain `.html` with embedded CSS and JavaScript.

```
the-other-league/
├── CLAUDE.md                          — you are here
├── index.html                         — main unified dashboard (target state)
├── the-other-league-FINAL.html        — current working version (most complete)
├── the-other-league-Claude-html.html  — earlier version (reference only)
├── the-other-league-context.md        — master league context document
└── chunks/                            — prior standalone chunk files (reference)
    ├── chunk1-history.html
    ├── chunk2-rosters.html
    └── chunk3-draft.html
```

**Current state:** `the-other-league-FINAL.html` is the working file. It combines rosters, league info, scoring, rivalries, draft, traded picks, and an embedded "Ask Claude" AI tab into one file.

**Deployment:** GitHub Pages (static hosting). No server, no backend. All API calls happen client-side from the browser.

---

## EXTERNAL APIS

### Sleeper API (no auth required)
- Base: `https://api.sleeper.app/v1`
- League ID: `1316225642072662016`
- Key endpoints:
  - `/league/{lid}` — league info
  - `/league/{lid}/rosters` — all 12 rosters
  - `/league/{lid}/traded_picks` — pick trade log
  - `/players/nfl` — full player database (~5MB, slow)
- CORS note: Direct browser fetch may fail. Fallback proxies in order: `corsproxy.io`, `api.allorigins.win`

### Anthropic API
- Endpoint: `https://api.anthropic.com/v1/messages`
- Model: `claude-sonnet-4-20250514`
- Used for: the "Ask Claude" tab — AI analysis chat with full league context injected
- No API key handling needed in code (handled externally)

---

## HOW TO WORK ON THIS PROJECT

### Always plan before acting
Before making any changes, present a written plan of what you intend to do and wait for approval. Do not edit files speculatively. Token efficiency matters — avoid redundant reads and unnecessary rewrites.

### Verify in browser
The only way to test is to open the HTML file in a browser. There is no local dev server, no test suite, and no linter. After changes, confirm the file opens without console errors and the relevant feature works visually.

### Comment all code in plain English
Every meaningful block of code — functions, event handlers, API calls, render loops — should have a short comment above it in plain English explaining what it does. Matt is not an engineer; the code should be readable by a non-technical person.

Example:
```javascript
// Fetch all rosters from Sleeper and render player chips for each team
async function buildRosters() { ... }
```

### Keep everything in one file
Do not split CSS, JS, or HTML into separate files. GitHub Pages serves static files and the project is intentionally self-contained. All styles go in `<style>`, all scripts go in `<script>`, inside the single `.html` file.

---

## KEY DESIGN DECISIONS (don't change without asking)

- **Non-PPR scoring** with TE premium (+0.5/rec) and distance bonuses — this affects all AI analysis context
- **Dark/light theme toggle** — persists via `localStorage`
- **LocalStorage caching** — Sleeper data cached for 6 hours to reduce API calls; cache key is `tol_cache_v2`
- **CORS fallback chain** — always try direct fetch first, then two proxy fallbacks
- **Roster chip colors**: green = starter, blue = taxi squad, orange = IR/reserve

---

## LEAGUE CONTEXT SUMMARY (for AI features)

- 12 teams, dynasty format, ~Year 4
- Commissioner/user: Matt Bova — team "Show Me Your Penix" (mid-tier, between contender and rebuild)
- 2025 Champion: Jake Blackwell ("Nacua Matata") — gets pick 1.12
- 2025 Consolation: Nick Merkel ("Breeces Peanut ButterCups") — gets pick 1.13
- Contenders: Chris Bova, Jake Bogardus
- Active traders (best trade partners): Chris Merkel, Nick Merkel
- 2027 rule change already voted in: 1 WRRB_FLEX → WR/RB/TE FLEX (increases TE value significantly)
- Full context available in: `the-other-league-context.md`

---

## PLANNED FEATURES (not yet built)

See `the-other-league-context.md` — "Dashboard Build Status" section for full backlog. Key items:

- Career earnings tracker across all seasons
- Post-playoff final standings (full bracket, not just regular season)
- Matchup history and schedule viewer
- Expanded AI context (pass live roster data into Claude calls)

---

## WHAT NOT TO DO

- Do not introduce React, Vue, npm, or any build tool without explicit discussion first
- Do not break the single-file structure
- Do not remove the CORS fallback chain from API calls
- Do not use `localStorage` for anything sensitive (API keys, personal data)
- Do not rewrite large sections of working code to fix a small issue — patch surgically
