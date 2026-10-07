-- Portfolio Terminal v2: user-owned scenarios and scorecards, upcoming events, RLS.
-- user_id ties rows to the logged-in user (same as user_settings). Shared reference data
-- (instruments, analyses, prices, macro) is readable/writable by any authenticated user.

create table public.user_scenarios (
  id                bigint generated always as identity primary key,
  user_id           uuid not null default auth.uid() references auth.users(id) on delete cascade,
  instrument_id     bigint not null references public.instruments(id) on delete cascade,
  base_analysis_id  bigint references public.analyses(id) on delete set null,  -- base it was built on
  name              text not null,
  note              text,
  overrides         jsonb not null,  -- [{"path": "...", "value": 30.0, "base_value": 25.7}]
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  unique (user_id, instrument_id, name)
);

-- Append-only; latest row per (user, instrument) is current.
create table public.scorecards (
  id              bigint generated always as identity primary key,
  user_id         uuid not null default auth.uid() references auth.users(id) on delete cascade,
  instrument_id   bigint not null references public.instruments(id) on delete cascade,
  growth          smallint check (growth between 1 and 5),
  value           smallint check (value  between 1 and 5),
  income          smallint check (income between 1 and 5),
  bull_catalysts  jsonb not null default '[]',  -- [{"text": "", "date": null, "status": "open|hit|missed"}]
  bear_catalysts  jsonb not null default '[]',
  note            text,
  created_at      timestamptz not null default now()
);
create index on public.scorecards (user_id, instrument_id, created_at desc);

create view public.v_scorecard_current with (security_invoker = true) as
  select distinct on (user_id, instrument_id) *
  from public.scorecards
  order by user_id, instrument_id, created_at desc;

-- Calendar items from current analyses plus open dated catalysts from the current scorecard.
create view public.v_upcoming_events with (security_invoker = true) as
  select i.ticker, c.event_date, c.event, c.type::text as type, c.confirmed, c.source,
         'calendar'::text as origin, null::uuid as user_id
  from public.analysis_calendar c
  join public.analyses a on a.id = c.analysis_id and a.is_current
  join public.instruments i on i.id = a.instrument_id
  where c.event_date >= current_date
  union all
  select i.ticker, (j.cat->>'date')::date, j.cat->>'text', j.side || '_catalyst', null, null,
         'scorecard', s.user_id
  from public.v_scorecard_current s
  join public.instruments i on i.id = s.instrument_id
  cross join lateral (
    select 'bull' as side, x as cat from jsonb_array_elements(s.bull_catalysts) x
    union all
    select 'bear', x from jsonb_array_elements(s.bear_catalysts) x
  ) j
  where j.cat->>'date' is not null and (j.cat->>'date')::date >= current_date
    and coalesce(j.cat->>'status', 'open') = 'open'
  order by 2;

-- ------------------------------------------------------------------ RLS
do $$
declare t text;
begin
  foreach t in array array[
    'instruments', 'analyses', 'analysis_forecast', 'analysis_segment_forecast',
    'analysis_calendar', 'analysis_macro', 'analysis_levers', 'analysis_backtest_requests',
    'backtest_results', 'macro_factors', 'macro_factor_proposals', 'macro_factor_moves',
    'prices', 'fx_rates']
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('create policy "authenticated full access" on public.%I
                    for all to authenticated using (true) with check (true)', t);
  end loop;

  foreach t in array array['user_scenarios', 'scorecards']
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format('create policy "own rows" on public.%I
                    for all to authenticated
                    using (user_id = (select auth.uid()))
                    with check (user_id = (select auth.uid()))', t);
  end loop;
end $$;
