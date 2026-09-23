# ⚠️ RAPTOR TOUCH — Borrado de organización

Command llama a este endpoint tras confirmación `eliminar` en la UI.

## Contrato propuesto

```
DELETE /api/v1/orgs/{org_id}
Authorization: Bearer <mismo JWT de platform_operator que org config>
```

**Respuestas:**

| Código | Significado |
|--------|-------------|
| 204 | Org y dependencias borradas (o soft-delete completado) |
| 403 | No platform_operator |
| 404 | Org no existe |
| 409 | Conflicto — p. ej. scan `running` (mensaje en body) |
| 501 | No implementado aún |

**Body opcional (JSON):** `{ "reason": "GDPR request #123" }` — Command lo reenvía si Raptor lo acepta.

## Orden de borrado en Raptor (implementación sugerida)

1. Rechazar si hay `scan_history.status = running` para esa org.
2. Hijos (`users`, `org_configs`, `scan_history`, …) según FKs del schema.
3. `organizations` al final.
4. Log/audit en Raptor (quién borró).

Command, tras 204, ejecuta `SELECT founder.f_purge_org_command_data(:org_id)` y escribe `founder.audit_log`.

## Deploy

1. Implementar y desplegar en **vex-raptor** primero.
2. Probar con org de prueba en staging.
3. Desplegar **vex-founder** (UI ya preparada).
