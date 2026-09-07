export function money(n: number, digits = 0): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: digits,
  }).format(n)
}

export function pct(n: number, digits = 1): string {
  return `${(n * 100).toFixed(digits)}%`
}

export function num(n: number): string {
  return new Intl.NumberFormat('en-US').format(n)
}

export function healthColor(h: number): string {
  if (h < 50) return 'var(--bad)'
  if (h < 75) return 'var(--warn)'
  return 'var(--good)'
}
