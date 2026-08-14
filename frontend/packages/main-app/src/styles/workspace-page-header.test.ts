import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { parse as parseSfc } from 'vue/compiler-sfc'
import { describe, expect, it } from 'vitest'

const readSource = (relativePath: string) =>
  readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8')

const AST_ELEMENT = 1
const AST_ATTRIBUTE = 6

interface CompilerAstProp {
  type: number
  name?: string
  value?: { content: string } | null
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
