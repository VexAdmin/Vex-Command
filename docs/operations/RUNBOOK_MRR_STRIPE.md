# Runbook — MRR en Command vs Stripe

**Estado:** F3 (C-20–C-24) en pausa hasta definir precios de planes. Hoy Command muestra
MRR desde `founder.manual_revenue` (ledger offline) y **no** reconcilia con Stripe.

## Cuando Stripe esté activo (futuro)

1. **Fuente canónica:** eventos firmados de Stripe → `fact_billing_event` (C-21) en Raptor/warehouse.
2. **Command:** `backend/app/kpis.py` — MRR/ARR deben coincidir con Stripe ± overrides auditados en `manual_revenue`.
3. **Si no cuadra:**
   - Revisar último webhook en Stripe Dashboard (eventos `invoice.paid`, `customer.subscription.updated`).
   - Comparar `GET /api/founder/v1/overview` (`mrr`, `dataset`) con Stripe MRR del periodo.
   - Buscar entradas recientes en `founder.manual_revenue` (override manual).
   - Confirmar que el mes contable usa `period_month` en UTC/coherente con finance.

## Hoy (pre-revenue)

- `dataset=pre_revenue` en overview es **honesto** — no indica fallo de integración.
- Ingresos manuales: pantalla **Ingresos** / API manual revenue; cada fila requiere `reason` y queda en audit.
