-- One-time, run as vex_raptor superuser (owner-level DDL for founder schema setup).
-- Runtime API never uses this role — see sql/003_roles.sql for vex_founder_ro grants.
-- Migrations (sql/001, sql/002, sql/003) run using this same vex_raptor connection
-- (MIGRATION_DATABASE_URL in .env), never vex_founder_rw.

GRANT CREATE ON DATABASE vex_raptor TO vex_raptor;
-- (vex_raptor is already superuser/owner — this file no longer grants elevated
-- schema ownership or public.* table access to vex_founder_rw. See CIERRE below
-- for the exact REVOKE statements the user must run manually in production to
-- undo the previous over-broad grants.)
