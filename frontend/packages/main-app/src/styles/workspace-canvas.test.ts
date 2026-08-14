import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const readSource = (path: string) =>
  readFileSync(new URL(path, import.meta.url), 'utf8')

const routerSource = readSource('../router/index.ts')
const globalSource = readSource('./global.css')

const workspacePages = [
  ['Home', '../pages/Home.vue'],
  ['Dashboard', '../pages/Dashboard.vue'],
  ['Monitor', '../pages/Monitor.vue'],
  ['Projects', '../pages/projects/Projects.vue'],
  ['ProjectDetail', '../pages/projects/ProjectDetail.vue'],
  ['Campaign', '../pages/campaigns/Campaign.vue'],
  ['CampaignDetail', '../pages/campaigns/CampaignDetail.vue'],
  ['CreateCampaign', '../pages/campaigns/CreateCampaign.vue'],
  ['CreateAdUnit', '../pages/campaigns/CreateAdUnit.vue'],
  ['Material', '../pages/creatives/Material.vue'],
  ['Settings', '../pages/settings/Settings.vue'],
  ['AccountConfig', '../pages/settings/AccountConfig.vue'],
  ['AIUsageConfig', '../pages/settings/AIUsageConfig.vue'],
  ['PlatformConnections', '../pages/settings/PlatformConnections.vue'],
  ['SystemAdmin', '../pages/system/SystemAdmin.vue'],
] as const

describe('workspace page canvas contract', () => {
  it('keeps exactly fifteen routes in the workspace shell', () => {
    expect(routerSource.match(/meta: \{ workspaceShell: true \}/g)).toHaveLength(15)
  })

  it('defines the Home-aligned light canvas token and reusable root class', () => {
    expect(globalSource).toContain('--workspace-canvas: #ffffff;')
    expect(globalSource).toContain('.workspace-page-canvas {')
    expect(globalSource).toContain('background-color: var(--workspace-canvas);')
  })

  it.each(workspacePages)('%s explicitly adopts the workspace canvas root', (_name, path) => {
    expect(readSource(path)).toContain('workspace-page-canvas')
  })
})
