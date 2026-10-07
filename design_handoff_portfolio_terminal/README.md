# Handoff: Portfolio Terminal

## Overview

A single-user, personal portfolio tool for a Trading212 GBP account of ~12 equity holdings plus cash. It exists to separate two questions that a broker app mixes together:

1. **Did something happen to this company overnight that I can't explain?** (Book — actual move vs model-expected move, residual, z-score)
2. **Is the macro backdrop for and against my positions, and am I over-concentrated?** (Macro — factor exposure per holding; Book — weighting by index)

Six surfaces: Dashboard, Book, Analysis (per-stock), Macro, Sizer, Settings. All read-only except the Sizer inputs and the theme toggle. There is no multi-user concept, no auth beyond whatever the deployment needs, and no writes back to the broker.

## About the design files

The files in `design/` are **design references created in HTML** — a working prototype of the intended look, layout and behaviour. They are **not production code to copy**. `Portfolio Terminal.dc.html` runs on a bespoke prototyping runtime (`support.js`) that will not exist in the target codebase; treat it as an interactive spec you can open in a browser and click through.

The task is to **rebuild these screens in the target environment**. No codebase exists yet, so the implementer chooses the stack. See "Recommended stack" below for the constraints that choice has to satisfy.

To view the prototype: open `design/Portfolio Terminal.dc.html` in a browser, with both files in the same folder. Nav is in the header; rows with a chevron expand.

## Fidelity

**High-fidelity.** Colors, typography, spacing, grid columns, hover states and copy are all final and specified below. Recreate them faithfully — the density is deliberate and is the main design decision in the product. Two qualifications:

- **All numbers are placeholder**, including the index levels, the macro factor scores, the z-scores and the BROS analysis figures. Do not treat any value as ground truth; they exist to show format, alignment and magnitude.
- **The Sizer screen is roughed in** relative to the other five. Treat it as lofi and defer it (see "Build order").

## Recommended stack, and the Streamlit question

Streamlit can host this, but it will fight you on the parts that matter most. The design leans on dense CSS grids with per-column alignment, hover-reveal row drawers, inline SVG sparklines and small custom bar/band graphics. In Streamlit each of those becomes a custom HTML component or an `st.markdown(unsafe_allow_html=True)` block, at which point you are writing the HTML anyway without the layout control. Its rerun-on-interaction model also makes expand/collapse rows feel wrong.

The recommendation:

- **Backend: Python.** The expected-move regression belongs in pandas/statsmodels, and the broker and price ingestion is a set of scheduled jobs. FastAPI serving JSON is enough.
- **Frontend: a small React + Vite SPA**, plain CSS custom properties (the token set below maps 1:1). No component library needed — nearly every element here is a styled `div` in a grid, and a UI kit would have to be fought to reach this density.
- **Deploy:** one small box or container. Postgres for the daily bars, or SQLite if you would rather not run a database.

If you want the fastest possible path to something usable and are willing to lose the layout precision, Streamlit for **Book only** is a defensible v1 — a dataframe with conditional formatting covers most of that screen's value. Expect to rebuild it when you want the rest.

## Build order

Phased deliberately, because two of the six screens depend on judgement inputs that don't exist yet.

1. **Data ingestion first, before any UI.** Daily bar per holding and per macro factor, stored permanently. Custom factor series can't be backfilled cheaply, so start capturing on day one.
2. **Book.** Needs only positions, prices and FX. Index weighting is a hand-maintained ticker→index map. Ship without the flag column if the model isn't ready — the weighting panel and day moves stand alone.
3. **Dashboard.** Mostly aggregation of Book, plus index levels and a calendar feed.
4. **Macro** — only after several weeks of using Book, when it's clear which factors matter. The factor→holding effect scores are hand-authored judgement; guessing them now bakes in false precision.
5. **Analysis** — needs the parsed-analysis pipeline (notes → structured EPS scenarios). Highest effort, lowest urgency.
6. **Sizer** — last, and redesign before building.

## The expected-move model

This is the one genuinely hard piece, and the flag column on Book plus everything on Macro rests on it. Specified here so it can be built independently of the UI.

**Model.** For each holding, per day:

```
expected_return = β_index · r_index + Σ_f (β_f · r_f)
residual        = actual_return − expected_return
z               = residual / rolling_stdev(residual)
```

