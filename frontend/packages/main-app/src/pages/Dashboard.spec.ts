import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const dashboard = readFileSync(new URL('./Dashboard.vue', import.meta.url), 'utf8')
const dashboardApi = readFileSync(new URL('../api/dashboard.ts', import.meta.url), 'utf8')

describe('Dashboard real Meta data contract', () => {
  it('keeps local refresh separate from explicit AdSet synchronization', () => {
    expect(dashboard).toContain('getMetaDashboardOverview')
    expect(dashboardApi).toContain('/dashboard/meta-overview?')
    expect(dashboardApi).toContain("'/meta-facts/sync'")
    expect(dashboard).toContain('DataSyncDialog')
    expect(dashboard).toContain('配置数据同步')
    expect(dashboard).toContain('刷新本地数据视图')
  })

  it('uses active connection and account filters instead of unsupported project/platform mocks', () => {
    expect(dashboard).toContain('v-model="connectionId"')
    expect(dashboard).toContain('v-model="accountId"')
    expect(dashboard).toContain("status: 'active'")
    expect(dashboard).not.toContain('CANDY BLASTER')
    expect(dashboard).not.toContain('<option>Google</option>')
    expect(dashboard).not.toContain('<option>TikTok</option>')
  })

  it('shows the supported Lead metrics and honest unavailable states', () => {
    for (const label of ['总消耗', 'Leads', 'CPL', 'Link CTR', 'Link Clicks', 'Impressions']) {
      expect(dashboard).toContain(`label: '${label}'`)
    }
    expect(dashboard).toContain('机会与风险')
    expect(dashboard).toContain('Meta 投放组合')
    expect(dashboard).toContain('AdSet × 日期')
    expect(dashboard).toContain('accessible_with_no_rows')
    expect(dashboard).not.toContain('平台健康度')
    expect(readFileSync(new URL('../components/dashboard/DataSyncDialog.vue', import.meta.url), 'utf8')).toContain('固定同步 <strong>AdSet 日级数据</strong>')
    expect(dashboard).not.toContain('平均 ROAS')
  })

  it('does not retain the previous fabricated business values', () => {
    for (const mock of ['$28,460', '4,832', '2.42x', 'Candy Blast Meta UA', 'DramaBox Google Ads']) {
      expect(dashboard).not.toContain(mock)
    }
  })
})
