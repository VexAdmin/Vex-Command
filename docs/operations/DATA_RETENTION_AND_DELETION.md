# Retención y borrado de datos (borrador operativo)

> No sustituye asesoría legal. Ajustar con contrato SaaS y DPA antes de publicar al cliente.

## Principios

1. **Impago / churn** — suspender producto; **no** borrar de forma automática el día del cancel.
2. **Petición del cliente** (GDPR art. 17, fin de contrato) — borrado **bajo demanda** con trazabilidad.
3. **Orgs de prueba** — mismo mecanismo de borrado, motivo documentado en audit.

## Plazos sugeridos (pendiente legal)

| Situación | Acción producto | Datos |
|-----------|-----------------|--------|
| Cancelación voluntaria | `pilot_stage=paused`, login suspendido en Raptor | Retener **12 meses** salvo otra cosa en contrato |
| Impago | Igual + dunning Stripe (F3) | Igual |
| Solicitud de supresión | Botón Command + ticket interno | Borrar en Raptor + purgar `founder.*` (salvo audit mínimo) |
| Org de prueba interna | Borrado cuando ya no sirve | Inmediato tras confirmación |

## Qué borra cada sistema

| Capa | Responsable | Contenido |
|------|-------------|-----------|
| **Raptor** | `DELETE /api/v1/orgs/{id}` (platform_operator) | `organizations`, usuarios, scans, configs, etc. |
| **Command** | `founder.f_purge_org_command_data(org_id)` | Notas, ops, checklist, deals ligados, manual_revenue |
| **Audit** | Se conserva fila `customers.org.delete` | Quién, cuándo, org_id, motivo (sin findings) |

## Uso del botón en Account 360

- Escribir **`eliminar`** y opcionalmente **motivo** (ticket GDPR, “org test”).
- Irreversible en Raptor una vez el endpoint esté desplegado.
- Si Raptor aún no tiene el endpoint, Command responde error claro — ver `RAPTOR_ORG_DELETE_API.md`.
