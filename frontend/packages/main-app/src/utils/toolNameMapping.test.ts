import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { parse as parseSfc } from 'vue/compiler-sfc'
import { describe, expect, it } from 'vitest'

import { getHiddenToolActivity, getToolPresentation } from './toolNameMapping'

describe('tool presentation registry', () => {
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
})

describe('MessageView tool activity contract', () => {
  const source = readFileSync(
    fileURLToPath(new URL('../components/agent/MessageView.vue', import.meta.url)),
    'utf8',
  )
  const { descriptor, errors } = parseSfc(source, { filename: 'MessageView.vue' })
  const template = descriptor.template?.content || ''

  it('uses one run activity fallback without rendering reasoning content', () => {
    expect(errors).toHaveLength(0)
    expect(template).toContain("block.type === 'thinking'")
    expect(template).toContain('v-if="runActivity"')
    expect(template).toContain('runActivity.label')
    expect(template).not.toContain('{{ block.thinking }}')
    expect(template).not.toContain('expandedThinking')
    expect(template).not.toContain('thinking-char-hint')
  })

  it('renders productized tool activity without raw payload controls', () => {
    expect(template).toContain('toolPresentation(block).title')
    expect(template).toContain('toolPresentation(block).summary')
    expect(template).not.toContain('toolInput(block)')
    expect(template).not.toContain('toolBlockResultText(block)')
    expect(template).not.toContain('tool-pre')
    expect(template).not.toContain('expandedTools')
  })
})
