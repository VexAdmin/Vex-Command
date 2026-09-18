import { describe, expect, it } from 'vitest'
import { ApiError } from '@/api/client'
import { targetAddErrorMessage, targetRemoveErrorMessage } from './targetErrors'

describe('targetErrors', () => {
  it('maps duplicate to Spanish message', () => {
    const err = new ApiError(422, '/customers/1/targets', {
      code: 'duplicate',
      message: 'Ese target ya está en la lista autorizada.',
    })
    expect(targetAddErrorMessage(err)).toBe('Ese target ya está en la lista autorizada.')
  })

  it('maps raptor proxy failure distinctly from format errors', () => {
    const err = new ApiError(502, '/customers/1/targets', {
      code: 'raptor_unavailable',
      message: 'Raptor no disponible. Reintenta más tarde.',
    })
    expect(targetAddErrorMessage(err)).toBe('No se pudo guardar en Raptor. Reintenta en unos minutos.')
  })

  it('maps remove-not-found', () => {
    const err = new ApiError(404, '/customers/1/targets', {
      code: 'not_found',
      message: 'Ese target no está en la lista autorizada.',
    })
    expect(targetRemoveErrorMessage(err)).toBe('Ese target no está en la lista autorizada.')
  })

  it('falls back to upstream message when code is unknown', () => {
    const err = new ApiError(403, '/customers/1/targets', {
      message: 'Insufficient Permissions: Administrator role required.',
    })
    expect(targetAddErrorMessage(err)).toBe('Insufficient Permissions: Administrator role required.')
  })

  it('maps string FastAPI detail to user-visible message', () => {
    const err = new ApiError(500, '/customers/1/targets', 'Internal Server Error')
    expect(targetAddErrorMessage(err)).toBe('Internal Server Error')
  })
})
