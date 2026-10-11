-- Scorecard scores move from 1–5 to 0–3 (0 is a real score). No rows existed when this ran.
alter table public.scorecards
  drop constraint scorecards_growth_check,
  drop constraint scorecards_value_check,
  drop constraint scorecards_income_check,
  add constraint scorecards_growth_check check (growth between 0 and 3),
  add constraint scorecards_value_check  check (value  between 0 and 3),
  add constraint scorecards_income_check check (income between 0 and 3);
