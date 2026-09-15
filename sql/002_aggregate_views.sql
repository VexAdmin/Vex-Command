-- Aggregate views over Raptor OLTP. NEVER select findings payloads.
-- Requires: public.organizations, public.scan_history, public.users

-- Attribute scans to orgs: direct org_id or legacy rows matched by user email (Raptor parity).
CREATE OR REPLACE VIEW founder.v_scan_attribution AS
SELECT
    COALESCE(sh.org_id, u.org_id) AS org_id,
    sh.id,
    sh.target,
    sh.status,
    sh.started_at,
    sh.finished_at,
    COALESCE(sh.finding_count, 0) AS finding_count,
    sh.user_email
FROM public.scan_history sh
LEFT JOIN public.users u
    ON sh.org_id IS NULL AND lower(u.email) = lower(sh.user_email)
WHERE COALESCE(sh.org_id, u.org_id) IS NOT NULL;

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
            WHERE sa.started_at::timestamptz >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
        ) AS scans_30d,
        COALESCE(SUM(sa.finding_count) FILTER (
            WHERE sa.started_at::timestamptz >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
        ), 0) AS findings_30d,
        MAX(sa.started_at::timestamptz) AS last_scan_at
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
        AND started_at::timestamptz < (NOW() AT TIME ZONE 'UTC') - INTERVAL '2 hours'
    )::int AS orphaned_running,
    COUNT(*) FILTER (
        WHERE started_at::timestamptz >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days'
    )::int AS scans_7d,
    COALESCE(SUM(finding_count) FILTER (
        WHERE started_at::timestamptz >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days'
    ), 0)::int AS findings_hc_7d
FROM founder.v_scan_attribution;

CREATE OR REPLACE VIEW founder.v_usage_platform AS
SELECT
    COUNT(DISTINCT org_id) FILTER (
        WHERE started_at::timestamptz >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days'
    )::int AS wau_orgs,
    COUNT(*) FILTER (
        WHERE started_at::timestamptz >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
    )::int AS scans_30d
FROM founder.v_scan_attribution;
