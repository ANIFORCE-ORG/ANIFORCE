import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./NewUserGuide.vue', import.meta.url), 'utf8')
const appSource = readFileSync(new URL('../../App.vue', import.meta.url), 'utf8')
const sidebarSource = readFileSync(new URL('../layout/SidebarNav.vue', import.meta.url), 'utf8')

describe('NewUserGuide', () => {
  it('mounts once for authenticated workspace routes and can be reopened from the sidebar', () => {
    expect(appSource).toContain('<NewUserGuide v-if="isWorkspaceShell" />')
    expect(sidebarSource).toContain("new CustomEvent('aniforce:open-new-user-guide')")
    expect(sidebarSource).toContain('aria-label="打开新手引导"')
  })

  it('derives completion from real platform and organization APIs', () => {
    expect(source).toContain('platformApi.getAllConnections()')
    expect(source).toContain('organizationApi.getMyOrganizations()')
    expect(source).toContain("item.status === 'active'")
    expect(source).toContain('organizationApi.join({ org_code: normalizedCode, invite_code: normalizedInvite })')
  })

  it('starts supported OAuth providers and keeps TikTok unavailable', () => {
    expect(source).toContain('platformApi.startMetaOAuth()')
    expect(source).toContain('platformApi.startGoogleOAuth()')
    expect(source).toContain('平台授权链路尚未接入')
    expect(source).toContain('即将支持')
  })

  it('does not contain simulated success or fixed organization credentials', () => {
    expect(source).not.toContain('授权已模拟完成')
    expect(source).not.toContain('Aniforce Growth Team')
    expect(source).not.toContain('AF-2026-88K')
    expect(source).not.toContain('素材评分、疲劳度')
  })
})