- `r_index` — daily return of the holding's primary benchmark (same ticker→index map as the Book weighting panel).
- `r_f` — daily return of each macro factor series (four factors, below).
- Betas fit by OLS on daily returns over the lookback window; re-derived on a schedule, never stored as truth, so a bad fit is always fixable.

**Parameters.**

| Parameter | Value | Note |
|---|---|---|
| Lookback | 250 trading days | Responsiveness vs accuracy; 120d is the alternative |
| Minimum history | 60 days | Below this, show no expected move at all rather than a bad one |
| Residual stdev window | Rolling, same as lookback | |
| Flag threshold | \|z\| ≥ 2.0 | Surfaced as "unexplained" |
| Factor count | 4, hard ceiling | More regressors on daily data with this window overfits; betas start drifting and residuals stop meaning anything |

**Factors** (as in the prototype): petrol at the pump (US retail gasoline), coffee (arabica), wages, rates. Each needs a daily series.

**Earnings-day suppression — required, not optional.** A regression on macro inputs cannot see a results release, so on earnings days the model will flag nearly everything. Either suppress flags on known earnings dates or label them as a distinct category ("earnings", not "unexplained"). Without this the flag list is noise four times a year and the feature loses trust immediately.

**Known limitation to surface in the UI:** holdings whose business changed inside the lookback window (in the sample book, BROS and CAVA) will have unstable betas. Showing the fit window and an R² per holding somewhere in Settings is cheap and worth it.

## Design tokens

Two themes, toggled from the header, persisted per user. Dark is the default.

### Color — dark (default)

| Token | Hex | Use |
|---|---|---|
| `--bg` | `#191d23` | Page background |
| `--panel` | `#212630` | Card/section background |
| `--panel2` | `#2a303a` | Table header, row drawer, inset bar track |
| `--line` | `#353c47` | Standard 1px border, row separator |
| `--line2` | `#48505d` | Stronger border (buttons, segmented controls, limit line) |
| `--ink` | `#f0f2f6` | Primary text, key figures |
| `--ink2` | `#aeb7c3` | Secondary text, labels |
| `--ink3` | `#848d9a` | Tertiary — uppercase micro-labels, captions, units |
| `--accent` | `#e6ae48` | Amber. Active nav, flags, primary series, "now" markers |
| `--accentSoft` | `rgba(230,174,72,.15)` | Active nav background, callout fill |
| `--up` | `#68c395` | Positive |
| `--down` | `#e57f76` | Negative |
| `--bandLow` | `rgba(140,152,168,.22)` | Scenario band fill |
| `--bandHigh` | `rgba(104,195,149,.18)` | Upper band fill |
| `--shadow` | `0 1px 0 rgba(255,255,255,.04) inset` | |

### Color — light

| Token | Hex |
|---|---|
| `--bg` | `#f6f5f2` |
| `--panel` | `#ffffff` |
| `--panel2` | `#f1f0ec` |
| `--line` | `#e3e1da` |
| `--line2` | `#cdcac1` |
| `--ink` | `#15181c` |
| `--ink2` | `#5b616b` |
| `--ink3` | `#8a9099` |
| `--accent` | `#9a6608` |
| `--accentSoft` | `rgba(154,102,8,.10)` |
| `--up` | `#2f7d57` |
| `--down` | `#b3423f` |
| `--bandLow` | `rgba(90,100,115,.14)` |
| `--bandHigh` | `rgba(47,125,87,.14)` |
| `--shadow` | `0 1px 2px rgba(20,22,26,.05)` |

No color outside this set. Chart series and index swatches are generated as `color-mix(in srgb, var(--accent) N%, var(--panel2))` at N = 100 / 66 / 46 / 32 / 22 — a single-hue ramp, not a categorical palette.

### Typography

Two families, both from Google Fonts, weights 400/500/600:

- **IBM Plex Mono** — the default for the entire app, set on the root container. All numbers, tickers, labels, table cells.
- **IBM Plex Sans** — headings, company names, and prose-like descriptive text (macro channel descriptions, thesis text). Applied per-element.

