-- DB roles for production. Run as superuser once via deploy/apply-founder-roles.sh
-- (idempotent — re-applied on every container start via MIGRATION_DATABASE_URL).
-- Passwords are NOT stored here — set at deploy time (H2).
--
-- S3 (2026-09-18): vex_founder_ro is the ONLY runtime role — SELECT on the
-- read-only aggregate views + narrowly scoped DML on the handful of tables
-- the app writes directly (pipeline, notes, goals/OKRs, manual revenue
-- ledger), INSERT-only on audit_log (read path goes through
-- founder.v_audit_log instead). vex_founder_rw is deprecated: kept only so
-- deploy/apply-founder-roles.sh can still rotate its password without
-- erroring, but it is granted NOTHING below. It must never again be the
-- runtime DATABASE_URL — deploy/run-vex-founder.sh refuses to start if it is.

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

-- Reset to a clean slate before re-granting narrowly. Earlier releases granted
-- vex_founder_ro blanket SELECT on every founder.* table and vex_founder_rw
-- full DML (including DELETE) on every founder.* table, incl. audit_log — a
-- leaked vex_founder_rw credential could erase the audit trail. Re-running
-- this file on an already-provisioned prod DB must revoke that, not just stop
-- re-granting it going forward.
REVOKE ALL ON ALL TABLES IN SCHEMA founder FROM vex_founder_ro, vex_founder_rw;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA founder FROM vex_founder_ro, vex_founder_rw;
REVOKE EXECUTE ON FUNCTION founder.f_org_targets() FROM vex_founder_rw;
REVOKE EXECUTE ON FUNCTION founder.f_scan_history() FROM vex_founder_rw;
REVOKE EXECUTE ON FUNCTION founder.f_scan_metrics() FROM vex_founder_rw;
ALTER DEFAULT PRIVILEGES IN SCHEMA founder REVOKE SELECT ON TABLES FROM vex_founder_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA founder REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM vex_founder_rw;
-- vex_founder_rw stops here — deprecated, no privileges granted below.

-- Runtime read path: aggregate views only. No blanket "ALL TABLES IN SCHEMA
-- founder" grant to vex_founder_ro anymore — an app-level bug can no longer
-- read every row of every founder table (e.g. raw audit_log, see below).
GRANT SELECT ON
    founder.v_org_summary,
    founder.v_platform_scan_ops,
    founder.v_usage_platform,
    founder.v_org_targets,
    founder.v_scan_attribution,
    founder.v_audit_log
TO vex_founder_ro;

-- Runtime write path: the only founder.* base tables the app writes directly
-- (pipeline, account notes, goals/OKRs, manual revenue ledger — see
-- backend/app/providers/sql.py). founder.deal_activity is the append-only
-- history side table for `deal` (create_deal/update_deal_stage write to it on
-- every deal insert/stage change) — it travels with `deal` even though the
-- plan's table list didn't spell it out; the app breaks without it.
GRANT SELECT, INSERT, UPDATE ON
    founder.deal,
    founder.deal_activity,
    founder.account_note,
    founder.account_ops,
    founder.goal,
    founder.okr,
    founder.manual_revenue
TO vex_founder_ro;

GRANT USAGE ON SEQUENCE
    founder.deal_id_seq,
    founder.deal_activity_id_seq,
    founder.account_note_id_seq,
    founder.manual_revenue_id_seq
TO vex_founder_ro;

-- Explicit deny pattern: ro role must not read scan_history.findings column via table grant.
-- Views never expose findings — revoke direct public table access from ro if granted by mistake.
REVOKE ALL ON public.scan_history FROM vex_founder_ro;

GRANT EXECUTE ON FUNCTION founder.f_org_targets() TO vex_founder_ro;

-- Scans/metrics live behind Raptor RLS — same SECURITY DEFINER pattern as targets.
GRANT EXECUTE ON FUNCTION founder.f_scan_history() TO vex_founder_ro;
GRANT EXECUTE ON FUNCTION founder.f_scan_metrics() TO vex_founder_ro;

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

-- vex_founder_ro is read-only everywhere except its own audit trail: the app
-- writes one row to founder.audit_log per authenticated request (who viewed
-- what, when). INSERT-only, no SELECT/UPDATE/DELETE on the base table — the
-- runtime role reads its own trail through founder.v_audit_log above instead,
-- so a compromised app process can append audit rows but can't rewrite or
-- bulk-export/erase history through any other query surface.
GRANT INSERT ON founder.audit_log TO vex_founder_ro;
GRANT USAGE ON SEQUENCE founder.audit_log_id_seq TO vex_founder_ro;
