-- =============================================================================
-- personal/0010_public_is_owner.sql
--
-- A public-schema ownership check for server-side API routes.
--
-- Why it exists: PostgREST exposes `public` only, so `personal.is_principal()`
-- is unreachable from an API route holding the caller's JWT. The routes must
-- still verify ownership without a service key (which must never exist in
-- this stack outside Supabase/Vercel secret stores), so this thin wrapper —
-- SECURITY DEFINER, caller-blind, boolean-only — answers one question: is
-- the caller the principal?
--
-- Why it is safe:
--   * EXECUTE is revoked from public/anon; only authenticated + service_role.
--   * It returns one bit about the caller, never about anyone else.
--   * isolation_matrix's anon_rpc_surface stays 0 (anon cannot execute it),
--     and its leak scan covers personal/training/aon_app functions only.
-- =============================================================================

create or replace function public.is_owner()
returns boolean
language sql
stable
security definer
set search_path = personal, pg_temp
as $$
  select personal.is_principal();
$$;

revoke all on function public.is_owner() from public, anon;
grant execute on function public.is_owner() to authenticated, service_role;
