const wait = (ms = 120) => new Promise(resolve => setTimeout(resolve, ms))

const now = '2026-08-05T10:00:00Z'

const projects: any[] = [
  { id: 'proj-001', name: 'Candy Match 全球增长', product: 'Candy Blast', description: '三消手游欧美市场增长项目', game_type: '休闲三消', target_market: '美国、加拿大、英国', tags: ['欧美', 'iOS', '规模化'], total_budget: 120000, spent: 68350, status: 'running', manager: '陈晓', start_date: '2026-07-01', end_date: '2026-09-30', created_at: '2026-06-20T08:00:00Z', updated_at: now },
  { id: 'proj-002', name: '短剧 App 日韩测试', product: 'DramaWave', description: '日韩短剧订阅产品冷启动', game_type: '短剧应用', target_market: '日本、韩国', tags: ['短剧', '订阅', '冷启动'], total_budget: 80000, spent: 29580, status: 'running', manager: '林薇', start_date: '2026-07-15', end_date: '2026-09-15', created_at: '2026-07-03T08:00:00Z', updated_at: now },
  { id: 'proj-003', name: 'RPG 新版本召回', product: 'Dragon Realm', description: '新版本上线用户召回', game_type: 'RPG', target_market: '东南亚', tags: ['召回', '安卓', 'RPG'], total_budget: 50000, spent: 42100, status: 'paused', manager: '王锐', start_date: '2026-06-10', end_date: '2026-08-20', created_at: '2026-06-01T08:00:00Z', updated_at: now },
  { id: 'proj-004', name: 'AI 修图工具首发', product: 'PicMagic AI', description: '生产力工具全球首发测试', game_type: '工具应用', target_market: '全球', tags: ['AI', '工具', '首发'], total_budget: 35000, spent: 8250, status: 'draft', manager: '赵晴', start_date: '2026-08-01', end_date: '2026-10-01', created_at: '2026-07-25T08:00:00Z', updated_at: now },
]

const campaigns: any[] = [
  { id: 'camp-001', project_id: 'proj-001', project_name: 'Candy Match 全球增长', name: 'Meta · UGC 通关挑战', description: '以玩家反应和高难关卡为核心', platform: 'Meta', connection_id: 'conn-meta-001', account_id: 'act_10240001', objective: 'App Promotion', buying_type: 'Auction', budget_type: 'daily', budget: 32000, spent: 18420, status: 'running', material_ids: ['mat-001', 'mat-002', 'mat-003'], start_date: '2026-07-20', end_date: '2026-08-20', created_at: '2026-07-18T08:00:00Z', updated_at: now },
  { id: 'camp-002', project_id: 'proj-001', project_name: 'Candy Match 全球增长', name: 'Google · 高价值用户扩量', platform: 'Google', connection_id: 'conn-google-001', account_id: '652-310-9921', objective: 'Install', budget_type: 'daily', budget: 28000, spent: 15980, status: 'running', material_ids: ['mat-002', 'mat-004'], start_date: '2026-07-25', end_date: '2026-08-31', created_at: '2026-07-22T08:00:00Z', updated_at: now },
  { id: 'camp-003', project_id: 'proj-002', project_name: '短剧 App 日韩测试', name: 'TikTok · 霸总短剧钩子测试', platform: 'TikTok', account_id: 'tt_7788021', objective: 'Conversions', budget_type: 'daily', budget: 24000, spent: 9280, status: 'running', material_ids: ['mat-005', 'mat-006'], start_date: '2026-07-28', end_date: '2026-08-28', created_at: '2026-07-26T08:00:00Z', updated_at: now },
  { id: 'camp-004', project_id: 'proj-003', project_name: 'RPG 新版本召回', name: 'Meta · Boss 战老用户召回', platform: 'Meta', connection_id: 'conn-meta-001', account_id: 'act_10240002', objective: 'Engagement', budget_type: 'lifetime', budget: 30000, spent: 21100, status: 'paused', material_ids: ['mat-007', 'mat-008'], start_date: '2026-06-25', end_date: '2026-08-15', created_at: '2026-06-22T08:00:00Z', updated_at: now },
  { id: 'camp-005', project_id: 'proj-004', project_name: 'AI 修图工具首发', name: 'Google · AI 功能关键词', platform: 'Google', connection_id: 'conn-google-001', account_id: '652-310-9921', objective: 'Traffic', budget_type: 'daily', budget: 12000, spent: 1850, status: 'draft', material_ids: ['mat-004'], start_date: '2026-08-05', end_date: '2026-09-05', created_at: '2026-08-01T08:00:00Z', updated_at: now },
]

