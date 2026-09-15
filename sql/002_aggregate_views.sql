-- Aggregate views over Raptor OLTP. NEVER select findings payloads.
-- Requires: public.organizations, public.users, public.scan_history, public.scan_metrics (optional)

CREATE OR REPLACE FUNCTION founder.scan_ts(raw text)
RETURNS timestamptz
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF raw IS NULL OR trim(raw) = '' THEN
        RETURN NULL;
    END IF;
    RETURN raw::timestamptz;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$;

-- RLS on scan_history/scan_metrics (Raptor T-22) hides rows from vex_founder_ro,
-- which has no bypass. These SECURITY DEFINER functions run as the schema owner
-- (bypasses RLS) but expose ONLY the columns founder needs — NEVER `findings`
-- (the raw pentest payload). Same pattern as founder.f_org_targets.
CREATE OR REPLACE FUNCTION founder.f_scan_history()
RETURNS TABLE(
    org_id integer,
    id varchar,
    target varchar,
    status varchar,
    started_at varchar,
    finished_at varchar,
    finding_count integer,
    user_email varchar
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
    SELECT org_id, id, target, status, started_at, finished_at, finding_count, user_email
    FROM public.scan_history;
$$;

REVOKE ALL ON FUNCTION founder.f_scan_history() FROM public;

-- scan_metrics is OPTIONAL (not every deployment has it — see file header).
-- plpgsql + dynamic SQL so CREATE FUNCTION itself doesn't fail to parse/validate
-- when the table is absent (unlike a static LANGUAGE sql body).
CREATE OR REPLACE FUNCTION founder.f_scan_metrics()
RETURNS TABLE(
    org_id integer,
    scan_id varchar,
    scan_type varchar,
    findings integer,
    created_at timestamptz
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'scan_metrics'
    ) THEN
        RETURN;
    END IF;
    RETURN QUERY EXECUTE
        'SELECT org_id, scan_id, scan_type, findings, created_at FROM public.scan_metrics';
END;
$$;

REVOKE ALL ON FUNCTION founder.f_scan_metrics() FROM public;

-- Attribute scans to orgs: org_id on row, user email fallback, or scan_metrics when history row missing.
CREATE OR REPLACE VIEW founder.v_scan_attribution AS
WITH history AS (
    SELECT
        COALESCE(sh.org_id, u.org_id) AS org_id,
        sh.id,
        sh.target,
        sh.status,
        sh.started_at,
        sh.finished_at,
        COALESCE(sh.finding_count, 0) AS finding_count,
        sh.user_email
    FROM founder.f_scan_history() sh
    LEFT JOIN public.users u ON lower(u.email) = lower(sh.user_email)
    WHERE COALESCE(sh.org_id, u.org_id) IS NOT NULL
),
metrics_only AS (
    SELECT
        sm.org_id,
        sm.scan_id AS id,
        COALESCE(NULLIF(trim(sh.target), ''), sm.scan_type, sm.scan_id) AS target,
        COALESCE(sh.status, 'completed') AS status,
        COALESCE(
            NULLIF(trim(sh.started_at), ''),
            to_char(sm.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
        ) AS started_at,
        sh.finished_at,
        COALESCE(sh.finding_count, sm.findings, 0) AS finding_count,
        COALESCE(sh.user_email, '') AS user_email
    FROM founder.f_scan_metrics() sm
    LEFT JOIN founder.f_scan_history() sh ON sh.id = sm.scan_id
    WHERE sm.org_id IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM history h WHERE h.id = sm.scan_id)
)
SELECT * FROM history
UNION ALL
SELECT * FROM metrics_only;

CREATE OR REPLACE VIEW founder.v_org_summary AS
SELECT
    o.id AS org_id,
    o.name,
    o.plan,
    o.is_active,
    o.created_at,
    COALESCE(sa.scans_30d, 0)::int AS scans_30d,
    COALESCE(sa.findings_30d, 0)::int AS findings_hc_30d,
    0::int AS reports_30d,
    COALESCE(
        GREATEST(sa.last_scan_at, uc.last_login_at),
        o.created_at
    ) AS last_active_at,
    COALESCE(uc.seats, 0)::int AS seats,
    COALESCE(uc.last_login_at, o.created_at) AS last_login_at
FROM public.organizations o
LEFT JOIN (
    SELECT
        sa.org_id,
        COUNT(*) FILTER (
            WHERE founder.scan_ts(sa.started_at) >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
        ) AS scans_30d,
        COALESCE(SUM(sa.finding_count) FILTER (
            WHERE founder.scan_ts(sa.started_at) >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
        ), 0) AS findings_30d,
        MAX(founder.scan_ts(sa.started_at)) AS last_scan_at
    FROM founder.v_scan_attribution sa
    GROUP BY sa.org_id
) sa ON sa.org_id = o.id
LEFT JOIN (
    SELECT
        u.org_id,
        COUNT(*)::int AS seats,
        MAX(u.last_login) AS last_login_at
    FROM public.users u
    WHERE u.org_id IS NOT NULL
    GROUP BY u.org_id
) uc ON uc.org_id = o.id
WHERE o.id > 0;

CREATE OR REPLACE VIEW founder.v_platform_scan_ops AS
SELECT
    COUNT(*) FILTER (WHERE status = 'running')::int AS running_scans,
    COUNT(*) FILTER (
        WHERE status = 'running'
        AND founder.scan_ts(started_at) < (NOW() AT TIME ZONE 'UTC') - INTERVAL '2 hours'
    )::int AS orphaned_running,
    COUNT(*) FILTER (
        WHERE founder.scan_ts(started_at) >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days'
    )::int AS scans_7d,
    COALESCE(SUM(finding_count) FILTER (
        WHERE founder.scan_ts(started_at) >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days'
    ), 0)::int AS findings_hc_7d
FROM founder.v_scan_attribution;

CREATE OR REPLACE VIEW founder.v_usage_platform AS
SELECT
    COUNT(DISTINCT org_id) FILTER (
        WHERE founder.scan_ts(started_at) >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days'
    )::int AS wau_orgs,
    COUNT(*) FILTER (
        WHERE founder.scan_ts(started_at) >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
    )::int AS scans_30d
FROM founder.v_scan_attribution;

-- org_configs is OPTIONAL locally (dev stub doesn't create it) but required in
-- prod (Raptor RLS). plpgsql + dynamic SQL so CREATE FUNCTION doesn't fail to
-- parse/validate when the table is absent — same reasoning as f_scan_metrics.
CREATE OR REPLACE FUNCTION founder.f_org_targets()
RETURNS TABLE(org_id integer, allowed_targets text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'org_configs'
    ) THEN
        RETURN;
    END IF;
    RETURN QUERY EXECUTE
        'SELECT org_id, allowed_targets FROM public.org_configs';
END;
$$;

REVOKE ALL ON FUNCTION founder.f_org_targets() FROM public;

CREATE OR REPLACE VIEW founder.v_org_targets AS
SELECT * FROM founder.f_org_targets();
