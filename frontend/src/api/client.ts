const BASE = import.meta.env.VITE_API_BASE || ''

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem('founder_token') || import.meta.env.VITE_FOUNDER_TOKEN || ''
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api/founder/v1${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(init?.headers || {}),
    },
  })
  if (res.status === 401 || res.status === 403) {
    throw new Error(`auth:${res.status}`)
  }
  if (!res.ok) throw new Error(`${res.status} ${path}`)
  return res.json() as Promise<T>
}

export function exportAccounting(): void {
  const base = import.meta.env.VITE_API_BASE || ''
  const token = localStorage.getItem('founder_token') || import.meta.env.VITE_FOUNDER_TOKEN || ''
  const url = new URL(`${base}/api/founder/v1/exports/accounting.csv`)
  if (token) url.searchParams.set('token', token)
  window.location.href = url.toString()
}
