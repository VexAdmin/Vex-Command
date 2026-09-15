-- DB roles for production. Run as superuser once via deploy/apply-founder-roles.sh.
-- vex_founder_ro: SELECT founder.* + aggregate views only (no findings table access).
-- Passwords are NOT stored here — set at deploy time (H2).

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vex_founder_ro') THEN
        CREATE ROLE vex_founder_ro NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vex_founder_rw') THEN
        CREATE ROLE vex_founder_rw NOLOGIN;
    END IF;
END
$$;

GRANT USAGE ON SCHEMA founder TO vex_founder_ro, vex_founder_rw;
GRANT SELECT ON ALL TABLES IN SCHEMA founder TO vex_founder_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA founder TO vex_founder_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA founder GRANT SELECT ON TABLES TO vex_founder_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA founder GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO vex_founder_rw;

-- Explicit deny pattern: ro role must not read scan_history.findings column via table grant.
-- Views never expose findings — revoke direct public table access from ro if granted by mistake.
REVOKE ALL ON public.scan_history FROM vex_founder_ro;

GRANT EXECUTE ON FUNCTION founder.f_org_targets() TO vex_founder_ro, vex_founder_rw;
GRANT SELECT ON founder.v_org_targets TO vex_founder_ro, vex_founder_rw;

-- Scans/metrics live behind Raptor RLS — same SECURITY DEFINER pattern as targets.
GRANT EXECUTE ON FUNCTION founder.f_scan_history() TO vex_founder_ro, vex_founder_rw;
GRANT EXECUTE ON FUNCTION founder.f_scan_metrics() TO vex_founder_ro, vex_founder_rw;

-- H4 follow-up (2026-09-15): information_schema.tables only lists a table for a
-- role that holds a real privilege on it — USAGE on schema public alone is not
-- enough. Without these grants, _run_migrations()'s has_raptor probe (which now
-- runs as the least-privilege runtime role, not the migration owner) silently
-- sees 0 rows and skips 002_aggregate_views.sql/003_roles.sql on a fresh
-- redeploy, even though the tables are really there. GRANT USAGE ON SCHEMA
-- public is still required (already applied at bootstrap) so these table-level
-- grants are visible at all.
GRANT USAGE ON SCHEMA public TO vex_founder_ro;
GRANT SELECT ON public.organizations TO vex_founder_ro;
GRANT SELECT (id, email, org_id) ON public.users TO vex_founder_ro;
