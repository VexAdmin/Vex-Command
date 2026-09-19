-- Oleada 0 — operational metadata per org (Command-only, no Raptor schema).

CREATE TABLE IF NOT EXISTS founder.account_ops (
    org_id          BIGINT PRIMARY KEY,
    pilot_stage     TEXT NOT NULL DEFAULT 'pilot'
        CHECK (pilot_stage IN ('discovery', 'pilot', 'production', 'paused')),
    next_step       TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by      TEXT
);

GRANT SELECT, INSERT, UPDATE ON founder.account_ops TO vex_founder_ro;