| Role | Family | Size | Weight | Letter-spacing |
|---|---|---|---|---|
| Body / root | Mono | 13px | 400 | — |
| Screen h1 | Sans | 24px | 600 | −.012em |
| Screen h1 (Sizer/Settings) | Sans | 22px | 600 | −.01em |
| Section h2 | Sans | 14–15px | 600 | .01em |
| Sidebar h2 | Sans | 13px | 600 | — |
| Big figure (tile hero) | Mono | 23px | 600 | −.015em |
| Medium figure | Mono | 19px | 600 | — |
| Table figure | Mono | 12–13px | 400–600 | — |
| Company name in row | Sans | 12–12.5px | 600 | — |
| Ticker sub-line | Mono | 10.5px | 400 | .05em |
| Micro-label (uppercase) | Mono | 10px | 400 | .08–.11em |
| Caption / note | Mono | 10.5–11px | 400 | .05em |
| Chip | Mono | 10.5px | 400 | .04em |
| Header wordmark | Mono | 11px | 600/400 | .14em |
| Nav button | Mono | 12px | 400/600 | .04em |
| Segmented button | Mono | 11.5px | 400/600 | .05em |

Line-height 1.45 globally. `font-variant-numeric: tabular-nums` on **every** numeric cell and figure — non-negotiable, the column alignment depends on it.

### Spacing, radius, shadow

- Radius: `4px` sections/cards, `3px` inner controls and inset panels, `2px` chips and bars, `1px` bar tracks and thin fills.
- Card padding: `15px 16px 14px` (tiles), `16px 18px` (sections), `18px` (account strip).
- Row padding: `11px 16px` standard, `9px 16px 9px 12px` table headers, `5px 16px` matrix rows.
- Grid gaps: `14px` between cards, `10–12px` within rows, `16–20px` in metric grids.
- Max content width: `1240px` (`760px` on Settings), centered, `24–26px 20px 80px` page padding.
- Borders are always `1px solid var(--line)`; `var(--line2)` for interactive outlines.

### Recurring patterns

**Chip** (verdict / flag / badge) — `padding:3px 9px; border-radius:2px; font-size:10.5px; letter-spacing:.04em; white-space:nowrap;` with color `C`, `background: color-mix(in srgb, C X%, transparent)` and `border: 1px solid color-mix(in srgb, C Y%, transparent)`, where X/Y = 20/50 at full strength, 12/34 at half, 7/22 neutral. `C` is `--up`, `--down` or `--ink3`.

**Nav button** — `padding:6px 12px; border-radius:3px; font-size:12px; letter-spacing:.04em;` inactive `transparent` / `--ink2` / weight 400; active `--accentSoft` / `--accent` / weight 600.

**Segmented control** — a flex row inside `1px solid var(--line2)`, `border-radius:3px; overflow:hidden`, no gaps. Buttons `padding:6px 13px; font-size:11.5px; letter-spacing:.05em;` inactive `transparent` / `--ink2`; active `background: var(--accent); color: var(--bg); font-weight:600`.

**Expandable row** — the whole row is the click target, `cursor:pointer`, `style-hover: background var(--panel2)`. A `▸`/`▾` chevron in `--ink3` sits in the last column. The drawer is a sibling block with `background: var(--panel2)`, `padding:15px 18px 17px 26px`, `border-bottom:1px solid var(--line)`.

**Gutter tint** — a 3–4px full-height first column, colored `color-mix(in srgb, C 85%|45%, transparent)` by strength, or `var(--line)` when neutral. Used for flags on Book and factor direction on Macro.

**Hover on cards** — `border-color: var(--ink3)`. Nothing moves, nothing scales.

## Screens

### Header (all screens)

Sticky, `height:52px`, `background: var(--panel)`, bottom `1px solid var(--line)`, `z-index:20`, `padding: 0 20px`, flex with `gap:20px`.

Left: wordmark `PORTFOLIO` (`--accent`, 600) + `TERMINAL` (`--ink3`, 400), 11px, `.14em`. Then nav: Dashboard, Book, `BROS` (the current Analysis subject — label is dynamic), Macro, Sizer, Settings, `gap:2px`.

Right, all 11px `--ink3` with `gap:14px`: timestamp `14 Aug 2026 · 09:12 BST`; a live indicator — 6px `--up` dot with a 2.4s ease-in-out opacity pulse (`.35 → 1 → .35`) plus the words `prices live`; and a theme toggle button reading `LIGHT` or `DARK` (the target theme, not the current one), `padding:5px 10px`, `1px solid var(--line2)`, radius 3px.

### 1. Dashboard

