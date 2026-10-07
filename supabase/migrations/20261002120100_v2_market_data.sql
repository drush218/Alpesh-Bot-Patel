-- Portfolio Terminal v2: prices, FX and the live views.
-- Prices/FX are source-agnostic; the backend refresh fills them from Yahoo (yfinance) at session
-- start / on demand. Same-day rows are overwritten in place, so fetched_at shows freshness.

create table public.prices (
  instrument_id  bigint not null references public.instruments(id) on delete cascade,
  price_date     date not null,
  close          numeric not null,   -- last price; intraday until the day closes
  currency       text not null,      -- as quoted, e.g. USD, GBp
  source         text not null,      -- 'yahoo', 't212', ...
  fetched_at     timestamptz not null default now(),
  primary key (instrument_id, price_date)
);

-- Major-unit pairs only (USD->GBP, not USD->GBp); fx_rate() handles pence.
create table public.fx_rates (
  from_ccy    text not null,
  to_ccy      text not null,
  rate_date   date not null,
  rate        numeric not null,
  source      text not null,
  fetched_at  timestamptz not null default now(),
  primary key (from_ccy, to_ccy, rate_date)
);

create view public.latest_prices with (security_invoker = true) as
  select distinct on (instrument_id) *
  from public.prices
  order by instrument_id, price_date desc;

-- Rate to convert 1 unit of from_ccy into to_ccy, using the latest stored rate.
-- Same currency -> 1. GBp (pence) is GBP / 100. Falls back to the inverse pair.
create function public.fx_rate(from_ccy text, to_ccy text) returns numeric
language sql stable set search_path = '' as $$
  with n as (
    select case when from_ccy in ('GBp', 'GBX') then 'GBP' else upper(from_ccy) end as f,
           case when to_ccy   in ('GBp', 'GBX') then 'GBP' else upper(to_ccy)   end as t,
           (case when from_ccy in ('GBp', 'GBX') then 0.01 else 1 end)
         * (case when to_ccy   in ('GBp', 'GBX') then 100  else 1 end) as unit
  )
  select n.unit * case
    when n.f = n.t then 1
    else coalesce(
      (select r.rate from public.fx_rates r
        where r.from_ccy = n.f and r.to_ccy = n.t order by r.rate_date desc limit 1),
      (select 1 / nullif(r.rate, 0) from public.fx_rates r
        where r.from_ccy = n.t and r.to_ccy = n.f order by r.rate_date desc limit 1))
    end
  from n
$$;

-- PE = price / (EPS converted into the price currency). Price currency comes from the price row.
create view public.v_live_pe with (security_invoker = true) as
  select i.id as instrument_id, i.ticker, a.id as analysis_id,
         f.scenario, f.fiscal_year, f.ordinal, f.eps,
         a.reporting_currency, p.currency as price_currency,
         p.close as price, p.price_date, p.fetched_at as price_fetched_at,
         public.fx_rate(a.reporting_currency, p.currency) as fx,
         p.close / nullif(f.eps * public.fx_rate(a.reporting_currency, p.currency), 0) as pe
  from public.analysis_forecast f
  join public.analyses a on a.id = f.analysis_id and a.is_current
  join public.instruments i on i.id = a.instrument_id
  join public.latest_prices p on p.instrument_id = i.id;

-- Stale when an earnings date in the analysis's own calendar has passed since it was created.
create view public.v_analysis_staleness with (security_invoker = true) as
  select a.id as analysis_id, i.ticker, a.created_at,
         max(c.event_date) filter (where c.type = 'earnings' and c.event_date < current_date) as last_earnings,
         coalesce(max(c.event_date) filter (where c.type = 'earnings' and c.event_date < current_date)
                  > a.created_at::date, false) as is_stale
  from public.analyses a
  join public.instruments i on i.id = a.instrument_id
  left join public.analysis_calendar c on c.analysis_id = a.id
  where a.is_current
  group by a.id, i.ticker, a.created_at;

-- Latest move per approved factor.
create view public.v_macro_latest_move with (security_invoker = true) as
  select distinct on (factor_code) factor_code, as_of, value, change, move
  from public.macro_factor_moves
  order by factor_code, as_of desc;

-- Macro cross for analysis_macro rows. Inner join to macro_factors excludes pending/rejected
-- proposed codes. Direction flips when the factor moved down.
create view public.v_macro_cross with (security_invoker = true) as
  select i.ticker, m.analysis_id, m.factor_code, m.channel, m.strength, m.speed,
         m.direction as stated_direction, mv.move, mv.as_of,
         case when mv.move = 'down' and m.direction = 'bull' then 'bear'::public.macro_dir
              when mv.move = 'down' and m.direction = 'bear' then 'bull'::public.macro_dir
              else m.direction end as effective_direction
  from public.analysis_macro m
  join public.analyses a on a.id = m.analysis_id and a.is_current
  join public.instruments i on i.id = a.instrument_id
  join public.macro_factors mf on mf.code = m.factor_code
  left join public.v_macro_latest_move mv on mv.factor_code = m.factor_code;

-- Same cross for levers that carry a macro_factor_code.
create view public.v_lever_macro_cross with (security_invoker = true) as
  select i.ticker, l.analysis_id, l.id as lever_id, l.lever_name, l.base, l.exposure,
         l.speed, l.macro_factor_code, l.channel_group,
         l.direction as stated_direction, mv.move, mv.as_of,
         case when mv.move = 'down' and l.direction = 'bull' then 'bear'
              when mv.move = 'down' and l.direction = 'bear' then 'bull'
              else l.direction end as effective_direction
  from public.analysis_levers l
  join public.analyses a on a.id = l.analysis_id and a.is_current
  join public.instruments i on i.id = a.instrument_id
  join public.macro_factors mf on mf.code = l.macro_factor_code
  left join public.v_macro_latest_move mv on mv.factor_code = l.macro_factor_code;