const materialImage = (index: number) => `/images/creatives/${[
  'creative_game_001.jpg', 'creative_game_002.jpg', 'creative_game_003.jpg', 'creative_game_004.jpg',
  'creative_drama_001.jpg', 'creative_drama_002.jpg', 'ai_candy_hook_001.jpg', 'ai_candy_combo_001.jpg',
][index]}`

const materials: any[] = [
  { id: 'mat-001', user_id: 'admin-001', project_ids: ['proj-001'], campaign_ids: ['camp-001'], name: 'UGC 玩家差一步通关', type: 'image', status: 'running', url: materialImage(0), thumbnail_url: materialImage(0), ctr_estimate: 3.42, tags: ['UGC', '失败钩子', '高点击'], file_size: 1480000, created_at: '2026-07-18T09:00:00Z', media_kind: 'image', format: 'JPG', width: 1080, height: 1080, ratio: '1:1', source: 'local', creator: 'Creative Team A', rights: '已授权', platforms: ['Meta'], review_status: '已通过', source_account: 'act_10240001', placements: ['Feed'], score: 91, fatigue: 42 },
  { id: 'mat-002', user_id: 'admin-001', project_ids: ['proj-001'], campaign_ids: ['camp-001', 'camp-002'], name: '糖果连击爽感展示', type: 'image', status: 'running', url: materialImage(1), thumbnail_url: materialImage(1), ctr_estimate: 2.86, tags: ['连击', '爽感', '产品演示'], file_size: 1720000, created_at: '2026-07-21T09:00:00Z', media_kind: 'image', format: 'JPG', width: 1080, height: 1350, ratio: '4:5', source: 'ai_generated', creator: 'AI Studio', rights: '商用授权', platforms: ['Meta', 'Google'], review_status: '已通过', source_account: 'act_10240001', placements: ['Feed', 'Display'], score: 86, fatigue: 55 },
  { id: 'mat-003', user_id: 'admin-001', project_ids: ['proj-001'], campaign_ids: ['camp-001'], name: '30 秒高难关卡挑战', type: 'video', status: 'fatigue', url: materialImage(2), thumbnail_url: materialImage(2), ctr_estimate: 1.65, tags: ['挑战', '倒计时', '竖版'], duration: 30, file_size: 12800000, created_at: '2026-07-11T09:00:00Z', media_kind: 'video', format: 'MP4', width: 1080, height: 1920, ratio: '9:16', source: 'oss_upload', creator: 'Studio North', rights: '已授权', platforms: ['Meta'], review_status: '需复审', source_account: 'act_10240001', placements: ['Reels', 'Stories'], score: 63, fatigue: 84 },
  { id: 'mat-004', user_id: 'admin-001', project_ids: ['proj-001', 'proj-004'], campaign_ids: ['camp-002', 'camp-005'], name: 'AI 一键美化前后对比', type: 'image', status: 'ready', url: materialImage(3), thumbnail_url: materialImage(3), ctr_estimate: 2.24, tags: ['前后对比', 'AI', '功能展示'], file_size: 980000, created_at: '2026-08-01T09:00:00Z', media_kind: 'image', format: 'JPG', width: 1200, height: 628, ratio: '1.91:1', source: 'ai_generated', creator: 'Growth Design', rights: '商用授权', platforms: ['Google'], review_status: '待审核', source_account: '652-310-9921', placements: ['Display'], score: 78, fatigue: 18 },
  { id: 'mat-005', user_id: 'admin-001', project_ids: ['proj-002'], campaign_ids: ['camp-003'], name: '霸总雨夜追妻片段', type: 'video', status: 'running', url: materialImage(4), thumbnail_url: materialImage(4), ctr_estimate: 3.74, tags: ['情绪冲突', '短剧', '前三秒'], duration: 22, file_size: 9200000, created_at: '2026-07-27T09:00:00Z', media_kind: 'video', format: 'MP4', width: 1080, height: 1920, ratio: '9:16', source: 'tiktok_import', creator: 'DramaWave', rights: '自有版权', platforms: ['TikTok'], review_status: '已通过', source_account: 'tt_7788021', placements: ['TikTok Feed'], score: 94, fatigue: 36 },
  { id: 'mat-006', user_id: 'admin-001', project_ids: ['proj-002'], campaign_ids: ['camp-003'], name: '豪门身份反转卡点', type: 'video', status: 'running', url: materialImage(5), thumbnail_url: materialImage(5), ctr_estimate: 3.18, tags: ['反转', '卡点', '短剧'], duration: 18, file_size: 7600000, created_at: '2026-07-29T09:00:00Z', media_kind: 'video', format: 'MP4', width: 1080, height: 1920, ratio: '9:16', source: 'local', creator: 'Drama Creative Lab', rights: '自有版权', platforms: ['TikTok'], review_status: '已通过', source_account: 'tt_7788021', placements: ['TikTok Feed'], score: 89, fatigue: 31 },
  { id: 'mat-007', user_id: 'admin-001', project_ids: ['proj-003'], campaign_ids: ['camp-004'], name: 'Boss 狂暴阶段实录', type: 'image', status: 'fatigue', url: materialImage(6), thumbnail_url: materialImage(6), ctr_estimate: 1.48, tags: ['Boss', 'RPG', '召回'], file_size: 1380000, created_at: '2026-06-20T09:00:00Z', media_kind: 'image', format: 'JPG', width: 1080, height: 1080, ratio: '1:1', source: 'meta_import', creator: 'RPG LiveOps', rights: '已授权', platforms: ['Meta'], review_status: '需复审', source_account: 'act_10240002', placements: ['Feed'], score: 58, fatigue: 88 },
  { id: 'mat-008', user_id: 'admin-001', project_ids: ['proj-003'], campaign_ids: ['camp-004'], name: '回归即送传奇装备', type: 'image', status: 'ready', url: materialImage(7), thumbnail_url: materialImage(7), ctr_estimate: 2.05, tags: ['回归奖励', '装备', '福利'], file_size: 1640000, created_at: '2026-07-30T09:00:00Z', media_kind: 'image', format: 'JPG', width: 1080, height: 1350, ratio: '4:5', source: 'ai_generated', creator: 'RPG LiveOps', rights: '已授权', platforms: ['Meta'], review_status: '待审核', source_account: 'act_10240002', placements: ['Feed'], score: 76, fatigue: 22 },
]

