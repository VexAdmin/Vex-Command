# Command ↔ Raptor boundary

**Oleada 0+** features should stay in **Vex-Command** (schema `founder`, aggregate SQL views, UI).

## Do not change Vex-Raptor unless explicitly approved

| Needs Raptor code/deploy | Command-only (preferred) |
|--------------------------|---------------------------|
| New tenant APIs, RLS session fixes | `founder.*` tables, views, audit |
| Reading `org_configs` via HTTP for display | `founder.v_org_targets` |
| Target **mutations** (PATCH config) | Target timeline from `founder.v_audit_log` |

When a task requires Raptor, stop and flag: **⚠️ RAPTOR TOUCH** — describe endpoint/schema impact before editing `Proyecto Vex-Raptor`.
