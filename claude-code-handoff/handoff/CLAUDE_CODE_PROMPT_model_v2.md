# Task: ingest stock model v2 (JSON block) + live PE

## Context
The stock-analysis skill now writes each company file with a fenced block:
````
```json stock-model
{ ...inputs..., "schema_version": 2, "outputs": {...} }
```
````
That block is the source of truth, rendered by the skill's `model.py`, so the parser no longer
scrapes tables for v2 files. Price is no longer in the file; PE is computed live.

Files:
- `BROS_v2_fixture.md` is the v2 fixture.
- `BROS_DutchBros.md` + `BROS_parsed_sample.json` are the legacy regression guard and must not
  break.

## 1. Parser (`markdown_to_json.py`)
- If the file contains a ```` ```json stock-model ```` block, take the v2 path: `json.loads` the
  block and validate `schema_version == 2`. Validate the enums against the same lists as `model.py`
  (copy them; don't import across repos). Reject the file on enum violations.
- Otherwise, take the existing legacy path **unchanged**. The BROS regression must stay
  byte-identical.
- Do not parse the markdown tables in v2 files.

## 2. Schema
```sql
alter table analyses add column schema_version int not null default 1;
alter table analyses add column model jsonb;   -- full v2 block, inputs + outputs

create type scenario as enum ('low','bau','high');
create table analysis_forecast (
  analysis_id bigint references analyses(id) on delete cascade,
  scenario scenario, fiscal_year text, ordinal int,
  revenue numeric, revenue_growth_pct numeric, operating_margin_pct numeric,
  operating_income numeric, net_income numeric, shares_diluted numeric, eps numeric,
  primary key (analysis_id, scenario, fiscal_year));

create table analysis_segment_forecast (            -- BAU and scenarios, per segment
  analysis_id bigint references analyses(id) on delete cascade,
  scenario scenario, fiscal_year text, segment text,
  growth_pct numeric, revenue numeric, source text, ref text,   -- source/ref from inputs (same for all scenarios)
  primary key (analysis_id, scenario, fiscal_year, segment));

create type event_type as enum ('earnings','trading_update','agm','ex_dividend','dividend_pay',
  'capital_markets_day','debt_maturity','guidance','index','other');
create table analysis_calendar (
  analysis_id bigint references analyses(id) on delete cascade,
  event_date date, event text, type event_type, confirmed boolean, source text);

create type macro_strength as enum ('negligible','mild','medium','strong');
create type macro_dir as enum ('bull','bear','neutral');
create table analysis_macro (
  analysis_id bigint references analyses(id) on delete cascade,
  factor_code text, channel text, direction macro_dir, strength macro_strength,
  speed lever_speed, ref text,
  primary key (analysis_id, factor_code, channel));

create table analysis_backtest_requests (
  analysis_id bigint references analyses(id) on delete cascade,
  factor_code text, series text, provider text, frequency text, lookback text, hypothesis text);
```
- Levers go into the existing `analysis_levers` table. `macro_factor_code` now arrives populated
  from the file. Stop leaving it null on parse.
- `channel_group` for levers: drop the token-matching heuristic for v2. Set it equal to
  `macro_factor_code` when two or more levers share that code; otherwise null.

## 3. Live views
```sql
create view v_live_pe as
select i.ticker, f.scenario, f.fiscal_year, f.eps,
       p.close as price, p.price_date,
       p.close / nullif(f.eps * fx.rate, 0) as pe       -- fx: reporting ccy -> price ccy (GBp handled here)
from analysis_forecast f
join analyses a on a.id = f.analysis_id and a.is_current
join instruments i on i.id = a.instrument_id
join latest_prices p on p.instrument_id = i.id
join latest_fx fx on fx.from_ccy = a.model->'meta'->>'reporting_currency'
                 and fx.to_ccy   = a.model->'meta'->>'price_currency';

create view v_upcoming_events as
select i.ticker, c.* from analysis_calendar c
join analyses a on a.id = c.analysis_id and a.is_current
join instruments i on i.id = a.instrument_id
where c.event_date >= current_date order by c.event_date;
```
- Adapt `latest_prices` / `latest_fx` to whatever already exists.
- `latest_fx` must return rate 1 for same-currency pairs. It must handle USD→GBp as the USD→GBP
  rate × 100.
- Staleness flag: an analysis is stale when `max(event_date) where type='earnings' and event_date
  < current_date` is later than `analyses.created_at`. Expose this on the dashboard.

## 4. Nightly job (still no LLM)
- Recompute PE from `v_live_pe`.
- Macro cross: join `analysis_macro` to `macro_factor_moves` on `factor_code`. Flip the direction
  when the move is down. Keep `v_lever_macro_cross` as is for levers.
- Backtests: for each request, regress weekly stock returns on factor changes over the lookback
  and store beta, t-stat and R² against the stated sign. This can be a separate later task: create
  the table now and stub the job.

## 5. Scenario workspace (editable model)

The analysis file is the **base**. On the stock page, every input is editable. Inputs are the cells
`model.py` takes as input; outputs are never edited directly. Editable inputs: segment growth per
year, operating margin, net interest, tax rate, NCI %, share change %, and the LOW/HIGH deltas.

**Calc engine.** Vendor the skill's `scripts/model.py` into the webapp as `stock_model.py` and call
`stock_model.run(inputs)` on every edit. Add a test asserting that `run(base inputs)` reproduces
`analyses.model.outputs` exactly. This stops the app engine and the skill engine drifting apart.

**UI behaviour:**
- Each edited cell is visibly marked and shows the base value and the base `ref` on hover.
- An output strip shows revenue, growth, margin, EPS and live PE per year: **base vs current
  workspace** side by side, with the delta.
- **Return to base** clears all overrides, with a confirmation step.
- **Save as scenario** takes a name and an optional note.
- **Load scenario** offers a dropdown of saved scenarios for this ticker; **Delete scenario** removes
  one.

```sql
create table user_scenarios (
  id bigserial primary key,
  instrument_id bigint references instruments(id) on delete cascade,
  base_analysis_id bigint references analyses(id),   -- base it was built on
  name text not null, note text,
  overrides jsonb not null,  -- [{"path":"revenue.segments[Company-operated].growth[1].pct","value":30.0,"base_value":25.7}]
  created_at timestamptz default now(), updated_at timestamptz default now(),
  unique (instrument_id, name));