const connections: any[] = [
  { id: 'conn-meta-001', platform: 'Meta', account_id: 'bm_66502001', account_name: 'ANIFORCE Global Meta', status: 'active', scopes: ['ads_management', 'business_management'], token_expires_at: '2027-01-31T00:00:00', created_at: '2026-05-12T08:00:00Z', updated_at: now },
  { id: 'conn-google-001', platform: 'Google', account_id: '652-310-9921', account_name: 'ANIFORCE Google Ads', status: 'active', scopes: ['adwords'], token_expires_at: '2027-02-15T00:00:00', created_at: '2026-05-20T08:00:00Z', updated_at: now },
  { id: 'conn-tiktok-001', platform: 'TikTok', account_id: 'tt_7788021', account_name: 'DramaWave TikTok', status: 'active', scopes: ['advertiser.read', 'campaign.read'], token_expires_at: '2026-12-20T00:00:00', created_at: '2026-06-15T08:00:00Z', updated_at: now },
]

const organizations: any[] = [
  { id: 'org-001', name: 'ANIFORCE Growth Lab', org_code: 'ANI-GROWTH', description: '全球化广告增长与素材创新团队', owner_id: 'admin-001', status: 'active', member_count: 5, role: 'admin', created_at: '2026-03-01T08:00:00Z' },
]

const members: any[] = [
  { id: 'member-001', user_id: 'admin-001', user_name: 'Admin', user_email: 'admin@animagus.ai', role: 'admin', joined_at: '2026-03-01T08:00:00Z' },
  { id: 'member-002', user_id: 'user-002', user_name: '林薇', user_email: 'linwei@aniforce.demo', role: 'member', joined_at: '2026-04-10T08:00:00Z' },
  { id: 'member-003', user_id: 'user-003', user_name: '王锐', user_email: 'wangrui@aniforce.demo', role: 'member', joined_at: '2026-05-18T08:00:00Z' },
  { id: 'member-004', user_id: 'user-004', user_name: '赵晴', user_email: 'zhaoqing@aniforce.demo', role: 'member', joined_at: '2026-06-05T08:00:00Z' },
  { id: 'member-005', user_id: 'user-005', user_name: 'Alex Chen', user_email: 'alex@aniforce.demo', role: 'member', joined_at: '2026-06-22T08:00:00Z' },
]

