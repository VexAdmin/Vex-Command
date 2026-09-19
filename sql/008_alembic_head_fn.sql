-- Read Raptor migration head without granting vex_founder_ro on public.alembic_version.

CREATE OR REPLACE FUNCTION founder.f_alembic_head()
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    head text;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'alembic_version'
    ) THEN
        RETURN NULL;
    END IF;
    SELECT version_num INTO head FROM alembic_version LIMIT 1;
    RETURN head;
END;
$$;

GRANT EXECUTE ON FUNCTION founder.f_alembic_head() TO vex_founder_ro;