```
- Overrides are stored as a **path → value list**, never as a full copy of the inputs.
  - Segments are addressed **by name**, not index, so a re-run that reorders segments doesn't
    misapply overrides.
  - Years are addressed by `forecast_years` label, not index.
  - Store `base_value` at save time.
- **Rebase on new analysis.** When a scenario is loaded against a newer current analysis:
  - apply overrides by path;
  - if a path no longer exists (segment renamed, year rolled off), drop it and list it in a
    "could not apply" note;
  - if the base value at that path changed since save, keep the override but flag it as
    "base moved: X → Y".
  - Do not update `base_analysis_id` until the user re-saves.

## 6. Scorecard (user-owned)

The file carries `scorecard_suggested`; the user's scorecard is separate and persists across
analysis re-runs.

```sql
create table scorecards (
  id bigserial primary key,
  instrument_id bigint references instruments(id) on delete cascade,
  growth smallint check (growth between 1 and 5),
  value  smallint check (value  between 1 and 5),
  income smallint check (income between 1 and 5),
  bull_catalysts jsonb not null default '[]',  -- [{"text":"","date":null,"status":"open|hit|missed"}]
  bear_catalysts jsonb not null default '[]',
  note text,
  created_at timestamptz default now());       -- append-only; latest row = current
create view v_scorecard_current as
  select distinct on (instrument_id) * from scorecards order by instrument_id, created_at desc;
```
- **No user scorecard yet:** show the suggested one greyed out, with **Adopt** (copies it into a
  first row) and **Edit** buttons.
- **User scorecard exists:** show it, with the suggested values in a collapsed "Claude's view
  (date)" panel underneath. Highlight any dimension where the two differ by 2 or more points.
- **Catalysts:**
  - add, edit and delete; set status to open / hit / missed;
  - a dated catalyst appears in `v_upcoming_events` alongside calendar items;
  - when its date passes with status still `open`, prompt for a status.
- Saving a scorecard always writes a new row, so the history is preserved.

## 7. Proposed macro factors
```sql
create table macro_factor_proposals (
  code text primary key, name text, series text, provider text,
  scope text check (scope in ('master','company')),
  rationale text, first_proposed_by bigint references analyses(id),
  status text not null default 'pending' check (status in ('pending','approved','rejected')),
  decided_at timestamptz);
```
- **On ingest:** insert each `proposed_factors` entry if its code is new. If the code already
  exists, append the proposing ticker to a list (add a column for this if needed) so you can see
  how many names want it.
- **Admin screen:** list pending proposals with **Approve** / **Reject**.
  - Approve adds the code to `macro_factors`, starts fetching the series in the nightly job, and
    activates the backtest requests that use it.
  - Reject keeps the macro and lever rows stored, but excludes them from the cross.
- `analysis_macro` / `analysis_levers` rows using a pending code are stored but excluded from
  `v_lever_macro_cross` and the macro cross until approved.
- Validation in the parser accepts a factor code if it is on the fixed list **or** declared in the
  same file's `proposed_factors`.

## 8. Tests
1. BROS legacy output is byte-identical.
2. The v2 fixture parses; `analysis_forecast` has 9 rows (3 scenarios × 3 years). BAU FY2028 EPS
   ≈ 1.87; total revenue = sum of segments in every row.
3. A v2 file with an invalid `strength` value is rejected with a clear error.
4. `v_live_pe` returns the same PE for USD/USD as a manual calc, and the correct PE for a GBp quote
   with USD EPS (synthetic HSBA row).
5. Two `oil` macro rows (demand, cost) are both stored and never summed.
6. `stock_model.run(base inputs)` equals the stored `outputs` for the BROS fixture.
7. Save a scenario overriding Company-operated FY2027 growth. Re-ingest a base where that cell
   changed: the override is still applied and flagged "base moved".
8. Re-ingest an analysis: the user scorecard is unchanged; `scorecard_suggested` updates.
9. BROS fixture ingest creates a pending `us_gasoline_retail` proposal. Its macro row is excluded
   from the cross until approved.

## Out of scope
Multi-user permissions (single user), scenario sharing, 
Migrating NFLX/CBRL/HSBA to v2 (re-run through the skill instead), backtest charting, and
`v_analysis_delta`.