const agentSessions: any[] = [
  { id: 'session-001', session_id: 'session-001', title: 'Candy Match 素材诊断', status: 'completed', created_at: '2026-08-04T09:20:00Z', updated_at: '2026-08-04T09:28:00Z', messages: [{ id: 'msg-001', role: 'assistant', content: 'Candy Match 当前高点击素材集中在失败钩子与连击爽感，建议优先扩展 UGC 变体。', created_at: '2026-08-04T09:28:00Z' }] },
  { id: 'session-002', session_id: 'session-002', title: '日韩短剧投放计划', status: 'completed', created_at: '2026-08-03T15:10:00Z', updated_at: '2026-08-03T15:18:00Z', messages: [{ id: 'msg-002', role: 'assistant', content: '日韩短剧测试建议按情绪冲突、身份反转、悬念截断三类钩子分组测试。', created_at: '2026-08-03T15:18:00Z' }] },
]

let lastAgentPrompt = ''

const jsonResponse = (data: unknown, status = 200) => new Response(JSON.stringify(data), {
  status,
  headers: { 'Content-Type': 'application/json; charset=utf-8' },
})

async function readBody(init?: RequestInit): Promise<any> {
  const body = init?.body
  if (!body) return {}
  if (typeof body === 'string') {
    try { return JSON.parse(body) } catch { return {} }
  }
  if (body instanceof FormData) {
    const result: Record<string, any> = {}
    body.forEach((value, key) => { result[key] = value })
    return result
  }
  return {}
}

function createRecord(collection: any[], body: any, prefix: string, defaults: Record<string, unknown>) {
  const item = { id: `${prefix}-${Date.now()}`, ...defaults, ...body, created_at: now, updated_at: now }
  collection.unshift(item)
  return item
}

function mockAgentEvents(runId: string): Response {
  const answer = `这是 Demo Agent 基于本地样例数据的回答。针对“${lastAgentPrompt || '当前投放'}”，建议先查看高消耗低回收计划，再复制高 CTR 素材的前三秒钩子进行小预算测试。`
  const events = [
    ['runtime.started', { run_id: runId, task_id: runId }],
    ['message.updated', { delta: answer }],
    ['message.completed', { content: answer, usage: { input: 128, output: 86, totalTokens: 214 }, timestamp: Date.now() }],
    ['runtime.completed', { status: 'completed' }],
  ].map(([event, data], index) => `id: ${index + 1}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`).join('')
  return new Response(events, { status: 200, headers: { 'Content-Type': 'text/event-stream; charset=utf-8' } })
}

