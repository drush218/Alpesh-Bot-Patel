-- rls_auto_enable() backs the ensure_rls event trigger; it is not meant to be called via the API.
-- Event triggers run it as its owner, so revoking EXECUTE from API roles doesn't stop it working.
revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
