-- Minimal Raptor-shaped tables for local dev / tests without full Vex Raptor DB.
-- Never used in production when attached to real Raptor Postgres.

CREATE TABLE IF NOT EXISTS public.organizations (
    id              SERIAL PRIMARY KEY,
    public_id       VARCHAR(36) NOT NULL DEFAULT gen_random_uuid()::text,
    name            VARCHAR(255) NOT NULL UNIQUE,
    plan            VARCHAR(50) NOT NULL DEFAULT 'essential',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    scans_today     INT DEFAULT 0,
    scans_today_date VARCHAR(10),
    llm_region      VARCHAR(8),
    inactivity_alerts_enabled BOOLEAN DEFAULT FALSE,
    last_inactivity_alert_scan_at VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS public.users (
    id              SERIAL PRIMARY KEY,
    public_id       VARCHAR(36) NOT NULL DEFAULT gen_random_uuid()::text,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL DEFAULT 'x',
    role            VARCHAR(50) NOT NULL DEFAULT 'viewer',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login      TIMESTAMPTZ,
    org_id          INT REFERENCES public.organizations(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS public.scan_history (
    id              VARCHAR(36) PRIMARY KEY,
    user_email      VARCHAR(255) NOT NULL,
    target          VARCHAR(2048) NOT NULL,
    tools           TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at      VARCHAR(50) NOT NULL,
    finished_at     VARCHAR(50),
    findings        TEXT,
    error_msg       TEXT,
    tool_count      INT,
    finding_count   INT,
    risk_score      INT DEFAULT 0,
    org_id          INT
);

CREATE INDEX IF NOT EXISTS ix_scan_history_org_id ON public.scan_history (org_id);
CREATE INDEX IF NOT EXISTS ix_scan_history_started_at ON public.scan_history (started_at);