Purpose: one screen that answers "anything I need to look at today?" Every tile is a clickable entry to its surface.

**Account strip** (full width, above the tiles). A `repeat(auto-fit, minmax(148px,1fr))` grid, `gap:16px 20px`, of seven metrics — each a 10px uppercase `--ink3` label, a value, and an optional sub-line. Values: portfolio value `£148,320.44`; net deposited `£101,750.00` / `since 04 Jul 2023`; total return `+£46,570.44` / `+45.8%` (in `--up`); annualised (CAGR) `13.4%` / `over 3.1 yrs`; cost basis `£118,940.10`; cash `£27,588.02` / `18.6% of book`; unrealised P&L `+£19,380.34` / `+16.3%`.

Below, separated by a `13px` padded top border: a collapsed disclosure button, `▸ CAGR vs indices` + `since first deposit` in `--ink3`. Expanded, it shows a `repeat(auto-fit, minmax(120px,1fr))` grid of five indices with the account CAGR comparison and the delta in `--up`/`--down`: S&P 500 11.8% `+1.6pp`; Nasdaq 100 15.2% `−1.8pp`; FTSE 100 6.1% `+7.3pp`; German DAX 9.4% `+4.0pp`; Nikkei 225 10.2% `+3.2pp`.

**Tile grid** — `repeat(auto-fit, minmax(320px,1fr))`, `gap:14px`. Each tile is a flex column so its footer row sits at the bottom via `margin-top:auto`. Tile header is a 10px `.11em` uppercase `--ink3` name on the left and a chip or note on the right.

- **Book** → Book. Hero: day P&L in GBP at 23px, colored, with `day · +0.31%` beside it. Header chip: flag count in a `--down` half-strength chip. Then a 3-column stat row (best / worst / breadth: `9 up / 3 dn`) above a divider, then `N unexplained` in `--accent` and one row per flagged holding: ticker (600), actual move with `exp +1.9%` in `--ink3` beside it, and `z 2.7` right-aligned, all colored by direction.
- **Macro** → Macro. Header chip: `book <tilt>`. Four factor rows — label, an 8px horizontal bar on a `--panel2` track (centered at zero, extending left/right by magnitude, colored by direction), and the move right-aligned. Below a divider, `most affected`: ticker, weight, verdict chip.
- **Analysis · BROS** → Analysis. Header chip: `stale 17d`. Hero `$71.20` + `+10.1% since strike` in `--up`. A 20px band bar (`--bandLow` fill on `--panel2`) with a 2px `--accent` marker at 63%, labelled `LOW $34.64` / `63% of range` / `HIGH $92.39` at 10.5px. Footer: 3 stats above a top border.
- **Indices** → Book. Header chip: concentration, e.g. `NDX 43% of invested`, in a `--down` half chip when over the limit, neutral otherwise. A 5-column table — an 8px color swatch, index name, level, day %, your weight (600) — with a `8px | 1fr | 62px | 52px | 52px` grid, `gap:11px`, and a 10px uppercase header row above a `--line` border. Sorted by your weight, descending. Footer: a 9px stacked bar of the whole book by index (one flex segment per index, sized by weight, in the accent ramp, plus a `--line` segment for cash, `gap:1px`), captioned `book by index` / `18.6% cash`.
- **Calendar** (not clickable). `next 30d` note. Four earnings rows — ticker, period (`Q2 FY26`), date, days away — then `dividend income` and three stats: run-rate `£2,940 / yr`, yield on book `1.98%`, received YTD `£1,806`.

### 2. Book

Purpose: the full holdings ledger, plus the two exposure reads — unexplained moves and index concentration.

**Header row.** `Holdings` h2 with a summary line beneath: `12 holdings · £148,320 · 2 unexplained overnight · 11 without a model`. Right: a segmented filter (All 13 rows / flagged / modelled).

**Weighting by index panel** (above the ledger; this is the concentration answer). A section card, `padding:15px 16px 14px`, `margin-bottom:14px`. Header: `WEIGHTING BY INDEX` on the left, and on the right the note `limit line at 40% of invested · index = primary listing benchmark`. Then one row per index on a `10px | 118px | 54px | minmax(100px,1fr) | 104px | 88px | minmax(0,190px)` grid, `gap:12px`, sorted by weight descending:

1. A 10px `border-radius:2px` swatch in the index's ramp color.
2. Index name, 12px `--ink`.
3. Weight of total book, 13px 600, right-aligned.
4. A 9px bar on a `--panel2` track, width = share of *invested* (not total), with a 1px `--line2` vertical limit line at 40% extending 3px past the track top and bottom.
5. Share of invested, e.g. `43% of invested`, 11px `--ink3`.
6. An `over 40%` chip in `--down` half-strength, only on breaching rows (hidden, not absent, so the columns stay aligned).
7. The member tickers, `MSFT · COST · ASML · SBUX`, 10.5px `--ink2`, `.05em`.

Shares are of invested capital, so cash (18.6%) is excluded from the denominator; the total-book column and the Dashboard stacked bar do include it. Membership is the primary-listing benchmark, one index per holding — a hand-maintained map, not derived.

**Ledger.** A section with `overflow:hidden` and a `--panel2` header row. Grid: `4px | 150px | minmax(0,1fr) | 52px | 88px | 74px | 54px | 78px | 20px`, `gap:11px`, `padding:9px 16px 9px 12px`. Columns: gutter, `holding`, `weight · cost basis ○`, `wt`, `price`, `today vs exp`, `live PE`, `band`, chevron.

Each row: the accent gutter when a flag is open; holding cell with company name (Sans 12px 600, ellipsised) over `TICKER +36.1%` (10.5px, P&L colored); a weight bar with a small circle marking cost basis on a 20% scale; then the numeric columns; then a band mini-bar showing price within LOW–HIGH; then the chevron. Rows without a model show `—` and dimmed cells rather than being hidden.

Expanded drawer: an `actual / expected / residual / z` four-figure row at 15px, then a 9px stacked attribution bar (index / consumer / oil / residual, the residual segment in `--accent`) with a labelled legend beneath. Attribution lives **only** in the drawer, never in the row.

Footer note, 10.5px `--ink3`: `bars GBP weight, 20% scale · ○ cost basis · accent gutter = open flag · band = price in LOW–HIGH at reference multiple`.

### 3. Analysis (per-stock; BROS in the prototype)

Purpose: the valuation and thesis view for one holding, built from a parsed research note.

Top: two status callouts in a flex row — a `STALE` callout bordered in `--accent` on `--accentSoft` explaining the model was struck on older data, and a `PARSE` callout on `--panel` listing parse warnings. Then the identity block: `BROS` at 26px `.02em`, `Dutch Bros` in Sans 15px `--ink2`, an `NYSE` tag in a 1px `--line2` box, and a metric row (price now, since strike, weight, P&L).

Body is a `minmax(0,1fr) | ~320px` grid (`data-stock-grid`) that collapses to one column under 900px, with a sticky sidebar (`top:66px`).

Main column, in order: **Price vs scenario band** — a ~900×320 SVG with a `--bandLow` polygon between dashed high (`--up`) and low (`--ink3`) EPS-scenario lines across FY2025–FY2029, a horizontal `--accent` line at the current price with a filled `now $71.20` tag; **Live valuation** — a table of EPS modelled / macro adjustment / implied PE by fiscal year, with a reference-multiple segmented control (25/30/35/40); **Sensitivities** — one block per factor with label, code, an aggregate badge, the modelled % EPS impact, distance travelled, and the transmission channel in Sans, plus a separate "Affects the multiple, not EPS" group kept deliberately apart; **BAU bridge** — a collapsible revenue→EPS table in $m; **Risks** and **Peers** side by side.

Sidebar: **Thesis** (prose, edited date), **What changed** vs the prior note, **Position & sizing** (held, avg cost, weight, P&L + recent sizer runs), and the data-source panel.

### 4. Macro

Purpose: is the backdrop for or against the book, and which holdings are exposed.

Header: `Macro` h1, and `positioning read · book tilt <chip>` on the right.

**Indicator cards** — `repeat(auto-fit, minmax(238px,1fr))`, `gap:12px`. One per factor: uppercase label, a direction arrow, a state line (`Accelerating up`), a 30px-high inline SVG sparkline with `vector-effect:non-scaling-stroke`, value + `1m +2.8%`, and above a top border the count of affected holdings. Clicking one selects it as the list view's factor.

**Mode + view controls.** A segmented control switches Ranked list / Matrix. In list mode a second segmented control picks the factor (Combined + one per factor) with a note beside it; in matrix mode a legend appears instead.

