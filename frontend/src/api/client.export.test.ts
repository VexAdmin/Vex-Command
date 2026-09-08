import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { exportAccounting } from './client'

// H1 regression test: exportAccounting must send the JWT via a real
// Authorization header (fetch + blob), never as a ?token= query param
// on window.location.href — a GET navigation can't carry that header,
// so the old code silently 401'd against FOUNDER_AUTH_MODE=jwt in prod.
// No jsdom environment configured for this project, so document/localStorage
// are stubbed directly rather than switching the whole suite to jsdom.

describe('exportAccounting', () => {
  let clickSpy: ReturnType<typeof vi.fn<() => void>>
  let createObjectURLSpy: ReturnType<typeof vi.fn>
  let revokeObjectURLSpy: ReturnType<typeof vi.fn>
  let anchorStub: { href: string; download: string; click: () => void }

  beforeEach(() => {
    const store: Record<string, string> = { founder_token: 'test.jwt.token' }
    vi.stubGlobal('localStorage', {
      getItem: (k: string) => store[k] ?? null,
      setItem: (k: string, v: string) => {
        store[k] = v
      },
      clear: () => {
        for (const k of Object.keys(store)) delete store[k]
      },
    })

    clickSpy = vi.fn<() => void>()
    anchorStub = { href: '', download: '', click: () => clickSpy() }
    vi.stubGlobal('document', {
      createElement: vi.fn(() => anchorStub),
    })

    createObjectURLSpy = vi.fn(() => 'blob:mock-url')
    revokeObjectURLSpy = vi.fn()
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL: createObjectURLSpy,
      revokeObjectURL: revokeObjectURLSpy,
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('calls fetch with a real Authorization: Bearer header (not a ?token= query param)', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: async () => new Blob(['csv,data'], { type: 'text/csv' }),
    })
    vi.stubGlobal('fetch', fetchSpy)

    await exportAccounting()

    expect(fetchSpy).toHaveBeenCalledTimes(1)
    const [url, init] = fetchSpy.mock.calls[0]
    expect(String(url)).not.toContain('token=')
    expect(String(url)).toContain('/api/founder/v1/exports/accounting.csv')
    expect(init.headers.Authorization).toBe('Bearer test.jwt.token')
    expect(clickSpy).toHaveBeenCalledTimes(1)
    expect(createObjectURLSpy).toHaveBeenCalledTimes(1)
    expect(revokeObjectURLSpy).toHaveBeenCalledTimes(1)
  })

  it('throws on 401/403 instead of silently navigating', async () => {
    const fetchSpy = vi.fn().mockResolvedValue({ ok: false, status: 401 })
    vi.stubGlobal('fetch', fetchSpy)

    await expect(exportAccounting()).rejects.toThrow('auth:401')
  })
})
