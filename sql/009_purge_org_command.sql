-- Purge Command-side founder data after Raptor deletes the org (GDPR / test cleanup).

CREATE OR REPLACE FUNCTION founder.f_purge_org_command_data(p_org_id BIGINT)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = founder, public
AS $$
BEGIN
    DELETE FROM founder.deal_activity
    WHERE deal_id IN (SELECT id FROM founder.deal WHERE org_id = p_org_id);

    DELETE FROM founder.deal WHERE org_id = p_org_id;
    DELETE FROM founder.account_note WHERE org_id = p_org_id;
    DELETE FROM founder.account_ops WHERE org_id = p_org_id;
    DELETE FROM founder.account_checklist WHERE org_id = p_org_id;
    DELETE FROM founder.manual_revenue WHERE org_id = p_org_id;
END;
$$;

GRANT EXECUTE ON FUNCTION founder.f_purge_org_command_data(BIGINT) TO vex_founder_ro;