**Ranked list** — grid `4px | minmax(150px,200px) | 132px | minmax(0,1fr) | 22px`, `gap:14px`. Gutter tinted by direction and strength, holding name over `TICKER · 4.2% of book`, a verdict chip (strong headwind / headwind / neutral / tailwind / strong tailwind), the transmission channel in Sans 11.5px ellipsised, chevron. Drawer: `factor by factor` — one row per factor with its own chip and channel text, plus a footnote on whether the holding is modelled or on a sector prior. Sorted by score.

**Matrix** — grid `minmax(140px,1fr) | repeat(4,64px) | 12px | 116px`, `gap:4px`, rows at `padding:5px 16px`. Holding (ticker + weight) then one cell per factor rendered as `−−` / `−` / `·` / `+` / `++`, colored and tinted by strength, each with a `title` giving the factor and channel; a spacer; then the combined verdict. Same click-to-expand behaviour.

**Weight direction** panel at the foot: three columns (trim / hold / add) listing tickers and weights, with the caveat `BROS modelled · 11 names on sector prior`.

Band thresholds: score ≤ −3 strong headwind, ≤ −1 headwind, < 1 neutral, < 3 tailwind, else strong tailwind. Combined score = Σ (factor effect × factor intensity).

### 5. Sizer

Purpose: position sizing for a candidate trade. **Roughed in — redesign before building.** Currently: target/stop/max-loss inputs, a computed share count and position size, and a run history. Reachable from nav and from the Analysis sidebar.

### 6. Settings

`760px` max width. Data-source and pipeline status as label/value rows: write path, parsed analyses (`1 of 12 holdings`), oldest strike date (in `--accent`), manual ingest fallback (`disabled`). This is where the model diagnostics belong — lookback window, per-holding R², last fit date, earnings-suppression status.

## Interactions & behavior

- **Navigation** — client-side screen switching, no page loads. Nav plus every Dashboard tile except Calendar. The Analysis nav item is labelled with the current subject ticker.
- **Row expansion** — one open row per table at a time (clicking another closes the first); clicking the open row closes it. Book defaults to `BROS` open.
- **Filters and view switches** — instant, no loading state.
- **Theme** — header toggle, persisted.
- **Hover** — cards get `border-color: var(--ink3)`; rows get `background: var(--panel2)`; disclosure buttons go `--ink2` → `--ink`. No transforms, no shadows on hover, no transitions longer than a snap.
- **Matrix cells** carry native `title` tooltips.
- **Responsive** — a single 900px breakpoint. The stock grid collapses to one column and un-stickies the sidebar; the ledger drops to `3px | 1fr | 48px | 72px | 66px` and hides the weight-bar, price, PE and chevron columns; wide metric grids collapse to single column. Below that it is not designed for phones and does not need to be.
- **Loading and error states are not designed.** Needed before shipping: stale-price indication (the header dot is the natural home), "no model yet" per holding (already handled as dimmed `—` cells), and a failed-sync state on the account strip.

## State

Screen-level: `screen` (home/book/stock/macro/sizer/settings), `theme`, `filter` (ledger), `expanded` (open ledger ticker), `macroOpen` (open macro ticker), `factor` (selected macro factor or ALL), macro mode (list/matrix), `idxOpen`, `bridgeOpen`, `peOpen`, `stepsOpen`, `scenario`, `mult` (reference multiple), and the Sizer inputs (`target`, `stop`, `maxLossPct`).

Persist across sessions: theme, ledger filter, macro mode and factor, reference multiple. Everything else can reset.

## Data requirements

See `DATA_MODEL.md` for the entity list, the ingestion jobs and their cadence, and the ticker→index map used by both index surfaces.

## Assets

None. No images, no icon set, no logos. Every graphic is inline SVG (sparklines, band chart) or CSS (bars, chips, gutters, swatches). Chevrons, arrows and matrix marks are text characters: `▸ ▾ ↑ ↓ ○ · − +`. Fonts are IBM Plex Mono and IBM Plex Sans from Google Fonts — self-host them if the deployment should work offline.

## Files

- `design/Portfolio Terminal.dc.html` — the full prototype, all six screens. Open in a browser to click through.
- `design/support.js` — prototype runtime. Reference only; nothing here belongs in production.
- `DATA_MODEL.md` — entities, sources, ingestion cadence, index map.