async function handleMockRequest(url: URL, init?: RequestInit): Promise<Response> {
  await wait()
  const path = url.pathname.replace(/^\/api\/v1/, '')
  const method = (init?.method || 'GET').toUpperCase()
  const body = await readBody(init)

  if (path === '/auth/validate') return jsonResponse({ success: true })
  if (path === '/auth/refresh') return jsonResponse({ success: true, data: { access_token: 'demo-token', refresh_token: 'demo-refresh', token_type: 'bearer' } })

  if (path === '/projects' && method === 'GET') {
    const status = url.searchParams.get('status')
    const limit = Number(url.searchParams.get('limit') || projects.length)
    return jsonResponse({ projects: projects.filter(item => !status || item.status === status).slice(0, limit) })
  }
  if (path === '/projects' && method === 'POST') return jsonResponse(createRecord(projects, body, 'proj', { game_type: '应用', target_market: '全球', tags: [], total_budget: 0, spent: 0, status: 'draft', manager: 'Admin' }))
  const projectMatch = path.match(/^\/projects\/([^/]+)$/)
  if (projectMatch) {
    const index = projects.findIndex(item => item.id === projectMatch[1])
    if (method === 'GET') return jsonResponse(projects[index] || projects[0])
    if (method === 'DELETE') { if (index >= 0) projects.splice(index, 1); return jsonResponse({ success: true }) }
    if (index >= 0 && (method === 'PUT' || method === 'PATCH')) { projects[index] = { ...projects[index], ...body, updated_at: now }; return jsonResponse(projects[index]) }
  }

  if (path === '/campaigns' && method === 'GET') {
    const projectId = url.searchParams.get('project_id')
    const status = url.searchParams.get('status')
    const limit = Number(url.searchParams.get('limit') || campaigns.length)
    return jsonResponse({ campaigns: campaigns.filter(item => (!projectId || item.project_id === projectId) && (!status || item.status === status)).slice(0, limit) })
  }
  if (path === '/campaigns' && method === 'POST') {
    const project = projects.find(item => item.id === body.project_id)
    return jsonResponse(createRecord(campaigns, { ...body, project_name: project?.name || '未分组项目' }, 'camp', { spent: 0, status: 'draft', material_ids: [], start_date: '2026-08-05' }))
  }
  const campaignMaterialsMatch = path.match(/^\/campaigns\/([^/]+)\/materials$/)
  if (campaignMaterialsMatch) return jsonResponse({ materials: materials.filter(item => item.campaign_ids.includes(campaignMaterialsMatch[1])) })
  const campaignStatusMatch = path.match(/^\/campaigns\/([^/]+)\/status$/)
  if (campaignStatusMatch && method === 'PUT') {
    const item = campaigns.find(value => value.id === campaignStatusMatch[1])
    if (item) item.status = body.status
    return jsonResponse({ message: '状态已更新' })
  }
  const campaignMatch = path.match(/^\/campaigns\/([^/]+)$/)
  if (campaignMatch) {
    const index = campaigns.findIndex(item => item.id === campaignMatch[1])
    if (method === 'GET') return jsonResponse(campaigns[index] || campaigns[0])
    if (method === 'DELETE') { if (index >= 0) campaigns.splice(index, 1); return jsonResponse({ success: true }) }
    if (index >= 0 && (method === 'PUT' || method === 'PATCH')) { campaigns[index] = { ...campaigns[index], ...body, updated_at: now }; return jsonResponse(campaigns[index]) }
  }

  if (path === '/materials/images/list') return jsonResponse({ images: materials.map(item => ({ filename: item.name, size: item.file_size, url: item.url })) })
  if (path === '/materials' && method === 'GET') {
    const projectId = url.searchParams.get('project_id')
    const campaignId = url.searchParams.get('campaign_id')
    const type = url.searchParams.get('type')
    const limit = Number(url.searchParams.get('limit') || materials.length)
    return jsonResponse({ materials: materials.filter(item => (!projectId || item.project_ids.includes(projectId)) && (!campaignId || item.campaign_ids.includes(campaignId)) && (!type || item.type === type)).slice(0, limit) })
  }
  if (path === '/materials' && method === 'POST') return jsonResponse(createRecord(materials, body, 'mat', { user_id: 'admin-001', project_ids: [], campaign_ids: [], status: 'ready', tags: [], created_at: now }))
  if ((path === '/materials/upload' || path === '/materials/upload-with-metadata') && method === 'POST') {
    const file = body.file || body.files
    const item = createRecord(materials, { name: body.name || file?.name || '新上传素材', type: body.media_kind || 'image', media_kind: body.media_kind || 'image', url: materialImage(0), thumbnail_url: materialImage(0), tags: body.tags ? JSON.parse(body.tags) : ['新上传'] }, 'mat', { user_id: 'admin-001', project_ids: [], campaign_ids: [], status: 'ready', created_at: now })
    return jsonResponse(path.endsWith('/upload') ? { materials: [item] } : item)
  }
  const materialImageMatch = path.match(/^\/materials\/([^/]+)\/image$/)
  if (materialImageMatch) {
    const item = materials.find(value => value.id === materialImageMatch[1]) || materials[0]
    return jsonResponse({ material_id: item.id, filename: item.name, mime_type: item.media_kind === 'video' ? 'video/mp4' : 'image/jpeg', size: item.file_size || 0, data: '', url: item.thumbnail_url || item.url })
  }
  const materialProjectMatch = path.match(/^\/materials\/([^/]+)\/projects\/([^/]+)$/)
  if (materialProjectMatch) {
    const item = materials.find(value => value.id === materialProjectMatch[1])
    if (item && method === 'POST' && !item.project_ids.includes(materialProjectMatch[2])) item.project_ids.push(materialProjectMatch[2])
    if (item && method === 'DELETE') item.project_ids = item.project_ids.filter((id: string) => id !== materialProjectMatch[2])
    return jsonResponse({ success: true })
  }
  const materialMatch = path.match(/^\/materials\/([^/]+)$/)
  if (materialMatch) {
    const index = materials.findIndex(item => item.id === materialMatch[1])
    if (method === 'GET') return jsonResponse(materials[index] || materials[0])
    if (method === 'DELETE') { if (index >= 0) materials.splice(index, 1); return jsonResponse({ success: true }) }
    if (index >= 0 && (method === 'PUT' || method === 'PATCH')) { materials[index] = { ...materials[index], ...body, updated_at: now }; return jsonResponse(materials[index]) }
  }

  if (path === '/platform-auth/ad-accounts') return jsonResponse([
    { account_id: 'act_10240001', account_name: 'Candy Global · Meta', channel: 'Meta', connection_id: 'conn-meta-001' },
    { account_id: 'act_10240002', account_name: 'RPG LiveOps · Meta', channel: 'Meta', connection_id: 'conn-meta-001' },
    { account_id: '652-310-9921', account_name: 'ANIFORCE · Google Ads', channel: 'Google', connection_id: 'conn-google-001' },
  ].filter(item => !url.searchParams.get('channel') || item.channel === url.searchParams.get('channel')))
  if (path === '/platform-auth/connections') return jsonResponse(connections)
  if (path === '/platform-auth/meta/config') return jsonResponse(connections.find(item => item.platform === 'Meta') || null)
  if (path === '/platform-auth/google/config') return jsonResponse(connections.find(item => item.platform === 'Google') || null)
  if (/^\/platform-auth\/(meta|google)\/config$/.test(path) && method === 'POST') return jsonResponse(connections[0])
  if (/^\/platform-auth\/(meta|google)\/.*sync-adaccounts$/.test(path)) return jsonResponse({ message: '已同步 2 个广告账户' })
  if (/^\/platform-auth\/(meta|google)\/.*authorize_url/.test(path)) return jsonResponse({ authorize_url: '/platform-connections?mock_oauth=success' })
  if (/^\/platform-auth\/(meta|google)\/start_oauth$/.test(path)) return jsonResponse({ authorize_url: '/platform-connections?mock_oauth=success', connection_id: 'conn-demo' })
  if (/^\/platform-auth\/google\/[^/]+\/sub-accounts$/.test(path)) {
    if (method === 'POST') return jsonResponse({ id: `sub-${Date.now()}`, name: body.name, sub_account_id: body.sub_account_id, bm_customer_id: body.bm_customer_id, status: 'active', updated_at: now })
    return jsonResponse([{ id: 'sub-001', name: 'US Apps', sub_account_id: '652-310-9921', bm_customer_id: 'mgr-001', status: 'active', updated_at: now }, { id: 'sub-002', name: 'JP Drama', sub_account_id: '441-882-1760', bm_customer_id: 'mgr-001', status: 'active', updated_at: now }])
  }
  if (/^\/platform-auth\/connections\/[^/]+$/.test(path) && method === 'DELETE') return jsonResponse({ success: true })
  if (/^\/platform-auth\/meta\/[^/]+\/adaccounts\/[^/]+\/applications$/.test(path)) return jsonResponse([{ id: 'app-001', name: 'Candy Blast', supported_platforms: ['iOS', 'Android'], app_type: 'GAME' }])
  if (/^\/platform-auth\/meta\/[^/]+\/pages$/.test(path)) return jsonResponse([{ id: 'page-001', name: 'Candy Blast Official', category: 'App Page', tasks: ['ADVERTISE'], has_advertise_permission: true }])
  if (/^\/platform-auth\/meta\/[^/]+\/adaccounts\/[^/]+\/images$/.test(path)) return jsonResponse(materials.slice(0, 4).map(item => ({ id: item.id, name: item.name, hash: `hash-${item.id}`, url: item.url, url_128: item.thumbnail_url, width: item.width, height: item.height, status: 'ACTIVE', created_time: item.created_at })))
  if (/^\/platform-auth\/meta\/[^/]+\/adaccounts\/[^/]+\/videos$/.test(path)) return jsonResponse(materials.filter(item => item.media_kind === 'video').map(item => ({ id: item.id, title: item.name, length: item.duration, picture: item.thumbnail_url, source: item.url, status: 'READY', created_time: item.created_at })))

  if (path === '/organizations' && method === 'GET') return jsonResponse(organizations)
  if (path === '/organizations' && method === 'POST') return jsonResponse(createRecord(organizations, body, 'org', { owner_id: 'admin-001', status: 'active', member_count: 1, role: 'admin' }))
  if (path === '/organizations/join' && method === 'POST') return jsonResponse(organizations[0])
  if (/^\/organizations\/[^/]+\/invite-code$/.test(path)) return jsonResponse({ invite_code: 'ANIFORCE-2026', expires_at: '2026-12-31T23:59:59Z' })
  if (/^\/organizations\/[^/]+\/members$/.test(path) && method === 'GET') return jsonResponse({ members, total: members.length, page: 1, page_size: 20, total_pages: 1 })
  if (/^\/organizations\/[^/]+\/members/.test(path)) return jsonResponse({ success: true })
  if (/^\/organizations\/[^/]+/.test(path) && method === 'DELETE') return jsonResponse({ success: true })

  if (path === '/contact' && method === 'GET') return jsonResponse([{ id: 'contact-001', name: 'Mia Chen', company: 'GameNova', contact: 'mia@gamenova.demo', message: '希望了解全球投放托管方案', source: 'website', status: 'new', created_at: now }])
  if (path === '/contact' && method === 'POST') return jsonResponse(createRecord([], body, 'contact', { source: 'website', status: 'new' }))
  if (path === '/user/name' && method === 'PUT') return jsonResponse({ data: { id: 'admin-001', email: 'admin@animagus.ai', name: body.name } })
  if (path === '/user/password' && method === 'PUT') return jsonResponse({ success: true })

  if (path === '/agent/health') return jsonResponse({ status: 'healthy', provider: 'mock', model: 'ANIFORCE Demo Agent' })
  if (path === '/agent/sessions' && method === 'GET') return jsonResponse(agentSessions)
  if (path === '/agent/sessions' && method === 'POST') return jsonResponse(createRecord(agentSessions, { ...body, session_id: `session-${Date.now()}`, messages: [] }, 'session', { title: body.title || '新对话', status: 'active' }))
  const agentSessionMatch = path.match(/^\/agent\/sessions\/([^/]+)$/)
  if (agentSessionMatch) {
    const index = agentSessions.findIndex(item => item.id === agentSessionMatch[1] || item.session_id === agentSessionMatch[1])
    if (method === 'GET') return jsonResponse(agentSessions[index] || agentSessions[0])
    if (method === 'DELETE') { if (index >= 0) agentSessions.splice(index, 1); return jsonResponse({ success: true }) }
    if (index >= 0 && method === 'PATCH') { agentSessions[index] = { ...agentSessions[index], ...body, updated_at: now }; return jsonResponse(agentSessions[index]) }
  }
  if (path === '/agent/runs' && method === 'POST') {
    lastAgentPrompt = body.prompt || ''
    return jsonResponse({ run_id: `run-${Date.now()}`, session_id: body.session_id, status: 'running' })
  }
  const runEventsMatch = path.match(/^\/agent\/runs\/([^/]+)\/events$/)
  if (runEventsMatch) return mockAgentEvents(runEventsMatch[1])
  if (/^\/agent\/runs\/[^/]+\/cancel$/.test(path)) return jsonResponse({ success: true })

  console.warn(`[Mock API] 未覆盖接口：${method} ${path}`)
  return jsonResponse({ success: true, data: null })
}

export function installMockApi(): void {
  const nativeFetch = window.fetch.bind(window)
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const rawUrl = typeof input === 'string' || input instanceof URL ? String(input) : input.url
    const url = new URL(rawUrl, window.location.origin)
    if (url.origin === window.location.origin && url.pathname.startsWith('/api/v1/')) {
      return handleMockRequest(url, init)
    }
    return nativeFetch(input, init)
  }
}
