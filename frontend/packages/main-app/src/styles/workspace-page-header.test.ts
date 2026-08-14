import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { parse as parseSfc } from 'vue/compiler-sfc'
import { describe, expect, it } from 'vitest'

const readSource = (relativePath: string) =>
  readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8')

const AST_ELEMENT = 1
const AST_ATTRIBUTE = 6
const AST_DIRECTIVE = 7

interface CompilerAstProp {
  type: number
  name?: string
  value?: { content: string } | null
  arg?: { content?: string } | null
  exp?: { content?: string } | null
}

interface CompilerAstNode {
  type: number
  tag?: string
  props?: CompilerAstProp[]
  children?: CompilerAstNode[]
}

interface CompilerAstElement extends CompilerAstNode {
  type: typeof AST_ELEMENT
  tag: string
  props: CompilerAstProp[]
  children: CompilerAstNode[]
}

const staticAttribute = (element: CompilerAstElement, name: string) =>
  element.props.find(
    (prop) => prop.type === AST_ATTRIBUTE && prop.name === name,
  )

const workspaceHeaderElement = (source: string) => {
  const { descriptor, errors } = parseSfc(source, {
    filename: 'workspace-page-header.vue',
  })
  expect(errors, 'expected valid Vue SFC source').toHaveLength(0)
  expect(descriptor.template, 'expected a Vue <template>').not.toBeNull()
  expect(
    descriptor.template?.ast,
    'expected a parsed Vue template AST',
  ).toBeDefined()

  const matches: CompilerAstElement[] = []
  const visit = (node: CompilerAstNode) => {
    if (node.type === AST_ELEMENT) {
      const element = node as CompilerAstElement
      if (staticAttribute(element, 'data-workspace-page-header')) {
        matches.push(element)
      }
    }
    node.children?.forEach(visit)
  }
  visit(descriptor.template?.ast as unknown as CompilerAstNode)

  expect(
    matches,
    'expected exactly one first-level workspace page header marker',
  ).toHaveLength(1)
  expect(
    matches[0].tag.toLowerCase(),
    'expected workspace page header marker on a semantic <header> opening tag',
  ).toBe('header')
  return matches[0]
}

const staticClassTokens = (element: CompilerAstElement) =>
  new Set(
    (staticAttribute(element, 'class')?.value?.content ?? '')
      .split(/\s+/)
      .filter(Boolean),
  )

const descendantElements = (
  element: CompilerAstElement,
  predicate: (candidate: CompilerAstElement) => boolean,
) => {
  const matches: CompilerAstElement[] = []
  const visit = (node: CompilerAstNode) => {
    if (node.type === AST_ELEMENT) {
      const candidate = node as CompilerAstElement
      if (candidate !== element && predicate(candidate)) matches.push(candidate)
    }
    node.children?.forEach(visit)
  }
  visit(element)
  return matches
}

const directive = (
  element: CompilerAstElement,
  name: string,
  argument?: string,
) =>
  element.props.find(
    (prop) =>
      prop.type === AST_DIRECTIVE &&
      prop.name === name &&
      (argument === undefined || prop.arg?.content === argument),
  )

const cssRuleBodies = (source: string, selectorFragment: string) =>
  [...source.matchAll(/([^{}]+)\{([^{}]*)\}/gs)]
    .filter(([, selector]) => selector.includes(selectorFragment))
    .map(([, , body]) => body)

const cssDeclarations = (body: string) =>
  body
    .split(';')
    .map(declaration => declaration.trim())
    .filter(Boolean)
    .map((declaration) => {
      const separator = declaration.indexOf(':')
      return {
        property: declaration.slice(0, separator).trim(),
        value: declaration.slice(separator + 1).trim(),
      }
    })

const mediaRuleBody = (source: string, maxWidth: number) => {
  const marker = `@media (max-width: ${maxWidth}px) {`
  const markerStart = source.indexOf(marker)
  expect(markerStart, `expected ${marker}`).toBeGreaterThanOrEqual(0)

  const openingBrace = source.indexOf('{', markerStart)
  let depth = 0
  for (let index = openingBrace; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1
    if (source[index] === '}') depth -= 1
    if (depth === 0) return source.slice(openingBrace + 1, index)
  }

  throw new Error(`expected ${marker} to have a closing brace`)
}

