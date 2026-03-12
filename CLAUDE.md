# Claude Working Notes — Alpesh Bot Patel

## Project Overview
Streamlit app connected to Trading212 API. Shows live portfolio with allocation chart, position calculator, and settings.

**Run command:** `streamlit run app.py`

**Key files:**
- `app.py` — entry point, auth, navigation
- `pages/1_My_Portfolio.py` — portfolio overview + allocation chart
- `pages/2_Position_Calculator.py` — position sizing tool
- `pages/3_Settings.py` — API credentials
- `auth.py` — Trading212 auth + deposit stats helpers

---

## How the User Likes to Work

- **Confirm understanding before acting** on ambiguous layout/design requests — user will correct interpretation before code is written
- **Incremental changes** — make one focused change at a time, don't refactor surrounding code
- **Ask before rethinking** — if a design has a fundamental constraint (e.g. won't fit on mobile), explain the trade-off and ask which direction to go rather than silently redesigning
- **Short, direct responses** — no preamble, no lengthy explanations unless asked
- **Screenshots help** — user will share screenshots when visual output is unclear; wait for one before guessing at rendering issues
- **Living doc** — user will ask to update this file as sessions progress

---

## Technical Pitfalls

### File editing
- **Never use bash/PowerShell heredoc or inline Python string replacement via shell** — `!=` gets corrupted to `\!=` due to shell escaping
- **Safe pattern:** write a temporary `_patch.py` file using the Write tool, execute it with `python _patch.py`, then delete it — OR use the Edit tool directly on small, targeted changes
- `pages/1_My_Portfolio.py` is **untracked by git** — no git restore fallback, be careful with whole-file rewrites
- When rewriting large sections, read the full file first to avoid losing context (the middle section was lost once)

### Trading212 API
- Auth: Basic auth with `base64(api_key:api_secret)` — applies to ALL endpoints including history
- Transaction history endpoint: `GET /api/v0/equity/history/transactions?limit=50`
- Rate limit: **6 req / 1 min** — burst allowed; check `x-ratelimit-remaining` header; sleep until `x-ratelimit-reset` when ≤ 1 remaining
- Pagination: cursor-based via `nextPagePath` in response — may return query string only (no leading `/`), so prepend `/api/v0/equity/history/transactions?` if needed
- Transactions return **newest first**
- Transaction type field: `dateTime` (not `date` or `dateModified`)
- Relevant types: `DEPOSIT`, `WITHDRAW` (not `WITHDRAWAL`), `TRANSFER` (signed — positive = in, negative = out), `FEE`
- Interest on cash comes through as small `DEPOSIT` entries — filter `amount >= 5` to exclude them
- No server-side filtering by type or amount — always fetch all pages client-side

### Deposit stats caching (auth.py + portfolio page)
- Cached in Supabase `user_settings` table: `deposit_total`, `first_deposit_date`, `deposit_stats_cached_at`, `last_tx_fetched_at`
- `get_deposit_stats()` always returns stored data (even if stale) — caller checks `cached_at` for staleness
- Stale threshold: 24 hours
- On stale: incremental fetch — pages newest-first, stops when hitting `last_tx_fetched_at`, adds delta to existing total
- On missing: full fetch across all pages
- To force full re-fetch: `UPDATE user_settings SET deposit_stats_cached_at = NULL, last_tx_fetched_at = NULL`

### Plotly annotation rendering
- `go.Bar` text does **not** support HTML (no `<span style="color:...">`) — use annotations for any coloured/styled text
- Annotations DO support HTML — use `<span style='color:...'>` and `<b>` tags
- For text inside bars: use `insidetextanchor="end"` on the bar trace for reliable right-alignment; don't rely on annotations with `xref="x"` for inside-bar positioning
- `xref="paper"` annotations are good for fixed-position labels (left company names, header row)
- `cornerradius` on `go.Bar` requires Plotly 5.12+

### Mobile vs desktop
- Left margin `l=160`, right margin `r=150` is the current balance — tighter breaks mobile, wider is better on desktop
- Company names truncated at 22 chars with `…` to save space

---

## Allocation Chart — Current Design

**Structure:**
1. Grey track bar (100% width) — scale reference
2. Blue pill bar — actual % allocation
3. White dot (scatter) — cost basis % position, with `X.X%` callout to its right
4. Left annotations — company name (bold, truncated) + ticker below in grey
5. Right annotations (inside grey track, right-aligned to x=100) — `Allocation%  |  P&L%` with coloured P&L
6. Header annotation at top — `"Allocation  |  P&L"` column labels

**Colour conventions:**
- Bars: `rgba(99,102,241,0.85)` (indigo blue) — uniform, no P&L colouring on bars
- P&L positive: `#16a34a` (green)
- P&L negative: `#dc2626` (red)
- Divider `|`: `#d1d5db` (light grey)
- Company name: `#111827`
- Ticker / header labels: `#6b7280` / `#9ca3af`

---

## Design Preferences
- Clean and modern — no clutter
- Colour should be meaningful (P&L direction), not decorative
- Text inside/on charts preferred over external legends
- Mobile compatibility matters but desktop is primary
