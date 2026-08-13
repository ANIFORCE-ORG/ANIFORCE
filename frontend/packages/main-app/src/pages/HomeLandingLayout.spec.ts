import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./Home.vue', import.meta.url), 'utf8')

describe('Home landing layout', () => {
  it('places the welcome and quick-start group lower while keeping the composer bottom anchored', () => {
    expect(source).toContain('padding: clamp(154px, calc(14vh + 50px), 182px) 24px 22px;')
    expect(source).toContain('margin: auto auto 0;')
    expect(source).toContain('@media (max-width: 980px)')
    expect(source).toContain('padding-top: 48px;')
  })
})
