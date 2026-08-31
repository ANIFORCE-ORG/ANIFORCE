import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./MaterialLibraryView.vue', import.meta.url), 'utf8')
const materialPage = readFileSync(new URL('../../pages/creatives/Material.vue', import.meta.url), 'utf8')

describe('MaterialLibraryView progressive UX absorption', () => {
  it('supports externally controlled filters without removing local defaults', () => {
    for (const prop of ['searchQuery?', 'accountFilter?', 'sourceFilter?', 'ratioFilter?', 'sortKey?']) {
      expect(source).toContain(prop)
    }
    for (const event of [
      "'update:searchQuery'",
      "'update:accountFilter'",
      "'update:sourceFilter'",
      "'update:ratioFilter'",
      "'update:sortKey'",
    ]) {
      expect(source).toContain(event)
    }
    expect(source).toContain("props.searchQuery ?? localSearchQuery.value")
  })

  it('paginates filtered real material rows and resets safely when filters change', () => {
    expect(source).toContain('const PAGE_SIZE = 10')
    expect(source).toContain('const paginatedRows = computed')
    expect(source).toContain('filteredRows.value.slice(start, start + PAGE_SIZE)')
    expect(source).toContain('v-for="row in paginatedRows"')
    expect(source).toContain('watch([searchQuery, accountFilter, sourceFilter, ratioFilter, sortKey]')
    expect(source).toContain('currentPage.value = 1')
  })

  it('preserves the compact embedded workspace table and icon actions', () => {
    expect(source).toContain(":class=\"embedded ? 'table-fixed' : 'min-w-[980px]'\"")
    expect(source).toContain('class="material-action"')
    expect(source).toContain('alternate_email')
  })

  it('scopes the Notion visual variant to the main materials page', () => {
    expect(source).toContain("variant?: 'default' | 'notion'")
    expect(source).toContain("'material-library--notion': variant === 'notion'")
    expect(materialPage).toContain('variant="notion"')
  })
})
