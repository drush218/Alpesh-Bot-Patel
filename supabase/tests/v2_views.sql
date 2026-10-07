-- Database halves of handoff tests 4 and 9 (CLAUDE_CODE_PROMPT_model_v2.md section 8).
-- Self-contained and side-effect free: everything runs in one transaction that always aborts.
-- Passing ends with ERROR 'V2 VIEW TESTS PASSED'; any failure raises 'FAIL: ...' instead.
-- Run via the Supabase SQL editor or the connector's execute_sql.

begin;

insert into public.instruments (ticker, currency) values ('ZZTEST_US', 'USD'), ('ZZTEST_GB', 'GBp');
insert into public.analyses (instrument_id, model, reporting_currency, price_currency, content_hash, is_current)
  select id, '{}', 'USD', currency, 'zztest', true from public.instruments where ticker like 'ZZTEST_%';
insert into public.analysis_forecast (analysis_id, scenario, fiscal_year, ordinal, eps)
  select a.id, 'bau', 'FY2026', 1, case i.ticker when 'ZZTEST_US' then 1.87 else 1.20 end
  from public.analyses a join public.instruments i on i.id = a.instrument_id where i.ticker like 'ZZTEST_%';
insert into public.prices (instrument_id, price_date, close, currency, source)
  select id, '2999-01-01', case ticker when 'ZZTEST_US' then 64.67 else 900 end, currency, 'test'
  from public.instruments where ticker like 'ZZTEST_%';
insert into public.fx_rates (from_ccy, to_ccy, rate_date, rate, source)
  values ('GBP', 'USD', '2999-01-01', 1.25, 'test');

insert into public.macro_factor_proposals (code, proposed_by_tickers) values ('zz_pending', '{ZZTEST_US}');
insert into public.analysis_macro (analysis_id, factor_code, channel, direction, strength, speed)
  select a.id, f, 'demand', 'bear', 'medium', 'near'
  from public.analyses a join public.instruments i on i.id = a.instrument_id,
       unnest(array['zz_pending', 'oil']) f
  where i.ticker = 'ZZTEST_US';
insert into public.macro_factor_moves (factor_code, as_of, change, move) values ('oil', '2999-01-01', -2, 'down');

do $$
declare
  pe_us numeric; pe_gb numeric; fx_gb numeric; codes text[]; oil_dir text;
begin
  -- Test 4a: USD price, USD EPS -> plain price / EPS
  select pe into pe_us from public.v_live_pe where ticker = 'ZZTEST_US';
  if round(pe_us, 6) <> round(64.67 / 1.87, 6) then
    raise exception 'FAIL: USD/USD pe % <> manual %', pe_us, 64.67 / 1.87;
  end if;

  -- Test 4b: GBp price, USD EPS. USD->GBp = (1 / 1.25) * 100 = 80; pe = 900 / (1.20 * 80)
  select fx, pe into fx_gb, pe_gb from public.v_live_pe where ticker = 'ZZTEST_GB';
  if fx_gb <> 80 or round(pe_gb, 6) <> 9.375 then
    raise exception 'FAIL: GBp pe % (fx %) <> 9.375 (fx 80)', pe_gb, fx_gb;
  end if;
  if public.fx_rate('USD', 'USD') <> 1 or public.fx_rate('GBp', 'GBP') <> 0.01 then
    raise exception 'FAIL: fx_rate same-currency / pence handling';
  end if;

  -- Test 9: pending code stored but excluded from the cross until approved
  select array_agg(factor_code order by factor_code) into codes
    from public.v_macro_cross where ticker = 'ZZTEST_US';
  if codes <> array['oil'] then
    raise exception 'FAIL: cross codes % <> {oil}', codes;
  end if;
  if (select count(*) from public.analysis_macro m join public.analyses a on a.id = m.analysis_id
       join public.instruments i on i.id = a.instrument_id
       where i.ticker = 'ZZTEST_US' and m.factor_code = 'zz_pending') <> 1 then
    raise exception 'FAIL: pending macro row not stored';
  end if;
  select effective_direction into oil_dir from public.v_macro_cross where ticker = 'ZZTEST_US' and factor_code = 'oil';
  if oil_dir <> 'bull' then
    raise exception 'FAIL: oil down move should flip bear -> bull, got %', oil_dir;
  end if;

  -- ...and included once approved
  insert into public.macro_factors (code, name) values ('zz_pending', 'zz');
  if (select count(*) from public.v_macro_cross where ticker = 'ZZTEST_US') <> 2 then
    raise exception 'FAIL: approved code not in cross';
  end if;

  raise exception 'V2 VIEW TESTS PASSED';
end $$;

rollback;
