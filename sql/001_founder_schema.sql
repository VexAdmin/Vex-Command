-- Vex Command — schema founder
-- Designed for 1.000 orgs. Never store finding payloads here.
-- Roles (prod): vex_founder_ro SELECT aggregates + founder.*
--               vex_founder_rw DML only on founder.*

CREATE SCHEMA IF NOT EXISTS founder;

CREATE TABLE IF NOT EXISTS founder.operator (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT,
    email           TEXT NOT NULL UNIQUE,
    role            TEXT NOT NULL CHECK (role IN ('founder', 'platform_operator', 'founder_readonly')),
    mfa_enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS founder.deal (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    org_id          BIGINT,
    stage           TEXT NOT NULL CHECK (stage IN (
                        'lead', 'qualified', 'pilot', 'negotiation', 'won', 'lost'
                    )),
    acv_usd         NUMERIC(12,2) NOT NULL DEFAULT 0,
    probability     SMALLINT NOT NULL DEFAULT 10 CHECK (probability BETWEEN 0 AND 100),
    source          TEXT NOT NULL DEFAULT 'inbound',
    region          TEXT,
    partner_org_id  BIGINT,
    close_date      DATE,
    win_loss_reason TEXT,
    owner_email     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS deal_stage_idx ON founder.deal (stage);
CREATE INDEX IF NOT EXISTS deal_org_idx ON founder.deal (org_id);

CREATE TABLE IF NOT EXISTS founder.deal_activity (
    id              BIGSERIAL PRIMARY KEY,
    deal_id         BIGINT NOT NULL REFERENCES founder.deal(id) ON DELETE CASCADE,
    kind            TEXT NOT NULL CHECK (kind IN ('note', 'demo', 'email', 'proposal', 'followup')),
    body            TEXT NOT NULL,
    actor_email     TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS founder.account_note (
    id              BIGSERIAL PRIMARY KEY,
    org_id          BIGINT NOT NULL,
    body            TEXT NOT NULL,
    actor_email     TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS account_note_org_idx ON founder.account_note (org_id, created_at DESC);

CREATE TABLE IF NOT EXISTS founder.goal (
    id              BIGSERIAL PRIMARY KEY,
    period          TEXT NOT NULL,
    kpi             TEXT NOT NULL,
    target          NUMERIC(14,2) NOT NULL,
    current         NUMERIC(14,2) NOT NULL DEFAULT 0,
    unit            TEXT NOT NULL DEFAULT 'usd',
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS founder.okr (
    id              BIGSERIAL PRIMARY KEY,
    quarter         TEXT NOT NULL,
    title           TEXT NOT NULL,
    target          NUMERIC(14,2) NOT NULL,
    current         NUMERIC(14,2) NOT NULL DEFAULT 0,
    unit            TEXT NOT NULL DEFAULT 'usd'
);

INSERT INTO founder.okr (quarter, title, target, current, unit)
SELECT * FROM (VALUES
    ('Q3 2026', 'First 10 paying logos', 10::numeric, 0::numeric, 'count'),
    ('Q3 2026', 'Stripe live (PRICE-01c)', 1::numeric, 0::numeric, 'count'),
    ('Q3 2026', 'COGS Gemini (PRICE-00)', 1::numeric, 0::numeric, 'count')
) AS v(quarter, title, target, current, unit)
WHERE NOT EXISTS (SELECT 1 FROM founder.okr);

INSERT INTO founder.goal (period, kpi, target, current, unit)
SELECT 'Q3 2026', 'net_new_mrr', 25000, 0, 'usd'
WHERE NOT EXISTS (SELECT 1 FROM founder.goal WHERE kpi = 'net_new_mrr');

CREATE TABLE IF NOT EXISTS founder.alert_rule (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    predicate       TEXT NOT NULL,
    channel         TEXT NOT NULL DEFAULT 'slack',
    enabled         BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS founder.alert_event (
    id              BIGSERIAL PRIMARY KEY,
    rule_id         BIGINT REFERENCES founder.alert_rule(id),
    severity        TEXT NOT NULL CHECK (severity IN ('info', 'warn', 'crit')),
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    fired_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    acked_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS founder.manual_revenue (
    id              BIGSERIAL PRIMARY KEY,
    org_id          BIGINT,
    period_month    DATE NOT NULL,
    mrr_usd         NUMERIC(12,2) NOT NULL,
    reason          TEXT NOT NULL,
    actor_email     TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS founder.cogs_daily (
    day             DATE NOT NULL,
    org_id          BIGINT,
    gemini_usd      NUMERIC(12,4) NOT NULL DEFAULT 0,
    infra_usd       NUMERIC(12,4) NOT NULL DEFAULT 0,
    scans           INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, org_id)
);

CREATE TABLE IF NOT EXISTS founder.nps_response (
    id              BIGSERIAL PRIMARY KEY,
    org_id          BIGINT NOT NULL,
    score           SMALLINT NOT NULL CHECK (score BETWEEN 0 AND 10),
    comment         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS founder.support_thread (
    id              BIGSERIAL PRIMARY KEY,
    org_id          BIGINT,
    org_name        TEXT NOT NULL,
    title           TEXT NOT NULL,
    priority        TEXT NOT NULL CHECK (priority IN ('P1', 'P2', 'P3')),
    status          TEXT NOT NULL DEFAULT 'open',
    source          TEXT NOT NULL DEFAULT 'email',
    opened_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    first_reply_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS founder.audit_log (
    id              BIGSERIAL PRIMARY KEY,
    actor_email     TEXT NOT NULL,
    action          TEXT NOT NULL,
    org_id          BIGINT,
    path            TEXT,
    ip              TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_log_org_idx ON founder.audit_log (org_id, created_at DESC);

-- Warehouse-shaped tables (Postgres stand-in until ClickHouse @ 200–1.000 orgs).
-- Grain documented in docs/RESOURCES_1000.md. No finding text.

CREATE TABLE IF NOT EXISTS founder.dim_org (
    org_id          BIGINT PRIMARY KEY,
    name            TEXT NOT NULL,
    plan            TEXT NOT NULL,
    region          TEXT,
    channel         TEXT,
    stage           TEXT NOT NULL,
    partner_org_id  BIGINT,
    created_at      TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS founder.fact_mrr_daily (
    day             DATE NOT NULL,
    org_id          BIGINT NOT NULL,
    mrr_usd         NUMERIC(12,2) NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    PRIMARY KEY (day, org_id)
);

CREATE TABLE IF NOT EXISTS founder.fact_usage_daily (
    day             DATE NOT NULL,
    org_id          BIGINT NOT NULL,
    scans           INTEGER NOT NULL DEFAULT 0,
    findings_hc     INTEGER NOT NULL DEFAULT 0,
    logins          INTEGER NOT NULL DEFAULT 0,
    reports         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, org_id)
);

CREATE TABLE IF NOT EXISTS founder.fact_billing_event (
    id              BIGSERIAL PRIMARY KEY,
    occurred_at     TIMESTAMPTZ NOT NULL,
    org_id          BIGINT,
    kind            TEXT NOT NULL,
    amount_usd      NUMERIC(12,2),
    stripe_id       TEXT
);

CREATE TABLE IF NOT EXISTS founder.agg_platform_hourly (
    hour            TIMESTAMPTZ PRIMARY KEY,
    arq_depth       INTEGER NOT NULL DEFAULT 0,
    orphaned_running INTEGER NOT NULL DEFAULT 0,
    errors_5xx      INTEGER NOT NULL DEFAULT 0,
    gemini_usd      NUMERIC(12,4) NOT NULL DEFAULT 0
);
