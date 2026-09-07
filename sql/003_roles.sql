-- DB roles for production. Run as superuser once.
-- vex_founder_ro: SELECT founder.* + aggregate views only (no findings table access).

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vex_founder_ro') THEN
        CREATE ROLE vex_founder_ro LOGIN PASSWORD 'change_me_ro';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'vex_founder_rw') THEN
        CREATE ROLE vex_founder_rw LOGIN PASSWORD 'change_me_rw';
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
