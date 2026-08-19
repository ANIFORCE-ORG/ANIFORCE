import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (relativePath: string) => readFileSync(new URL(relativePath, import.meta.url), 'utf8')

const globalCss = read('./global.css')
const app = read('../App.vue')
const sidebar = read('../components/layout/SidebarNav.vue')
const home = read('../pages/Home.vue')
const campaign = read('../pages/campaigns/Campaign.vue')
const campaignDetail = read('../pages/campaigns/CampaignDetail.vue')
const createCampaign = read('../pages/campaigns/CreateCampaign.vue')
const createAdUnit = read('../pages/campaigns/CreateAdUnit.vue')
const settingsCss = read('./settings-notion.css')
const organizationDialog = read('../components/settings/OrganizationDetail.vue')

describe('application-wide responsive layout', () => {
  it('provides viewport, overflow and media safety defaults', () => {
    expect(globalCss).toContain('--app-ui-scale: 0.9;')
    expect(globalCss).toContain('transform: scale(var(--app-ui-scale));')
    expect(globalCss).toContain('transform-origin: top left;')
    expect(globalCss).not.toContain('zoom: var(--app-ui-scale);')
    expect(globalCss).toContain('#app .min-h-screen')
    expect(globalCss).toContain('#app .h-screen')
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
    expect(sidebar).toContain("window.matchMedia('(max-width: 1023px)')")
    expect(sidebar).toContain('const isNarrowViewport = ref(false)')
    expect(sidebar).toContain('const mobileExpanded = ref(false)')
    expect(sidebar).toContain('class="sidebar-mobile-backdrop"')
    expect(sidebar).toContain(':aria-expanded="!isSidebarCollapsed"')
  })

  it('forces every workspace content container to remain centered in the main column', () => {
    expect(globalCss).toContain('.workspace-page-canvas:has(> .sidebar-rail-spacer)')
    expect(globalCss).toContain('--workspace-sidebar-width: 240px;')
    expect(globalCss).toContain('--workspace-content-max-width: 1920px;')
    expect(globalCss).toContain('width: min(100%, var(--workspace-content-max-width)) !important;')
    expect(globalCss).toContain('max-width: var(--workspace-content-max-width) !important;')
    expect(globalCss).toContain('margin-right: auto !important;')
    expect(globalCss).toContain('margin-left: auto !important;')
    expect(globalCss).toMatch(/\.workspace-page-header \{[\s\S]*?padding-inline:\s*max\(/)
    expect(globalCss).toContain('padding-right: 0;')
    expect(globalCss).not.toContain('padding-right: var(--workspace-sidebar-width, 240px);')
    expect(home).toMatch(/\.landing-document \{[\s\S]*?margin: 0 auto;/)
  })

  it('clips the scaled application inside the real viewport', () => {
    expect(globalCss).toMatch(/#app \{[^}]*width:\s*100%;[^}]*overflow-x:\s*hidden;/)
    expect(globalCss).toMatch(/#app:has\(\.workspace-app-shell\) \{[^}]*height:\s*100dvh;[^}]*overflow:\s*hidden;/)
    expect(globalCss).toMatch(/#app > div:first-child \{[^}]*width:\s*calc\(100% \+ 11\.111111%\);/)
    expect(globalCss).toMatch(/#app > div:first-child \{[^}]*transform:\s*scale\(var\(--app-ui-scale\)\);/)
    expect(globalCss).not.toMatch(/#app \{[^}]*width:\s*calc\(100% \+ 11\.111111%\);/)
  })

  it('switches the sidebar to its overlay rail before the content column becomes cramped', () => {
    expect(sidebar).toContain("window.matchMedia('(max-width: 1023px)')")
    expect(sidebar).not.toContain("window.matchMedia('(max-width: 767px)')")
  })

  it('uses a single subtle Notion hairline between the sidebar and content', () => {
    expect(sidebar).toContain('--sidebar-divider: rgba(55, 53, 47, 0.08);')
    expect(sidebar).toMatch(/\.sidebar-notion \{[\s\S]*?border-right: 1px solid var\(--sidebar-divider\) !important;/)
    expect(sidebar).not.toContain('.sidebar-notion::after')
    expect(sidebar).not.toContain('linear-gradient(90deg')
  })

  it('lets the desktop divider resize both workspace columns in sync', () => {
    expect(sidebar).toContain("const SIDEBAR_WIDTH_KEY = 'animagus_sidebar_width'")
    expect(sidebar).toContain('const SIDEBAR_MIN_WIDTH = 200')
    expect(sidebar).toContain('const SIDEBAR_MAX_WIDTH = 420')
    expect(sidebar).toContain('Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, width))')
    expect(sidebar).toContain('class="sidebar-resize-handle"')
    expect(sidebar).toContain('v-if="!isNarrowViewport && !isSidebarCollapsed"')
    expect(sidebar).toContain('role="separator"')
    expect(sidebar).toContain('@pointerdown="startSidebarResize"')
    expect(sidebar).toContain('@keydown="handleSidebarResizeKeydown"')
    expect(sidebar).toContain(':style="{ width: layoutSidebarWidth }"')
    expect(sidebar).toContain(':style="{ width: renderedSidebarWidth }"')
    expect(sidebar).toContain("document.documentElement.style.setProperty('--workspace-sidebar-width', layoutSidebarWidth.value)")
    expect(sidebar).toMatch(/\.sidebar-resize-handle \{[\s\S]*?cursor: col-resize;/)
    expect(sidebar).toMatch(/\.sidebar-notion\.is-resizing[\s\S]*?transition: none !important;/)
  })

  it('keeps workspace scrollbars narrow, right-aligned and outside centering math', () => {
    expect(globalCss).toContain('--workspace-scrollbar-size: 8px;')
    expect(globalCss).toContain('scrollbar-gutter: auto;')
    expect(globalCss).toMatch(/\.workspace-page-canvas :where\([\s\S]*?scrollbar-gutter: stable;/)
    expect(globalCss).toContain('scrollbar-width: thin;')
    expect(globalCss).toContain('width: var(--workspace-scrollbar-size);')
    expect(globalCss).toContain('::-webkit-scrollbar-button')
  })

  it('prevents the scaled workspace shell from creating a second document scrollbar', () => {
    expect(app).toContain("workspace-app-shell bg-white")
    expect(globalCss).toContain('html:has(.workspace-app-shell)')
    expect(globalCss).toContain('body:has(.workspace-app-shell)')
    expect(globalCss).toMatch(/body:has\(\.workspace-app-shell\) \{[\s\S]*?height: 100dvh;[\s\S]*?overflow: hidden;/)
  })

  it('allows campaign search, cards and details to reflow', () => {
    expect(campaign).toContain('class="campaign-filter-bar')
    expect(campaign).toContain('class="campaign-card-head')
    expect(campaign).toContain('@media (max-width: 720px)')
    expect(campaignDetail).toContain('grid grid-cols-1 gap-[8px] sm:grid-cols-2 xl:grid-cols-4')
    expect(campaignDetail).toContain('class="campaign-detail-head')
  })

  it('stacks campaign creation forms on narrow screens', () => {
    expect(createCampaign).toContain('class="campaign-stepper-scroll')
    expect(createCampaign).toContain('grid grid-cols-1 gap-[12px] md:grid-cols-2')
    expect(createAdUnit).toContain('grid grid-cols-1 gap-[10px] md:grid-cols-2')
    expect(createAdUnit).not.toContain('class="grid grid-cols-2 gap-[10px]"')
  })

  it('stacks settings grids and bounds tall dialogs to the viewport', () => {
    expect(settingsCss).toContain('@media (max-width: 520px)')
    expect(settingsCss).toContain('.sn-oauth-steps,.sn-summary-grid { grid-template-columns: 1fr; }')
    expect(organizationDialog).toContain('h-[min(702px,calc(100dvh-24px))]')
  })
})
