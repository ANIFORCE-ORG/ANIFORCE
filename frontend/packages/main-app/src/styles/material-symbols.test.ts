import { existsSync, readFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const appRoot = fileURLToPath(new URL('../..', import.meta.url))
const indexHtml = readFileSync(`${appRoot}/index.html`, 'utf8')
const globalCss = readFileSync(`${appRoot}/src/styles/global.css`, 'utf8')
const localFontPath = `${appRoot}/public/fonts/material-symbols-outlined.woff2`

describe('Material Symbols font', () => {
  it('is self-hosted so icon ligatures render without Google Fonts', () => {
    expect(indexHtml).not.toMatch(/fonts\.googleapis\.com[^\n]*Material\+Symbols/i)
    expect(globalCss).toContain("font-family: 'Material Symbols Outlined'")
    expect(globalCss).toContain("url('/fonts/material-symbols-outlined.woff2')")
    expect(existsSync(localFontPath)).toBe(true)
    expect(statSync(localFontPath).size).toBeGreaterThan(10_000)
  })
})
