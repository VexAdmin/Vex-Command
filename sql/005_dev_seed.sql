-- Seed data for dev stub only (3 orgs, no billing).
INSERT INTO public.organizations (id, name, plan, is_active, created_at)
VALUES
    (1, 'Harbor Fintech Pilot', 'pilot', true, NOW() - INTERVAL '45 days'),
    (2, 'NovaSec MSSP', 'professional', true, NOW() - INTERVAL '120 days'),
    (3, 'Meridian Lab', 'essential', true, NOW() - INTERVAL '14 days')
ON CONFLICT (name) DO NOTHING;

SELECT setval(pg_get_serial_sequence('public.organizations', 'id'), GREATEST(3, (SELECT MAX(id) FROM public.organizations)));

INSERT INTO public.users (email, role, org_id, last_login)
VALUES
    ('admin@harbor.test', 'admin', 1, NOW() - INTERVAL '2 days'),
    ('viewer@nova.test', 'viewer', 2, NOW() - INTERVAL '1 days'),
    ('idle@meridian.test', 'viewer', 3, NOW() - INTERVAL '28 days')
ON CONFLICT (email) DO NOTHING;

INSERT INTO public.scan_history (id, user_email, target, status, started_at, finished_at, finding_count, org_id)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'admin@harbor.test', 'https://harbor.test', 'completed',
     (NOW() - INTERVAL '3 days')::text, (NOW() - INTERVAL '3 days')::text, 4, 1),
    ('22222222-2222-2222-2222-222222222222', 'viewer@nova.test', 'https://nova.test', 'completed',
     (NOW() - INTERVAL '1 days')::text, (NOW() - INTERVAL '1 days')::text, 12, 2),
    ('33333333-3333-3333-3333-333333333333', 'idle@meridian.test', 'https://meridian.test', 'running',
     (NOW() - INTERVAL '3 hours')::text, NULL, 0, 3),
    ('44444444-4444-4444-4444-444444444444', 'admin@harbor.test', 'https://legacy.harbor.test', 'completed',
     (NOW() - INTERVAL '5 days')::text, (NOW() - INTERVAL '5 days')::text, 2, NULL)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.org_configs (org_id, allowed_targets)
VALUES
    (1, 'https://harbor.test, https://api.harbor.test'),
    (2, 'nova.test'),
    (3, NULL)
ON CONFLICT (org_id) DO NOTHING;

INSERT INTO public.scan_metrics (scan_id, org_id, scan_type, findings, critical, high, created_at)
VALUES
    ('55555555-5555-5555-5555-555555555555', 3, 'pentest', 7, 1, 2, NOW() - INTERVAL '2 days')
ON CONFLICT (scan_id) DO NOTHING;
