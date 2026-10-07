-- Portfolio Terminal v2: instruments, analyses and the v2 child tables.
-- v2-only: the legacy (schema_version 1) child tables are not created. Legacy files still parse
-- but are not persisted; re-run them through the stock-analysis skill instead.

-- ------------------------------------------------------------------ enums
create type public.scenario as enum ('low', 'bau', 'high');
create type public.event_type as enum ('earnings', 'trading_update', 'agm', 'ex_dividend',
  'dividend_pay', 'capital_markets_day', 'debt_maturity', 'guidance', 'index', 'other');
create type public.macro_strength as enum ('negligible', 'mild', 'medium', 'strong');
create type public.macro_dir as enum ('bull', 'bear', 'neutral');
create type public.lever_speed as enum ('immediate', 'near', 'lagged');

-- ------------------------------------------------------------------ instruments
-- ticker is the model ticker from meta.ticker (e.g. BROS, HSBA). t212_ticker links the
-- Trading212 position (e.g. BROS_US_EQ); yahoo_symbol is what the price refresh fetches
-- (e.g. BROS, HSBA.L). Both are nullable until mapped.
create table public.instruments (
  id            bigint generated always as identity primary key,
  ticker        text not null unique,
  company       text,
  exchange      text,
  currency      text,                 -- quote currency, e.g. USD, GBp
  t212_ticker   text unique,
  yahoo_symbol  text unique,
  created_at    timestamptz not null default now()
);

-- ------------------------------------------------------------------ analyses
create table public.analyses (
  id                  bigint generated always as identity primary key,
  instrument_id       bigint not null references public.instruments(id) on delete cascade,
  schema_version      int not null default 2,
  model               jsonb not null,       -- full v2 block, inputs + outputs
  reporting_currency  text,                 -- meta.reporting_currency (EPS currency)
  price_currency      text,                 -- meta.price_currency (quote currency)
  data_as_of          date,
  content_hash        text not null,
  raw_markdown        text,
  narrative           jsonb not null default '{}',
  warnings            jsonb not null default '[]',
  is_current          boolean not null default false,
  created_at          timestamptz not null default now(),
  unique (instrument_id, content_hash)
);
-- At most one current analysis per instrument. promote clears the old flag before setting the new.
create unique index analyses_one_current on public.analyses (instrument_id) where is_current;

create table public.analysis_forecast (
  analysis_id           bigint not null references public.analyses(id) on delete cascade,
  scenario              public.scenario not null,
  fiscal_year           text not null,
  ordinal               int not null,
  revenue               numeric,
  revenue_growth_pct    numeric,
  operating_margin_pct  numeric,
  operating_income      numeric,
  net_income            numeric,
  shares_diluted        numeric,
  eps                   numeric,
  primary key (analysis_id, scenario, fiscal_year)
);

create table public.analysis_segment_forecast (
  analysis_id  bigint not null references public.analyses(id) on delete cascade,
  scenario     public.scenario not null,
  fiscal_year  text not null,
  segment      text not null,
  growth_pct   numeric,
  revenue      numeric,
  source       text,     -- from inputs, same for all scenarios
  ref          text,
  primary key (analysis_id, scenario, fiscal_year, segment)
);

create table public.analysis_calendar (
  id           bigint generated always as identity primary key,
  analysis_id  bigint not null references public.analyses(id) on delete cascade,
  event_date   date not null,
  event        text,
  type         public.event_type not null,
  confirmed    boolean,
  source       text
);
create index on public.analysis_calendar (analysis_id);
create index on public.analysis_calendar (event_date);

create table public.analysis_macro (
  analysis_id  bigint not null references public.analyses(id) on delete cascade,
  factor_code  text not null,
  channel      text not null,
  direction    public.macro_dir not null,
  strength     public.macro_strength not null,
  speed        public.lever_speed,
  ref          text,
  primary key (analysis_id, factor_code, channel)
);

create table public.analysis_levers (
  id                 bigint generated always as identity primary key,
  analysis_id        bigint not null references public.analyses(id) on delete cascade,
  base               text not null check (base in ('revenue', 'cost')),
  lever_name         text not null,
  exposure           text check (exposure in ('minor', 'partial', 'dominant')),
  exposure_pct       numeric,
  speed              public.lever_speed,
  direction          text check (direction in ('bull', 'bear')),
  macro_factor_code  text,
  channel_group      text,     -- = macro_factor_code when 2+ levers share it, else null
  watch_metric       text,
  current_reading    text,
  pushes_low         text,
  pushes_high        text
);
create index on public.analysis_levers (analysis_id);

create table public.analysis_backtest_requests (
  id           bigint generated always as identity primary key,
  analysis_id  bigint not null references public.analyses(id) on delete cascade,
  factor_code  text not null,
  series       text,
  provider     text,
  frequency    text,
  lookback     text,
  hypothesis   text
);
create index on public.analysis_backtest_requests (analysis_id);

-- Filled by the (stubbed) nightly backtest job.
create table public.backtest_results (
  request_id    bigint primary key references public.analysis_backtest_requests(id) on delete cascade,
  beta          numeric,
  t_stat        numeric,
  r_squared     numeric,
  n_obs         int,
  sign_matches  boolean,   -- beta sign agrees with the hypothesis
  run_at        timestamptz not null default now()
);

-- ------------------------------------------------------------------ macro factors
-- Approved factors. A code is in the macro cross only if it is in this table.
create table public.macro_factors (
  code        text primary key,
  name        text not null,
  series      text,
  provider    text,
  scope       text not null default 'master' check (scope in ('master', 'company')),
  created_at  timestamptz not null default now()
);
insert into public.macro_factors (code, name) values
  ('rates_policy',   'Policy rate'),
  ('rates_10y',      '10y government yield'),
  ('fx_usd',         'US dollar'),
  ('oil',            'Crude oil'),
  ('natgas',         'Natural gas'),
  ('labour',         'Labour costs'),
  ('consumer_spend', 'Consumer spending'),
  ('credit_spreads', 'Credit spreads'),
  ('inflation',      'Inflation'),
  ('china_activity', 'China activity');

create table public.macro_factor_proposals (
  code                text primary key,
  name                text,
  series              text,
  provider            text,
  scope               text check (scope in ('master', 'company')),
  rationale           text,
  first_proposed_by   bigint references public.analyses(id) on delete set null,
  proposed_by_tickers text[] not null default '{}',
  status              text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  created_at          timestamptz not null default now(),
  decided_at          timestamptz
);

-- One row per factor per observation date; written by the nightly macro fetch.
create table public.macro_factor_moves (
  factor_code  text not null references public.macro_factors(code) on delete cascade,
  as_of        date not null,
  value        numeric,
  change       numeric,
  move         text not null check (move in ('up', 'down', 'flat')),
  primary key (factor_code, as_of)
);
