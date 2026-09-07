-- Aggregate views over Raptor OLTP. NEVER select findings payloads.
-- Requires: public.organizations, public.scan_history, public.users

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
    COALESCE(sa.last_scan_at, o.created_at) AS last_active_at,
    COALESCE(uc.seats, 0)::int AS seats,
    COALESCE(uc.last_login_at, o.created_at) AS last_login_at
FROM public.organizations o
LEFT JOIN (
    SELECT
        sh.org_id,
        COUNT(*) FILTER (
            WHERE sh.started_at::timestamptz >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
        ) AS scans_30d,
        COALESCE(SUM(sh.finding_count) FILTER (
            WHERE sh.started_at::timestamptz >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
        ), 0) AS findings_30d,
        MAX(sh.started_at::timestamptz) AS last_scan_at
    FROM public.scan_history sh
    WHERE sh.org_id IS NOT NULL
    GROUP BY sh.org_id
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
FROM public.scan_history;

CREATE OR REPLACE VIEW founder.v_usage_platform AS
SELECT
    COUNT(DISTINCT org_id) FILTER (
        WHERE started_at::timestamptz >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '7 days'
        AND org_id IS NOT NULL
    )::int AS wau_orgs,
    COUNT(*) FILTER (
        WHERE started_at::timestamptz >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '30 days'
    )::int AS scans_30d
FROM public.scan_history;
