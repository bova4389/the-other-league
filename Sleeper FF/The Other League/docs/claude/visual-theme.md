# Visual Theme (Arcade Neon) — The Other League reference

Moved verbatim out of `CLAUDE.md` on 2026-11-11 so it loads only when needed. A cross-reference to another section may now point to a different `docs/claude/` file; grep the folder for the heading.

## VISUAL THEME — Arcade Neon (NFL Blitz)

Aesthetic: late-90s NFL Blitz / arcade-neon sports broadcast — glossy electric-teal + hot-magenta + neon-purple on near-black, pulled directly from the TOL logo. Premium / "legit" (ESPN/Sleeper-grade), **mobile-first**. Dark is the default theme; light mode is fully supported.

**HOW THE REDESIGN IS STRUCTURED — read this before editing styles:**
- The redesign is a stack of **appended CSS layers at the very END of `<style>`**, each opened by a banner comment: `ARCADE NEON REDESIGN`, then one block per tab (`CAREERS TAB — Arcade Neon polish`, `SCORES TAB…`, `RIVALRIES…`, `TRADE EVALUATOR…`, `DRAFT · STATS · TRANSACTIONS · LEAGUE…`, `HOME TAB…`, `LIGHT MODE…`), then the Phase 6 `.gr-*` block and the Phase 1 `CAREERS TAB · RECORD BOOK + HALL OF FAME & SHAME` block. They cascade over the original CSS above them — do not delete them.
- The Phase 1 layer styles `.hof-card` as an extension of the existing `.fun-card` (which had been defined but unused), with `.shame` recoloring to `--accent3`. Verified at 280 / 375 / 1280px in both themes: 1 / 2 / 5 columns, zero page or card overflow, and no hardcoded hex — light mode picks up `#0E9C92` / `#D6258F` automatically.
- Styling is **by class name and CSS variable**, never by editing individual elements. New content rendered by the existing JS inherits the look automatically **as long as it reuses the existing class names**.
- **To keep the design when adding things:** (1) reuse existing classes (`.r-card`, `.chip`, `.cp`, `.f-pill`, `.match-card`, `.dtbl`/`.career-tbl`, `.s-pill`, `.ic`, `.note`, …); (2) use the palette **variables**, never hardcode hex; (3) put any NEW css at the very bottom; (4) keep the banner-commented blocks.

### Color Palette — Dark (default)

| Role | Variable | Value |
|------|----------|-------|
| Primary accent (teal) | `--accent` | `#21F5E4` |
| Secondary accent (purple) | `--accent2` | `#9A55FF` |
| Tertiary accent (magenta) | `--accent3` | `#FF3DBE` |
| Background | `--bg` | `#06060C` (body uses a purple radial-glow gradient) |
| Panel surface | `--surface` | `#0B0918` |
| Card background | `--card` | `#100C22` (cards use a `#120D26 → #0C0920` gradient) |
| Borders | `--border` | `#27194E` (card borders often `#2A1C54`) |
| Body text | `--text` | `#FFFFFF` |
| Secondary text | `--text2` | `#D9D2F2` |
| Muted text | `--muted` | `#928AB8` |
| Position QB / RB / WR / TE | `--pos-*` | `#B98CFF` / `#3DF0A6` / `#5BB8FF` / `#FFB24A` |

### Color Palette — Light (toggle)
`--accent #0E9C92` · `--accent2 #7A33E0` · `--accent3 #D6258F` · `--bg #EEF0F5` · `--surface`/`--card #FFFFFF` · `--border #D6DAE6` · `--text #11151F` · `--text2 #3A4252` · `--muted #6A7384`. Light-mode surface fixes live in the `LIGHT MODE` block — any new **dark-only** rule (a `rgba(255,255,255,…)` background/border, or a hardcoded dark hex) must be paired with a `[data-theme="light"]` override there so the toggle stays clean.

### Typography System
Three-font system (Google Fonts):

| Use | Font | Notes |
|-----|------|-------|
| Display — titles, team names, stat values, countdown | **Saira Condensed** | Athletic condensed; **italic** on the marquee bits (`.sec-title`, `.rch-team`, `.champ-name`, `.cd-num`, `.hdr-league-name`) for the Blitz slant + teal neon glow in dark. **Replaced Bebas Neue everywhere.** |
| Body — chips, table cells, buttons, pills, labels | **DM Sans** | Clean, legible. Player-name chips are DM Sans (not mono). |
| Technical — timestamps, KTC raw values | **DM Mono** | Sparingly; never for primary content. |

