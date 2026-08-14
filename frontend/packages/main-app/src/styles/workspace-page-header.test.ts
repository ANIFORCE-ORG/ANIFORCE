import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const readSource = (relativePath: string) =>
  readFileSync(fileURLToPath(new URL(relativePath, import.meta.url)), 'utf8')

const templateSource = (source: string) => {
  const match = source.match(/<template>([\s\S]*?)<\/template>/)
  expect(match, 'expected a Vue <template>').not.toBeNull()
  return match?.[1] ?? ''
}

const workspaceHeaderTag = (source: string) => {
  const template = templateSource(source)
  const matches = [
    ...template.matchAll(
      /<([a-z][\w-]*)\b[^>]*\sdata-workspace-page-header(?:="")?[^>]*>/gi,
    ),
  ]
  expect(
    matches,
    'expected exactly one first-level workspace page header marker',
  ).toHaveLength(1)
  return matches[0][0]
}

const staticClassTokens = (openingTag: string) => {
  const match = openingTag.match(/(?:^|\s)class="([^"]*)"/)
  return new Set((match?.[1] ?? '').split(/\s+/).filter(Boolean))
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
      const openingTag = workspaceHeaderTag(readSource(relativePath))
      const classes = staticClassTokens(openingTag)

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
