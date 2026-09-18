const BASE = import.meta.env.VITE_API_BASE || ''

// S7: the Bearer/localStorage token is a dev convenience only — an XSS on the
// SPA can read localStorage but not the httpOnly session cookie Command sets.
// `import.meta.env.PROD` is true for any `vite build` output (what ops.
// serves), so this path never ships live even if VITE_FOUNDER_TOKEN or a
// stale localStorage entry is present.
function legacyToken(): string {
  if (import.meta.env.PROD) return ''
  return localStorage.getItem('founder_token') || import.meta.env.VITE_FOUNDER_TOKEN || ''
}

function authHeaders(): Record<string, string> {
  const token = legacyToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function refreshSession(): Promise<boolean> {
  const res = await fetch(`${BASE}/api/founder/v1/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
  return res.ok
}

async function fetchApi(path: string, init?: RequestInit, allowRefresh = true): Promise<Response> {
  const res = await fetch(`${BASE}/api/founder/v1${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(init?.headers || {}),
    },
  })
  if (allowRefresh && res.status === 401 && !path.startsWith('/auth/')) {
    if (await refreshSession()) {
      return fetch(`${BASE}/api/founder/v1${path}`, {
        ...init,
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
          ...(init?.headers || {}),
        },
      })
    }
  }
  return res
}

type ApiErrorDetail = string | { code?: string; message?: string }

export class ApiError extends Error {
  readonly status: number
  readonly path: string
  readonly code?: string
  readonly userMessage?: string

  constructor(status: number, path: string, detail?: ApiErrorDetail) {
    const parsed = parseApiErrorDetail(detail)
    super(parsed.message || `${status} ${path}`)
    this.name = 'ApiError'
    this.status = status
    this.path = path
    this.code = parsed.code
    this.userMessage = parsed.message
  }
}

function parseApiErrorDetail(detail?: ApiErrorDetail): { code?: string; message?: string } {
  if (!detail) return {}
  if (typeof detail === 'string') {
    return { message: detail }
  }
  return {
    code: detail.code,
    message: detail.message,
  }
}

async function readApiError(res: Response, path: string): Promise<ApiError> {
  let detail: ApiErrorDetail | undefined
  try {
    const body = await res.json()
    detail = body?.detail as ApiErrorDetail | undefined
  } catch {
    detail = undefined
  }
  return new ApiError(res.status, path, detail)
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetchApi(path, init)
  if (!res.ok) {
    throw await readApiError(res, path)
  }
  return res.json() as Promise<T>
}

export async function checkSession(): Promise<boolean> {
  const res = await fetchApi('/auth/me', undefined, false)
  if (res.ok) return true
  if (res.status === 401) return refreshSession()
  return false
}

export async function login(email: string, password: string): Promise<void> {
  const res = await fetch(`${BASE}/api/founder/v1/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (res.status === 403) throw new Error('auth:403')
  if (!res.ok) throw new Error('auth:401')
  localStorage.removeItem('founder_token')
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/api/founder/v1/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  })
  localStorage.removeItem('founder_token')
}

export async function exportAccounting(): Promise<void> {
  const base = import.meta.env.VITE_API_BASE || ''
  let res = await fetch(`${base}/api/founder/v1/exports/accounting.csv`, {
    credentials: 'include',
    headers: authHeaders(),
  })
  if (res.status === 401) {
    if (await refreshSession()) {
      res = await fetch(`${base}/api/founder/v1/exports/accounting.csv`, {
        credentials: 'include',
        headers: authHeaders(),
      })
    }
  }
  if (res.status === 401 || res.status === 403) {
    throw new Error(`auth:${res.status}`)
  }
  if (!res.ok) throw new Error(`${res.status} exports/accounting.csv`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'vex-founder-accounting.csv'
  anchor.click()
  URL.revokeObjectURL(url)
}
