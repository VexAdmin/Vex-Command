-- Oleada 2 — per-org operational checklist (Command-only).

CREATE TABLE IF NOT EXISTS founder.account_checklist (
    org_id                  BIGINT PRIMARY KEY,
    dpa_signed              BOOLEAN NOT NULL DEFAULT false,
    primary_contact_set     BOOLEAN NOT NULL DEFAULT false,
    kickoff_done            BOOLEAN NOT NULL DEFAULT false,
    scope_documented        BOOLEAN NOT NULL DEFAULT false,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by              TEXT
);

GRANT SELECT, INSERT, UPDATE ON founder.account_checklist TO vex_founder_ro;
