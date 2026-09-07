from app.kpis import arr, gross_margin, net_new_mrr, nrr, org_health


def test_canonical_kpis():
    assert arr(402_000) == 4_824_000
    assert net_new_mrr(22100, 8600, 3200, 9100) == 18400
    assert round(nrr(100, 20, 5, 5), 2) == 1.10
    assert round(gross_margin(100, 14, 8), 2) == 0.78
    h = org_health(100, 100, 100, 100)
    assert h == 100
