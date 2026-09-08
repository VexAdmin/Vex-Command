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

export async function exportAccounting(): Promise<void> {
  const base = import.meta.env.VITE_API_BASE || ''
  const res = await fetch(`${base}/api/founder/v1/exports/accounting.csv`, {
    headers: authHeaders(),
  })
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
