import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const readSource = (path: string) =>
  readFileSync(new URL(path, import.meta.url), 'utf8')

const routerSource = readSource('../router/index.ts')
const globalSource = readSource('./global.css')

const workspacePages = [
  ['Home', '../pages/Home.vue', '@/pages/Home.vue'],
  ['Campaign', '../pages/campaigns/Campaign.vue', '@/pages/campaigns/Campaign.vue'],
  ['Material', '../pages/creatives/Material.vue', '@/pages/creatives/Material.vue'],
  ['Monitor', '../pages/Monitor.vue', '@/pages/Monitor.vue'],
  ['Dashboard', '../pages/Dashboard.vue', '@/pages/Dashboard.vue'],
  ['Projects', '../pages/projects/Projects.vue', '@/pages/projects/Projects.vue'],
  ['ProjectDetail', '../pages/projects/ProjectDetail.vue', '@/pages/projects/ProjectDetail.vue'],
  ['CampaignDetail', '../pages/campaigns/CampaignDetail.vue', '@/pages/campaigns/CampaignDetail.vue'],
  ['CreateCampaign', '../pages/campaigns/CreateCampaign.vue', '@/pages/campaigns/CreateCampaign.vue'],
  ['CreateAdUnit', '../pages/campaigns/CreateAdUnit.vue', '@/pages/campaigns/CreateAdUnit.vue'],
  ['Settings', '../pages/settings/Settings.vue', '@/pages/settings/Settings.vue'],
  ['AccountConfig', '../pages/settings/AccountConfig.vue', '@/pages/settings/AccountConfig.vue'],
  ['AIUsageConfig', '../pages/settings/AIUsageConfig.vue', '@/pages/settings/AIUsageConfig.vue'],
  ['PlatformConnections', '../pages/settings/PlatformConnections.vue', '@/pages/settings/PlatformConnections.vue'],
  ['SystemAdmin', '../pages/system/SystemAdmin.vue', '@/pages/system/SystemAdmin.vue'],
] as const

const workspaceRouteComponents = [...routerSource.matchAll(
  /component:\s*\(\)\s*=>\s*import\('(@\/pages\/[^']+\.vue)'\),\s*meta:\s*\{ workspaceShell: true \}/g,
)].map(match => match[1])

const staticClassTokens = (attributes: string) => {
  const classAttribute = attributes.match(/(?:^|\s)class="([^"]*)"/)
  return classAttribute
    ? classAttribute[1].split(/\s+/).filter(Boolean)
    : null
}

const rootClassTokens = (source: string) => {
  const root = source.match(/<template>(?:\s|<!--[\s\S]*?-->)*<[a-z][\w-]*\b([^>]*)>/)
  expect(root, 'expected first template element to have a static class').not.toBeNull()

  const tokens = staticClassTokens(root![1])
  expect(tokens, 'expected first template element to have a static class').not.toBeNull()
  return tokens!
}

const elementClassTokens = (
  source: string,
  tagName: string,
  requiredTokens: string[],
) => {
  const matches = [...source.matchAll(new RegExp(`<${tagName}\\b([^>]*)>`, 'g'))]
    .map(match => staticClassTokens(match[1]))
    .filter((tokens): tokens is string[] =>
      tokens !== null && requiredTokens.every(token => tokens.includes(token)),
    )

  expect(
    matches,
    `expected exactly one <${tagName}> with class tokens: ${requiredTokens.join(', ')}`,
  ).toHaveLength(1)
  return matches[0]
}