const sharedHeaderPages = [
  '../pages/projects/ProjectDetail.vue',
  '../pages/campaigns/Campaign.vue',
  '../pages/campaigns/CampaignDetail.vue',
  '../pages/campaigns/CreateCampaign.vue',
  '../pages/campaigns/CreateAdUnit.vue',
  '../pages/creatives/Material.vue',
  '../pages/Monitor.vue',
  '../pages/settings/Settings.vue',
  '../pages/settings/AccountConfig.vue',
  '../pages/settings/AIUsageConfig.vue',
  '../pages/settings/PlatformConnections.vue',
  '../pages/system/SystemAdmin.vue',
] as const

const expectRuleNotToDeclareMinHeight = (
  source: string,
  selector: string,
) => {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  expect(source).not.toMatch(
    new RegExp(`${escapedSelector}\\s*\\{[^}]*\\bmin-height\\s*:`, 's'),
  )
}

describe('workspaceHeaderElement', () => {
  it('does not count markers inside Vue template comments', () => {
    const source = `
      <template>
        <!-- <header data-workspace-page-header class="workspace-page-header"></header> -->
      </template>
    `

    expect(() => workspaceHeaderElement(source)).toThrow()
  })

  it('does not count a header-like string inside a Vue interpolation', () => {
    const source = [
      '<template>',
      '  <div>{{ `<header data-workspace-page-header class="workspace-page-header"></header>` }}</div>',
      '</template>',
    ].join('\n')

    expect(() => workspaceHeaderElement(source)).toThrow()
  })

  it.each([
    [
      'script',
      `const fakeHeader = '<template><header data-workspace-page-header class="workspace-page-header"></header></template>'`,
    ],
    [
      'style',
      `.fake::before { content: '<template><header data-workspace-page-header class="workspace-page-header"></header></template>'; }`,
    ],
  ])('does not count header-like strings inside <%s>', (block, content) => {
    const source = `
      <${block}>${content}</${block}>
      <template><div>真实页面内容</div></template>
    `

    expect(() => workspaceHeaderElement(source)).toThrow()
  })

  it.each(['main', 'section', 'div', 'nav'])(
    'rejects a marker placed on a <%s> element',
    (tagName) => {
      const source = `
        <template>
          <${tagName} data-workspace-page-header class="workspace-page-header"></${tagName}>
        </template>
      `

      expect(() => workspaceHeaderElement(source)).toThrow()
    },
  )
})

describe('workspace page header contract', () => {
  it('defines a shared fixed 57px page header height', () => {
    const globalStyles = readSource('./global.css')
    expect(globalStyles).toContain('--workspace-page-header-height: 57px;')

    const rule = globalStyles.match(/\.workspace-page-header\s*\{([^}]*)\}/s)
    expect(rule, 'expected a .workspace-page-header rule').not.toBeNull()
    expect(rule?.[1]).toMatch(
      /\bheight:\s*var\(--workspace-page-header-height\)\s*;/,
    )
    expect(rule?.[1]).toMatch(
      /\bmin-height:\s*var\(--workspace-page-header-height\)\s*;/,
    )
    expect(rule?.[1]).toMatch(
      /\bflex:\s*0\s+0\s+var\(--workspace-page-header-height\)\s*;/,
    )
  })

  it.each(sharedHeaderPages)(
    '%s opts exactly one first-level header into the shared contract',
    (relativePath) => {
      const header = workspaceHeaderElement(readSource(relativePath))
      const classes = staticClassTokens(header)

      expect(classes).toContain('workspace-page-header')
      expect(
        [...classes].filter((token) => /^(?:min-)?h-\[\d+px\]$/.test(token)),
      ).toEqual([])
    },
  )

  it('removes local min-height overrides from contract headers', () => {
    expectRuleNotToDeclareMinHeight(
      readSource('../pages/projects/ProjectDetail.vue'),
      '.detail-page-bar',
    )
    expectRuleNotToDeclareMinHeight(
      readSource('../pages/settings/Settings.vue'),
      '.settings-page-head',
    )
    expectRuleNotToDeclareMinHeight(
      readSource('./settings-notion.css'),
      '.sn-page-head',
    )
  })

  it('keeps Home outside the opt-in contract', () => {
    const home = readSource('../pages/Home.vue')
    expect(home).not.toContain('data-workspace-page-header')
    expect(home).not.toContain('workspace-page-header')
  })
})

