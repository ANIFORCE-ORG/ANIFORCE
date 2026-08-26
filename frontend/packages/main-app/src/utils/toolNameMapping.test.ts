import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { parse as parseSfc } from 'vue/compiler-sfc'
import { describe, expect, it } from 'vitest'

import { getHiddenToolActivity, getToolPresentation, hasToolPresentationDefinition } from './toolNameMapping'

describe('tool presentation registry', () => {
  it('covers every business MCP registered by the Agent', () => {
    const registrySource = readFileSync(
      fileURLToPath(new URL('../../../../../aniforce-agent/app/agent/business_skills/registry.py', import.meta.url)),
      'utf8',
    )
    const registryBlock = /MCP_TOOL_NAMES\s*=\s*frozenset\(\{([\s\S]*?)\}\)/.exec(registrySource)?.[1] || ''
    const registeredTools = [...registryBlock.matchAll(/["']([a-z][a-z0-9_]*)["']/g)].map(match => match[1])
    const missingPresentations = registeredTools.filter(toolName => !hasToolPresentationDefinition(toolName))

    expect(registeredTools.length).toBeGreaterThan(0)
    expect(missingPresentations).toEqual([])
  })

  it('maps a known English tool name to state-specific business copy', () => {
    expect(getToolPresentation('list_projects', 'running')).toMatchObject({
      visible: true,
      category: 'read',
      icon: 'folder_open',
      title: '正在查询项目列表',
    })
    expect(getToolPresentation('list_projects', 'completed').title).toBe('已查询项目列表')
    expect(getToolPresentation('list_projects', 'error').title).toBe('查询项目列表失败')
  })

  it('hides internal tools while retaining safe run activity copy', () => {
    expect(getToolPresentation('request_workspace_projection', 'running').visible).toBe(false)
    expect(getHiddenToolActivity('request_workspace_projection', 'running')).toEqual({
      icon: 'dashboard_customize',
      label: '正在更新工作台',
    })
    expect(getToolPresentation('load_skill', 'running').visible).toBe(false)
    expect(getHiddenToolActivity('select_campaign_skill', 'completed')?.label).toBe('正在准备处理流程')
  })

  it('never exposes an unknown raw tool name', () => {
    const presentation = getToolPresentation('vendor_private_lookup_v2', 'running')
    expect(presentation.title).toBe('正在处理任务')
    expect(presentation.title).not.toContain('vendor_private_lookup_v2')
  })

  it('summarizes only allowlisted collection counts', () => {
    expect(getToolPresentation('list_projects', 'completed', {
      projects: [{ id: 'p1' }, { id: 'p2' }],
      secret: 'must-not-render',
    }).summary).toBe('找到 2 个项目')
    expect(getToolPresentation('list_materials', 'completed', '{"materials":[{}, {}, {}]}').summary).toBe('找到 3 个素材')
  })

  it('presents each Meta performance tool as a distinct business activity', () => {
    const overview = {
      window: { since: '2026-08-19', until: '2026-08-25' },
      kpis: { spend: 100 },
      accounts: [{ account_id: '1', account_name: 'Main account' }],
      campaigns: [{ campaign_id: 'c1' }, { campaign_id: 'c2' }],
      adsets: [{ adset_id: 'a1' }, { adset_id: 'a2' }, { adset_id: 'a3' }],
      trend: [{ date: '2026-08-19' }, { date: '2026-08-20' }],
      data_quality: { accounts_with_rows: 11, accounts_expected: 102 },
    }

    expect(getToolPresentation('list_meta_ad_accounts_with_spend', 'running').title).toBe('正在汇总 Meta 投放数据')
    expect(getToolPresentation('list_meta_ad_accounts_with_spend', 'completed', overview).summary).toBe('11 / 102 个账号有数据')
    expect(getToolPresentation('get_meta_account_performance', 'completed', overview).summary).toBe('Main account · 2 天')
    expect(getToolPresentation('get_meta_campaign_performance', 'completed', overview).summary).toBe('2 个 Campaign · 3 个 AdSet')
    expect(getToolPresentation('get_meta_performance_trend', 'completed', overview).summary).toBe('2 天 · 08-19 至 08-25')
  })
})

describe('MessageView tool activity contract', () => {
  const source = readFileSync(
    fileURLToPath(new URL('../components/agent/MessageView.vue', import.meta.url)),
    'utf8',
  )
  const { descriptor, errors } = parseSfc(source, { filename: 'MessageView.vue' })
  const template = descriptor.template?.content || ''

  it('keeps process details collapsed until the user opens them', () => {
    expect(errors).toHaveLength(0)
    expect(source).toContain('const processExpanded = ref(false)')
    expect(template).toContain(':aria-expanded="processExpanded"')
    expect(template).toContain('v-if="processExpanded"')
    expect(template).toContain('thinkingText(item)')
    expect(template).toContain('runActivity && !hasProcessDetails')
    expect(template).not.toContain('{{ block.thinking }}')
    expect(template).not.toContain('thinking-char-hint')
  })

  it('renders productized process activity without raw payload controls', () => {
    expect(template).toContain('processToolPresentation(item).title')
    expect(template).toContain('processToolPresentation(item).summary')
    expect(template).not.toContain('toolInput(')
    expect(template).not.toContain('toolBlockResultText(')
    expect(template).not.toContain('tool-pre')
    expect(template).not.toContain('expandedTools')
  })
})