const topLevelSfcStyleRules = (source: string) => {
  const styleBlocks = [...source.matchAll(/<style\b[^>]*>([\s\S]*?)<\/style>/g)]
    .map(match => match[1])
  expect(styleBlocks, 'expected at least one SFC style block').not.toHaveLength(0)

  const styles = styleBlocks.join('\n').replace(/\/\*[\s\S]*?\*\//g, '')
  const rules: Array<{ selector: string, body: string }> = []
  let selectorStart = 0
  let bodyStart = -1
  let selector = ''
  let depth = 0
  let quote: '"' | "'" | null = null
  let escaped = false

  for (let index = 0; index < styles.length; index += 1) {
    const character = styles[index]

    if (quote) {
      if (escaped) {
        escaped = false
      }
      else if (character === '\\') {
        escaped = true
      }
      else if (character === quote) {
        quote = null
      }
      continue
    }

    if (character === '"' || character === "'") {
      quote = character
    }
    else if (character === '{') {
      if (depth === 0) {
        selector = styles.slice(selectorStart, index).trim()
        bodyStart = index + 1
      }
      depth += 1
    }
    else if (character === '}') {
      if (depth === 0)
        throw new Error('unexpected closing brace in SFC styles')

      depth -= 1
      if (depth === 0) {
        rules.push({ selector, body: styles.slice(bodyStart, index) })
        selectorStart = index + 1
        bodyStart = -1
      }
    }
    else if (character === ';' && depth === 0) {
      selectorStart = index + 1
    }
  }

  if (depth !== 0)
    throw new Error('unclosed rule in SFC styles')

  return rules
}

const backgroundDeclarations = (ruleBody: string) =>
  [...ruleBody.matchAll(/(?:^|;)\s*(background(?:-color)?)\s*:\s*([^;]*?)(?=;|$)/gi)]
    .map(match => ({
      property: match[1].toLowerCase(),
      value: match[2].trim(),
    }))

describe('workspace page canvas contract', () => {
  it('keeps exactly fifteen routes in the workspace shell', () => {
    expect(workspacePages).toHaveLength(15)
    expect(routerSource.match(/meta: \{ workspaceShell: true \}/g)).toHaveLength(15)
    expect(workspaceRouteComponents).toEqual(workspacePages.map(([, , routePath]) => routePath))
  })

  it('defines the Home-aligned light canvas token and reusable root class', () => {
    expect(globalSource).toContain('--workspace-canvas: #ffffff;')
    expect(globalSource).toContain('.workspace-page-canvas {')
    expect(globalSource).toContain('background-color: var(--workspace-canvas);')
  })

  it('removes legacy gray only from full-height page canvases', () => {
    const monitor = readSource('../pages/Monitor.vue')
    const projects = readSource('../pages/projects/Projects.vue')
    const createCampaign = readSource('../pages/campaigns/CreateCampaign.vue')
    const material = readSource('../pages/creatives/Material.vue')

    const monitorCanvas = elementClassTokens(
      monitor,
      'main',
      ['flex-1', 'flex-col', 'overflow-hidden'],
    )
    expect(monitorCanvas).toContain('workspace-page-canvas')
    expect(monitorCanvas).not.toContain('bg-slate-50')
    expect(monitorCanvas).toContain('dark:bg-slate-950')

    const createCampaignCanvas = elementClassTokens(
      createCampaign,
      'div',
      ['flex-1', 'flex-col', 'overflow-hidden'],
    )
    expect(createCampaignCanvas).toContain('workspace-page-canvas')
    expect(createCampaignCanvas).not.toContain('bg-slate-50')
    expect(createCampaignCanvas).toContain('dark:bg-slate-950')

    const projectShellRules = topLevelSfcStyleRules(projects)
      .filter(rule => rule.selector === '.projects-shell')
    expect(projectShellRules, 'expected exactly one base .projects-shell rule').toHaveLength(1)
    expect(backgroundDeclarations(projectShellRules[0].body)).toEqual([
      { property: 'background', value: 'var(--workspace-canvas)' },
    ])

    const materialCanvas = rootClassTokens(material)
    expect(materialCanvas).toContain('workspace-page-canvas')
    expect(materialCanvas).not.toContain('bg-[#f6f7f9]')
  })

  it('preserves representative component-level soft surfaces', () => {
    const monitor = readSource('../pages/Monitor.vue')
    const material = readSource('../pages/creatives/Material.vue')

    const monitorTableHead = elementClassTokens(monitor, 'thead', [])
    expect(monitorTableHead).toContain('bg-slate-50')
    expect(monitorTableHead).toContain('text-slate-500')
    expect(monitorTableHead).toContain('dark:bg-slate-800/50')

    const materialDropZone = elementClassTokens(
      material,
      'div',
      ['min-h-[220px]', 'border-dashed', 'border-slate-300'],
    )
    expect(materialDropZone).toContain('bg-slate-50')

    const materialDrawer = elementClassTokens(
      material,
      'aside',
      ['border-l', 'border-slate-200', 'shadow-2xl'],
    )
    expect(materialDrawer).toContain('bg-[#f6f7f9]')
  })

  it.each(workspacePages)('%s explicitly adopts the workspace canvas root', (_name, path) => {
    expect(rootClassTokens(readSource(path))).toContain('workspace-page-canvas')
  })
})