describe('Projects workspace page header contract', () => {
  const projects = readSource('../pages/projects/Projects.vue')

  it('uses one semantic shared header with one embedded search and status toolbar', () => {
    const header = workspaceHeaderElement(projects)
    const headerClasses = staticClassTokens(header)
    expect(headerClasses).toContain('projects-page-bar')
    expect(headerClasses).toContain('workspace-page-header')

    const directChildClasses = header.children
      .filter((child): child is CompilerAstElement => child.type === AST_ELEMENT)
      .map(child => staticClassTokens(child))
    expect(directChildClasses).toHaveLength(3)
    expect(directChildClasses[0]).toContain('projects-page-title-wrap')
    expect(directChildClasses[1]).toContain('projects-toolbar')
    expect(directChildClasses[2]).toContain('projects-page-actions')

    const toolbar = descendantElements(
      header,
      element => staticClassTokens(element).has('projects-toolbar'),
    )
    expect(toolbar, 'expected exactly one Projects toolbar inside the header').toHaveLength(1)

    const searchInputs = descendantElements(
      toolbar[0],
      element => element.tag.toLowerCase() === 'input',
    )
    const statusFilters = descendantElements(
      toolbar[0],
      element => staticClassTokens(element).has('projects-status-filter'),
    )
    expect(searchInputs).toHaveLength(1)
    expect(statusFilters).toHaveLength(1)

    expect(staticAttribute(searchInputs[0], 'aria-label')?.value?.content).toBe(
      '搜索项目名称或标签',
    )
    expect(directive(searchInputs[0], 'model')?.exp?.content).toBe('searchQuery')
    expect(directive(searchInputs[0], 'on', 'input')?.exp?.content).toBe('handleSearch')

    expect(staticAttribute(statusFilters[0], 'aria-label')?.value?.content).toBe(
      '按项目状态筛选',
    )
    expect(directive(statusFilters[0], 'model')?.exp?.content).toBe('filterStatus')
    expect(directive(statusFilters[0], 'on', 'change')?.exp?.content).toBe('handleSearch')

    const createButtons = descendantElements(
      header,
      element => staticClassTokens(element).has('projects-create-button'),
    )
    expect(createButtons).toHaveLength(1)
    expect(staticAttribute(createButtons[0], 'aria-label')?.value?.content).toBe(
      '创建项目',
    )
  })

  it('keeps Projects filtering, search handling, and create handling intact', () => {
    expect(projects).toContain("filterStatus.value !== 'all'")
    expect(projects).toContain('p.name.toLowerCase().includes(query)')
    expect(projects).toContain(
      'p.tags.some(tag => tag.toLowerCase().includes(query))',
    )
    expect(projects).toContain(
      `const handleSearch = () => {\n  // 筛选逻辑在 computed 中处理\n}`,
    )
    expect(projects).toContain(
      `const handleCreateProject = () => {\n  editingProject.value = null\n  showCreateModal.value = true\n}`,
    )
    expect(projects).toContain('@click="handleCreateProject"')
  })

  it('uses the fixed-height header grid and transparent zero-box toolbar contract', () => {
    const pageBarRules = cssRuleBodies(projects, '.projects-page-bar')
    expect(pageBarRules.length).toBeGreaterThan(0)
    pageBarRules.forEach((body) => {
      expect(body).not.toMatch(/\b(?:min-)?height\s*:/)
    })

    expect(projects).toMatch(
      /\.projects-page-bar\s*\{[^}]*\bdisplay:\s*grid;[^}]*\bgrid-template-columns:\s*auto minmax\(180px,\s*1fr\) auto;[^}]*\balign-items:\s*center;[^}]*\bgap:\s*14px;/s,
    )

    const toolbarRules = cssRuleBodies(projects, '.projects-toolbar')
    expect(toolbarRules.length).toBeGreaterThan(0)
    toolbarRules.forEach((body) => {
      const declarations = cssDeclarations(body)
      expect(
        declarations.filter(({ property }) => property === 'padding'),
      ).toEqual(
        declarations
          .filter(({ property }) => property === 'padding')
          .map(({ property }) => ({ property, value: '0' })),
      )
      expect(
        declarations.filter(({ property }) => /^border(?:-[\w-]+)?$/.test(property)),
      ).toEqual(
        declarations
          .filter(({ property }) => /^border(?:-[\w-]+)?$/.test(property))
          .map(({ property }) => ({ property, value: '0' })),
      )
      expect(
        declarations.filter(({ property }) => /^background(?:-color)?$/.test(property)),
      ).toEqual(
        declarations
          .filter(({ property }) => /^background(?:-color)?$/.test(property))
          .map(({ property }) => ({ property, value: 'transparent' })),
      )
    })
    expect(projects).toMatch(
      /\.projects-toolbar\s*\{[^}]*\bmin-width:\s*0;[^}]*\bdisplay:\s*grid;[^}]*\bgrid-template-columns:\s*minmax\(140px,\s*1fr\) 112px;[^}]*\bgap:\s*7px;[^}]*\bpadding:\s*0;[^}]*\bborder:\s*0;[^}]*\bbackground:\s*transparent;/s,
    )
    expect(projects).toMatch(
      /\.projects-search-field input,\s*\.projects-status-filter\s*\{[^}]*\bheight:\s*34px;/s,
    )
  })

  it('keeps Projects controls on one responsive header row', () => {
    expect(projects).toMatch(
      /@media \(max-width: 1180px\)[\s\S]*?\.projects-page-subtitle\s*\{\s*display:\s*none;\s*\}/,
    )
    expect(projects).toMatch(
      /@media \(max-width: 900px\)[\s\S]*?\.projects-view-switch,\s*\.projects-create-label\s*\{\s*display:\s*none;\s*\}/,
    )
    expect(projects).toMatch(
      /@media \(max-width: 900px\)[\s\S]*?\.projects-create-button\s*\{[^}]*\bwidth:\s*34px;[^}]*\bheight:\s*34px;/,
    )
    expect(projects).toMatch(
      /@media \(max-width: 620px\)[\s\S]*?\.projects-page-title-content\s*\{\s*display:\s*none;\s*\}/,
    )
    expect(projects).toMatch(
      /@media \(max-width: 620px\)[\s\S]*?\.projects-page-bar\s*\{[^}]*\bpadding:\s*0 14px;/,
    )
    expect(projects).toMatch(
      /@media \(max-width: 620px\)[\s\S]*?\.projects-toolbar\s*\{[^}]*\bgrid-template-columns:\s*minmax\(120px,\s*1fr\) 104px;/,
    )
    expect(projects).toMatch(
      /@media \(max-width: 520px\)[\s\S]*?\.projects-toolbar\s*\{[^}]*\bgrid-template-columns:\s*1fr;/,
    )
    expect(projects).toMatch(
      /@media \(max-width: 520px\)[\s\S]*?\.projects-status-filter\s*\{\s*display:\s*none;\s*\}/,
    )
  })

  it('compresses the 520px header to toolbar and actions columns', () => {
    const mobileStyles = mediaRuleBody(projects, 520)
    expect(mobileStyles).toMatch(
      /\.projects-page-title-wrap\s*\{\s*display:\s*none;\s*\}/,
    )
    expect(mobileStyles).toMatch(
      /\.projects-page-bar\s*\{[^}]*\bgrid-template-columns:\s*minmax\(0,\s*1fr\) auto;[^}]*\bgap:\s*7px;[^}]*\bpadding:\s*0 8px;/s,
    )
    expect(mobileStyles).not.toMatch(
      /\.projects-page-bar\s*\{[^}]*\b(?:min-)?height\s*:/s,
    )
  })

  it('offers an accessible mobile-only way to clear an active status filter', () => {
    const header = workspaceHeaderElement(projects)
    const searchFields = descendantElements(
      header,
      element => staticClassTokens(element).has('projects-search-field'),
    )
    expect(searchFields).toHaveLength(1)

    const clearButtons = descendantElements(
      searchFields[0],
      element => staticClassTokens(element).has('projects-clear-status-filter'),
    )
    expect(clearButtons).toHaveLength(1)
    expect(staticAttribute(clearButtons[0], 'type')?.value?.content).toBe('button')
    expect(staticAttribute(clearButtons[0], 'aria-label')?.value?.content).toBe(
      '清除状态筛选',
    )
    expect(directive(clearButtons[0], 'if')?.exp?.content).toBe(
      "filterStatus !== 'all'",
    )
    expect(directive(clearButtons[0], 'on', 'click')?.exp?.content).toBe(
      "filterStatus = 'all'; handleSearch()",
    )

    expect(projects).toMatch(
      /\.projects-clear-status-filter\s*\{[^}]*\bdisplay:\s*none;/s,
    )
    const mobileStyles = mediaRuleBody(projects, 520)
    expect(mobileStyles).toMatch(
      /\.projects-search-field input\s*\{[^}]*\bpadding-right:\s*38px;/s,
    )
    expect(mobileStyles).toMatch(
      /\.projects-clear-status-filter\s*\{[^}]*\bdisplay:\s*inline-grid;/s,
    )
  })

  it('uses stable high-contrast focus rings in light and dark themes', () => {
    const lightFocus = projects.match(
      /\.projects-search-field input:focus,\s*\.projects-status-filter:focus\s*\{([^}]*)\}/s,
    )
    expect(lightFocus, 'expected the light Projects focus rule').not.toBeNull()
    expect(cssDeclarations(lightFocus?.[1] ?? '')).toEqual(
      expect.arrayContaining([
        { property: 'border', value: '1px solid #37352f' },
        { property: 'box-shadow', value: '0 0 0 2px rgba(55, 53, 47, 0.28)' },
      ]),
    )

    const darkFocus = projects.match(
      /\.dark \.projects-search-field input:focus,\s*\.dark \.projects-status-filter:focus\s*\{([^}]*)\}/s,
    )
    expect(darkFocus, 'expected a higher-specificity dark Projects focus rule').not.toBeNull()
    expect(cssDeclarations(darkFocus?.[1] ?? '')).toEqual(
      expect.arrayContaining([
        { property: 'border', value: '1px solid #f3f3f2' },
        { property: 'box-shadow', value: '0 0 0 2px rgba(243, 243, 242, 0.45)' },
      ]),
    )
    expect(darkFocus?.index).toBeGreaterThan(lightFocus?.index ?? Number.MAX_SAFE_INTEGER)
  })
})