### Nav (type-only)
The icon nav is **type-only** — emoji icons are hidden via `.itab-icon{display:none}` (markup untouched; the refresh ↺ still shows). The active tab gets a glowing teal underline (`.icon-tab.active::after`) + glowing label. Mobile: wraps to 2 rows of 5, 46px touch targets, clean per-cell teal underline.

### Accent usage
- **Teal** — active nav, primary buttons, winner rails, leading scores, links, key numbers.
- **Magenta/pink** — table headers, section subtitles, position-group labels (`.pl`), rivalry cards/totals, KTC owner column, H2H strips.
- **Purple** — countdown separators, secondary borders, the `is-you` roster card.
- **Gold** (`#FFD25A`) — champion card frame + trophy, "CHAMP" badges.

### Glow System
Neon glows are scoped to `[data-theme="dark"]` inside the appended blocks. Pattern: `text-shadow` / `box-shadow: 0 0 Xpx rgba(R,G,B,.Y)`. Keep subtle.

### Mobile-first
Phones are the primary target. Wide tables (`.career-tbl` / `.dtbl` / `.ktc-tbl`) scroll **inside their own container** with a sticky owner column so the page + nav stay put; card grids collapse to one column; stat strips are swipeable; the body background drops `fixed` attachment on mobile (iOS-safe). Each tab block ends with a `@media(max-width:680px)` section — keep new mobile rules there.

### Team-name shorthand
**`shortName()` does not exist — use `abbrev(name)`.** This entry described a
`shortName()` "defined next to `abbrev()`" for years; there are **zero** occurrences of it
in `index.html`, and calling it threw a live `ReferenceError` the first time Phase 12's chip
bar trusted this line. `abbrev(name)` is the real function and returns first-initial +
last name ("Matt Bova" → "M. Bova"). Team filter chips (Rosters, Draft, Transactions, Stats,
Trade Eval, Trade ROI) label with `abbrev(t(uid).name)` — the **real** name, not the Sleeper
display handle. Use it for any new team-filter UI, and fall back to the stored handle only
for a manager who has left the league and is no longer in `TEAMS`.

### Logo Files (wired in)
- **`TOL Banner Logo.jpg`** - the sticky header wordmark (84px tall; 56px mobile). 1998x648, ~3.08:1,
  500 KB. **It is a JPEG, not a PNG** - it arrived named `.png` and was renamed to match its actual
  bytes; browsers sniff content type either way, but the wrong extension is a trap for the next
  person. Being a JPEG it has **no alpha**: the black background is baked into the artwork.
- `TOL Large Logo.png` - home hero only now (max 420px; 260px mobile). Deliberately still the
  shield: a wide banner suits a header strip, a square mark suits a centered hero.
- `TOL Abbreviated Icon.png` - favicon + iOS add-to-homescreen icon
- `TOL Small Logo.png` - available if needed

**Glow treatment differs by mark shape, and that is the point.** The shield is a transparent PNG,
so `drop-shadow()` traces its silhouette. The banner is an opaque rectangle, so the same filters
trace its bounding box and read as a smeared rectangular halo. The `HEADER BANNER` CSS layer
therefore drops both `drop-shadow()` filters and the `.hdr-logo-link::before` radial glow, and
gives the banner rounded corners plus a single soft `box-shadow` in each theme. **If a
transparent-background banner ever replaces this file, revisit that layer** - `drop-shadow` would
be the right call again.

Banner size was left at 500 KB rather than downscaled: neither Pillow nor Node is installed on
this machine, and 500 KB is already 3-6x lighter than the three existing logo PNGs (1.5-3 MB
each). Worth revisiting if image tooling ever lands - it renders at 259px wide, so a 2000px source
is far more than it needs.

### PWA / Mobile meta
```html
<link rel="icon" type="image/png" href="TOL Abbreviated Icon.png">
<link rel="apple-touch-icon" href="TOL Abbreviated Icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="The Other League">
<meta name="theme-color" content="#06060C">
```

---
