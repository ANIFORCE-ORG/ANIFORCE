import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const readSource = (path: string) =>
  readFileSync(new URL(path, import.meta.url), 'utf8')

const materialSource = readSource('../pages/creatives/Material.vue')
const librarySource = readSource('../components/materials/MaterialLibraryView.vue')

describe('material page Notion visual contract', () => {
  it('keeps the redesign scoped to the material page', () => {
    expect(materialSource).toContain('material-notion-page')
    expect(materialSource).toContain('material-notion-content')
    expect(materialSource).toContain('material-notion-section')
    expect(materialSource).toContain('material-analysis-card')
    expect(materialSource).toContain('variant="notion"')

    expect(librarySource).toContain("variant?: 'default' | 'notion'")
    expect(librarySource).toContain("variant: 'default'")
    expect(librarySource).toContain('material-library--notion')
  })

  it('uses the established Notion canvas, ink, surface and hairline tokens', () => {
    expect(materialSource).toContain('--mn-canvas: #ffffff;')
    expect(materialSource).toContain('--mn-surface: #f6f5f4;')
    expect(materialSource).toContain('--mn-hairline: #e5e3df;')
    expect(materialSource).toContain('--mn-ink: #37352f;')
    expect(materialSource).toContain('--mn-muted: #787671;')
    expect(materialSource).toContain('.material-analysis-card {')

    expect(librarySource).toContain('.material-library--notion {')
    expect(librarySource).toContain('.material-library--notion .material-library-table-head {')
    expect(librarySource).toContain('.material-library--notion .material-library-tag {')
  })
})
