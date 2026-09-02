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

  it('uses the same live connection controls for full-page and workspace rendering', () => {
    const initialize = dashboard.slice(dashboard.indexOf('const initialize = async'), dashboard.indexOf('const changePeriod'))
    expect(initialize).toContain('platformApi.getAllConnections()')
    expect(initialize).toContain('await loadAccounts()')
    expect(initialize).toContain('if (!props.workspaceOverview) await loadOverview()')
    expect(initialize).not.toContain('loading.value = false\n    return')
    expect(dashboard).toContain('<div class="page-actions replay-actions">')
  })

  it('uses active connection and account filters instead of unsupported project/platform mocks', () => {
    expect(dashboard).toContain('v-model="connectionId"')
    expect(dashboard).toContain('v-model="accountId"')
    expect(dashboard).toContain("status: 'active'")
    expect(dashboard).not.toContain('CANDY BLAST')
    expect(dashboard).not.toContain('<option>Google</option>')
    expect(dashboard).not.toContain('<option>TikTok</option>')
  })

  it('organizes by objective because success is a different metric per objective', () => {
    for (const label of ['OUTCOME_SALES', 'OUTCOME_LEADS', 'objective-switch', 'selectObjective']) {
      expect(dashboard).toContain(label)
    }
    expect(dashboard).toContain('isSales')
    expect(dashboard).toContain('formatRoas')
    expect(dashboard).toContain('客单价')
    expect(dashboard).toContain('funnel')
    expect(dashboard).toContain('ROAS')
    expect(dashboard).toContain('事件漏斗')
    expect(dashboard).toContain('投放层级分析')
    expect(dashboard).toContain('drillInto')
    expect(dashboard).toContain('breadcrumb')
    expect(dashboard).toContain('accessible_with_no_rows')
    expect(dashboard).not.toContain('平台健康度')
    expect(readFileSync(new URL('../components/dashboard/DataSyncDialog.vue', import.meta.url), 'utf8')).toContain('固定同步 <strong>AdSet 日级数据</strong>')
  })

  it('does not retain the previous fabricated business values', () => {
    for (const mock of ['$28,460', '4,832', '2.42x', 'Candy Blast Meta UA', 'DramaBox Google Ads']) {
      expect(dashboard).not.toContain(mock)
    }
  })
})
