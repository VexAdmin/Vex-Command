import { describe, expect, it } from 'vitest'
import { money, pct } from './format'

describe('format', () => {
  it('formats money', () => {
    expect(money(402000)).toBe('$402,000')
  })
  it('formats percent', () => {
    expect(pct(0.78, 0)).toBe('78%')
  })
})
