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

const rootClassTokens = (source: string) => {
  const root = source.match(/<template>(?:\s|<!--[\s\S]*?-->)*<[a-z][\w-]*\b([^>]*)>/)
  expect(root, 'expected first template element to have a static class').not.toBeNull()

  const classAttribute = root![1].match(/\bclass="([^"]*)"/)
  expect(classAttribute, 'expected first template element to have a static class').not.toBeNull()
  return classAttribute![1].split(/\s+/)
}

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

    expect(monitor).not.toContain(
      '<main class="flex flex-1 flex-col overflow-hidden bg-slate-50 dark:bg-slate-950">',
    )
    expect(createCampaign).not.toContain(
      '<div class="flex-1 flex flex-col bg-slate-50 dark:bg-slate-950 overflow-hidden">',
    )
    expect(projects).not.toContain('background: #f7f7f5;')
    expect(material).not.toContain(
      '<div class="flex h-screen w-full overflow-hidden bg-[#f6f7f9] dark:bg-slate-950">',
    )
  })

  it('preserves representative component-level soft surfaces', () => {
    const monitor = readSource('../pages/Monitor.vue')
    const material = readSource('../pages/creatives/Material.vue')

    expect(monitor).toContain('<thead class="bg-slate-50 text-slate-500 dark:bg-slate-800/50">')
    expect(material).toContain('border-dashed border-slate-300 bg-slate-50')
    expect(material).toContain('border-l border-slate-200 bg-[#f6f7f9] shadow-2xl')
  })

  it.each(workspacePages)('%s explicitly adopts the workspace canvas root', (_name, path) => {
    expect(rootClassTokens(readSource(path))).toContain('workspace-page-canvas')
  })
})
