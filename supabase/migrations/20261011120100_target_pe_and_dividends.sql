-- Scorecard carries the user's macro score (0-3), target PE and why; saved with each version like the scores.
alter table public.scorecards
  add column macro          smallint check (macro between 0 and 3),
  add column target_pe      numeric check (target_pe > 0),
  add column target_pe_note text;

-- The user's dividend per share for a stock, in the quote currency (e.g. GBp, USD).
-- per_payment: amount x frequency; half: amount x 2; annual: amount; uneven: sum of payments.
create table public.dividend_inputs (
  user_id        uuid not null default auth.uid() references auth.users(id) on delete cascade,
  instrument_id  bigint not null references public.instruments(id) on delete cascade,
  mode           text not null check (mode in ('per_payment', 'half', 'annual', 'uneven')),
  amount         numeric check (amount >= 0),
  frequency      smallint check (frequency in (1, 2, 4, 12)),
  payments       jsonb not null default '[]',  -- uneven only: [12.5, 23.0]
  updated_at     timestamptz not null default now(),
  primary key (user_id, instrument_id)
);

alter table public.dividend_inputs enable row level security;
create policy "own rows" on public.dividend_inputs
  for all to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
