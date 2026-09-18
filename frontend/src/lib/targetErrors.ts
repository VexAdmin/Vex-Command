import { ApiError } from '@/api/client'

export function targetAddErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'duplicate':
        return 'Ese target ya está en la lista autorizada.'
      case 'invalid_format':
        return 'Formato inválido. Usa un dominio (ej. ejemplo.com), URL https://… o CIDR.'
      case 'allowlist_too_long':
        return 'La lista supera el límite de 2000 caracteres.'
      case 'raptor_unavailable':
        return 'No se pudo guardar en Raptor. Reintenta en unos minutos.'
      case 'raptor_rejected':
        return 'Raptor rechazó el cambio. Verifica el formato o contacta soporte.'
      case 'raptor_forbidden':
        return 'Sin permisos para editar targets de esta organización en Raptor.'
      case 'auth':
        return 'Sesión expirada o sin permisos. Vuelve a iniciar sesión.'
      case 'rate_limited':
        return 'Demasiados cambios seguidos. Espera unos minutos.'
      case 'org_not_found':
        return 'Organización no encontrada en Raptor.'
      default:
        if (error.userMessage) return error.userMessage
        if (error.message && !/^\d{3}\s\/customers\//.test(error.message)) {
          return error.message
        }
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return 'No se pudo agregar el target.'
}

export function targetRemoveErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case 'not_found':
        return 'Ese target no está en la lista autorizada.'
      case 'raptor_unavailable':
        return 'No se pudo guardar en Raptor. Reintenta en unos minutos.'
      case 'raptor_forbidden':
        return 'Sin permisos para editar targets de esta organización en Raptor.'
      case 'auth':
        return 'Sesión expirada o sin permisos. Vuelve a iniciar sesión.'
      case 'rate_limited':
        return 'Demasiados cambios seguidos. Espera unos minutos.'
      default:
        if (error.userMessage) return error.userMessage
        if (error.message && !/^\d{3}\s\/customers\//.test(error.message)) {
          return error.message
        }
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return 'No se pudo quitar el target.'
}
