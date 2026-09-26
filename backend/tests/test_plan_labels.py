from app.providers.sql import PLAN_LABEL, _org_billing_stage


def test_eval_and_free_are_eval_tier():
    assert PLAN_LABEL["eval"] == "Eval"
    assert PLAN_LABEL["free"] == "Eval"
    assert _org_billing_stage("eval") == "eval"
    assert _org_billing_stage("free") == "eval"


def test_essential_is_paid_stage():
    assert PLAN_LABEL["essential"] == "Essential"
    assert _org_billing_stage("essential") == "paid"
