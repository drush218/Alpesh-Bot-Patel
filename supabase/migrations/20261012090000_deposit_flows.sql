-- Dated net deposit flows for the money-weighted return (XIRR): {"YYYY-MM-DD": net GBP in}.
-- Cached alongside deposit_total; caches without it trigger one full transaction rescan.
alter table public.user_settings add column if not exists deposit_flows jsonb;
