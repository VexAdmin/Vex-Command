-- One-time after manual sql/001+002 as vex_raptor superuser.
-- Lets vex_founder_rw run migrate-on-startup and own founder objects.

GRANT CREATE ON DATABASE vex_raptor TO vex_founder_rw;
ALTER SCHEMA founder OWNER TO vex_founder_rw;
GRANT USAGE ON SCHEMA public TO vex_founder_rw;
GRANT SELECT ON public.organizations, public.users, public.scan_history, public.org_configs TO vex_founder_rw;

DO $$
DECLARE r RECORD;
BEGIN
  FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'founder'
  LOOP
    EXECUTE format('ALTER TABLE founder.%I OWNER TO vex_founder_rw', r.tablename);
  END LOOP;
  FOR r IN SELECT viewname FROM pg_views WHERE schemaname = 'founder'
  LOOP
    EXECUTE format('ALTER VIEW founder.%I OWNER TO vex_founder_rw', r.viewname);
  END LOOP;
  FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'founder'
  LOOP
    EXECUTE format('ALTER SEQUENCE founder.%I OWNER TO vex_founder_rw', r.sequencename);
  END LOOP;
END $$;