describe('Dashboard workspace page contract', () => {
  const dashboard = readSource('../pages/Dashboard.vue')

  it('uses the shared header marker with Dashboard header classes and embedded opt-out', () => {
    const header = workspaceHeaderElement(dashboard)
    const classes = staticClassTokens(header)

    expect(classes).toContain('page-bar')
    expect(classes).toContain('replay-bar')
    expect(dashboard).toContain(
      `<header class="page-bar replay-bar" data-workspace-page-header :class="{ 'workspace-page-header': !props.embedded }">`,
    )
  })

  it('keeps accessible Dashboard filters while removing their visible captions', () => {
    expect(dashboard).not.toMatch(
      /<label class="filter-field">\s*(?:时间范围|平台|项目)\s*<select/,
    )
    expect(dashboard).toContain(
      '<select v-model="period" class="period-select" aria-label="时间范围" @change="changePeriod">',
    )
    expect(dashboard).toContain(
      '<select v-model="platform" class="period-select" aria-label="平台" @change="changePlatform">',
    )
    expect(dashboard).toContain(
      '<select v-model="project" class="period-select" aria-label="项目" @change="changeProject">',
    )
  })

  it('removes the Dashboard data note and its dead update state', () => {
    expect(dashboard).not.toContain('class="data-note"')
    expect(dashboard).not.toContain('ANIFORCE Demo 数据集')
    expect(dashboard).not.toContain('updatedText')
    expect(dashboard).not.toContain('.data-note {')
    expect(dashboard).toContain('.quiet-badge {')
  })

  it('uses the compact Dashboard chart geometry and marker weights', () => {
    expect(dashboard).toContain('preserveAspectRatio="xMidYMid meet"')
    expect(dashboard).toContain('stroke="#4f8fe8" stroke-width="1.4"')
    expect(dashboard).toContain('stroke="#dd7d00" stroke-width="1.35"')
    expect(dashboard).toMatch(
      /<g fill="#4f8fe8" stroke="#fff" stroke-width="1">[\s\S]*?<circle cx="91" cy="106" r="2\.1"/,
    )
    expect(dashboard).toMatch(
      /<g fill="#dd7d00" stroke="#fff" stroke-width="1">[\s\S]*?<circle cx="91" cy="138" r="2\.1"/,
    )
    expect(dashboard).toContain(
      '<rect :x="activeTrendPoint.x - 10" :y="activeTrendPoint.barY" width="20" :height="activeTrendPoint.barHeight" rx="3" />',
    )
    expect(dashboard).toContain(
      '<circle class="spend" :cx="activeTrendPoint.x" :cy="activeTrendPoint.spendY" r="3.5" />',
    )
    expect(dashboard).toContain(
      '<circle class="roas" :cx="activeTrendPoint.x" :cy="activeTrendPoint.roasY" r="3.5" />',
    )
    expect(dashboard).toMatch(/\.legend-dot\s*\{[^}]*\bwidth:\s*5px;[^}]*\bheight:\s*5px;/s)
    expect(dashboard).toMatch(/\.chart-active-markers line\s*\{[^}]*\bstroke-width:\s*\.75;/s)
    expect(dashboard).toMatch(/\.chart-active-markers rect\s*\{[^}]*\bstroke-width:\s*1\.2;/s)
    expect(dashboard).toMatch(/\.chart-active-markers circle\s*\{[^}]*\bstroke-width:\s*1\.5;/s)
  })

  it('stretches platform cards evenly without one-off insight content', () => {
    expect(dashboard).not.toContain('insight:')
    expect(dashboard).not.toContain('insightValue')
    expect(dashboard).not.toContain('.platform-insight')
    expect(dashboard).toMatch(/\.platform-grid\s*\{[^}]*\balign-items:\s*stretch;/s)
    expect(dashboard).toMatch(/\.platform-card\s*\{[^}]*\balign-self:\s*stretch;/s)
  })

  it('keeps the standalone Dashboard header fixed-height and responsive', () => {
    expectRuleNotToDeclareMinHeight(dashboard, '.replay-bar')
    expect(dashboard).toContain('<span class="refresh-label">刷新</span>')
    expect(dashboard).toMatch(
      /<button class="refresh-button"[^>]*\baria-label="刷新数据"[^>]*>/,
    )
    expect(dashboard).toMatch(/\.filter-field\s*\{[^}]*\bdisplay:\s*flex;/s)
    expect(dashboard).not.toMatch(/\.refresh-button\s*\{[^}]*\balign-self:\s*end;/s)
    expect(dashboard).toMatch(
      /@media \(max-width: 900px\)[\s\S]*?\.replay-title p\s*\{\s*display:\s*none;\s*\}/,
    )
    expect(dashboard).toMatch(
      /@media \(max-width: 620px\)[\s\S]*?\.replay-title h1\s*\{\s*display:\s*none;\s*\}/,
    )
    expect(dashboard).toMatch(
      /@media \(max-width: 620px\)[\s\S]*?\.refresh-label\s*\{\s*display:\s*none;\s*\}/,
    )
  })
})
