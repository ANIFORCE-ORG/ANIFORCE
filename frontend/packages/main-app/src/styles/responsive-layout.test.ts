import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (relativePath: string) => readFileSync(new URL(relativePath, import.meta.url), 'utf8')

const globalCss = read('./global.css')
const sidebar = read('../components/layout/SidebarNav.vue')
const campaign = read('../pages/campaigns/Campaign.vue')
const campaignDetail = read('../pages/campaigns/CampaignDetail.vue')
const createAdUnit = read('../pages/campaigns/CreateAdUnit.vue')
const settingsCss = read('./settings-notion.css')
const organizationDialog = read('../components/settings/OrganizationDetail.vue')

describe('application-wide responsive layout', () => {
  it('provides viewport, overflow and media safety defaults', () => {
    expect(globalCss).toContain('min-width: 320px;')
    expect(globalCss).toContain('min-height: 100dvh;')
    expect(globalCss).toContain('overflow-wrap: anywhere;')
    expect(globalCss).toContain('max-inline-size: 100%;')
    expect(globalCss).toContain('padding-left: env(safe-area-inset-left);')
    expect(globalCss).toContain('@media (max-width: 767px)')
  })

  it('keeps mobile controls readable and touch friendly', () => {
    expect(globalCss).toContain('min-width: 44px;')
    expect(globalCss).toContain('min-height: 44px;')
    expect(globalCss).toMatch(/font-size:\s*16px(?:\s*!important)?;/)
    expect(globalCss).toContain('--workspace-page-gutter: 14px;')
    expect(globalCss).toContain('overscroll-behavior: contain;')
  })

  it('turns the workspace sidebar into a mobile drawer', () => {
    expect(sidebar).toContain("window.matchMedia('(max-width: 767px)')")
    expect(sidebar).toContain('const isNarrowViewport = ref(false)')
    expect(sidebar).toContain('const mobileExpanded = ref(false)')
    expect(sidebar).toContain('class="sidebar-mobile-backdrop"')
    expect(sidebar).toContain(':aria-expanded="!isSidebarCollapsed"')
  })

  it('allows campaign search, cards and details to reflow', () => {
    expect(campaign).toContain('class="campaign-filter-bar')
    expect(campaign).toContain('class="campaign-card-head')
    expect(campaign).toContain('@media (max-width: 720px)')
    expect(campaignDetail).toContain('grid grid-cols-1 gap-[8px] sm:grid-cols-2 xl:grid-cols-4')
    expect(campaignDetail).toContain('class="campaign-detail-head')
  })

  it('stacks campaign creation forms on narrow screens', () => {
    expect(createAdUnit).toContain('grid grid-cols-1 gap-[10px] md:grid-cols-2')
    expect(createAdUnit).not.toContain('class="grid grid-cols-2 gap-[10px]"')
  })

  it('stacks settings grids and bounds tall dialogs to the viewport', () => {
    expect(settingsCss).toContain('@media (max-width: 520px)')
    expect(settingsCss).toContain('.sn-oauth-steps,.sn-summary-grid { grid-template-columns: 1fr; }')
    expect(organizationDialog).toContain('h-[min(702px,calc(100dvh-24px))]')
  })
})
