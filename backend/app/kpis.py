"""Canonical KPI formulas — UI only formats, never redefines."""

from __future__ import annotations


def arr(mrr: float) -> float:
    return mrr * 12


def net_new_mrr(new: float, expansion: float, contraction: float, churn: float) -> float:
    return new + expansion - contraction - churn


def logo_churn(lost: int, start: int) -> float:
    return 0.0 if start <= 0 else lost / start


def revenue_churn(lost_mrr: float, start_mrr: float) -> float:
    return 0.0 if start_mrr <= 0 else lost_mrr / start_mrr


def nrr(start_mrr: float, expansion: float, contraction: float, churn: float) -> float:
    if start_mrr <= 0:
        return 0.0
    return (start_mrr + expansion - contraction - churn) / start_mrr


def gross_margin(revenue: float, gemini: float, infra: float) -> float:
    if revenue <= 0:
        return 0.0
    return (revenue - gemini - infra) / revenue


def org_health(recency: float, payment: float, usage: float, support: float) -> float:
    """0–100. Weights: recency 40%, payment 30%, usage 20%, support 10%."""
    return max(0.0, min(100.0, recency * 0.40 + payment * 0.30 + usage * 0.20 + support * 0.10))
