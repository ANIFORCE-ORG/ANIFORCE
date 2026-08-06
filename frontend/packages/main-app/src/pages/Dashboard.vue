<script setup lang="ts">
import { onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()
const activeSession = ref('sess-g001')
const period = ref('7')
const platform = ref('全部平台')
const project = ref('全部项目')
const updatedText = ref('2026/8/4 22:23:48')
const refreshing = ref(false)
const toastMessage = ref('')
const toastVisible = ref(false)
let toastTimer: number | undefined
let refreshTimer: number | undefined

const sessions = ref([
  { id: 'sess-g001', name: 'Candy Blast 投放咨询', active: true },
  { id: 'sess-g002', name: '素材优化建议', active: false },
  { id: 'sess-g003', name: '东南亚市场测试', active: false },
  { id: 'sess-d001', name: 'DramaBox 新剧推广', active: false },
])

const kpis = [
  { label: '总消耗', value: '$28,460', delta: '+12.4%', icon: 'account_balance_wallet' },
  { label: '转化数', value: '4,832', delta: '+8.7%', icon: 'download' },
  { label: 'CPI', value: '$5.89', delta: '−6.2%', icon: 'attach_money' },
  { label: 'ROAS', value: '2.42x', delta: '+0.18x', icon: 'trending_up' },
  { label: 'CTR', value: '4.0%', delta: '+0.7%', icon: 'ads_click' },
  { label: 'CVR', value: '9.1%', delta: '需关注', icon: 'target', warning: true },
]

const funnel = [
  { label: '曝光', value: '1,240,000', rate: '100%', width: 100 },
  { label: '点击', value: '68,420', rate: '5.5%', width: 58 },
  { label: '安装', value: '14,834', rate: '21.7%', width: 36 },
  { label: '注册', value: '8,420', rate: '56.8%', width: 25 },
  { label: '付费', value: '1,128', rate: '13.4%', width: 15 },
]

const segments = [
  { name: 'US / iOS / Broad', detail: '可控量 · CPI $5.62 · ROAS 2.82x' },
  { name: 'US / Android / LAL 2%', detail: '观察 · CPI $6.12 · ROAS 2.41x' },
  { name: 'US / Android / Spark', detail: '加预算 · CPI $5.25 · ROAS 3.04x' },
  { name: 'US / Search / Core', detail: '稳定 · CPI $5.95 · ROAS 2.22x' },
  { name: 'US / PMax / Creative', detail: '降预算 · CPI $8.97 · ROAS 1.86x' },
  { name: 'CA / Drama Fans', detail: '继续测 · CPI $6.31 · ROAS 2.06x' },
]

const platforms = [
  {
    name: 'Meta', account: 'Candy Blast Meta UA', campaigns: 5, score: 68, className: '',
    spend: '$12,840', conversions: '2,180', cpi: '$5.89', roas: '2.31x',
    daily: [
      ['05-21', '$1,284', '205', '2.13x'], ['05-22', '$1,412', '228', '2.19x'],
      ['05-23', '$1,541', '251', '2.26x'], ['05-24', '$1,798', '293', '2.33x'],
      ['05-25', '$1,926', '326', '2.40x'], ['05-26', '$2,311', '398', '2.47x'],
      ['05-27', '$2,568', '479', '2.54x'],
    ],
  },
  {
    name: 'Google', account: 'DramaBox Google Ads', campaigns: 3, score: 54, className: 'google',
    spend: '$8,620', conversions: '1,426', cpi: '$6.04', roas: '2.12x',
    daily: [
      ['05-21', '$1,552', '257', '2.37x'], ['05-22', '$1,465', '242', '2.29x'],
      ['05-23', '$1,379', '228', '2.20x'], ['05-24', '$1,293', '214', '2.12x'],
      ['05-25', '$1,121', '185', '2.06x'], ['05-26', '$948', '157', '1.99x'],
      ['05-27', '$862', '143', '1.93x'],
    ],
    insight: '05-26 · PMax 素材资产转化效率偏低。', insightValue: 'ROAS 1.94x',
  },
  {
    name: 'TikTok', account: 'Candy Blast TikTok US', campaigns: 4, score: 78, className: 'tiktok',
    spend: '$7,000', conversions: '1,226', cpi: '$5.71', roas: '2.86x',
    daily: [
      ['05-21', '$700', '121', '2.63x'], ['05-22', '$770', '135', '2.72x'],
      ['05-23', '$840', '147', '2.80x'], ['05-24', '$980', '171', '2.89x'],
      ['05-25', '$1,050', '184', '2.97x'], ['05-26', '$1,260', '220', '3.08x'],
      ['05-27', '$1,400', '248', '3.15x'],
    ],
  },
]

const showToast = (message: string) => {
  window.clearTimeout(toastTimer)
  toastMessage.value = message
  toastVisible.value = true
  toastTimer = window.setTimeout(() => { toastVisible.value = false }, 2000)
}

const switchPanel = (item: any) => item.path && router.push(item.path)

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(item => { item.active = item.id === session.id })
}

const changePeriod = () => {
  updatedText.value = '统计范围已更新'
  showToast(`统计周期已切换为最近 ${period.value} 天`)
}

const changePlatform = () => {
  updatedText.value = '平台范围已更新'
  showToast(`平台筛选：${platform.value}`)
}

const changeProject = () => {
  updatedText.value = '项目范围已更新'
  showToast(`项目筛选：${project.value}`)
}

const handleRefresh = () => {
  window.clearTimeout(refreshTimer)
  refreshing.value = false
  requestAnimationFrame(() => { refreshing.value = true })
  updatedText.value = '刚刚更新'
  showToast('数据已刷新')
  refreshTimer = window.setTimeout(() => { refreshing.value = false }, 700)
}

onBeforeUnmount(() => {
  window.clearTimeout(toastTimer)
  window.clearTimeout(refreshTimer)
})
</script>

<template>
  <div class="dashboard-shell">
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="workspace replay-page">
      <header class="page-bar replay-bar">
        <div class="page-title replay-title">
          <span class="page-icon material-symbols-outlined" aria-hidden="true">bar_chart</span>
          <div>
            <h1>数据复盘</h1>
            <p>跨平台投放表现、Campaign 预算消耗和素材信号</p>
          </div>
        </div>
        <div class="page-actions replay-actions">
          <label class="filter-field">时间范围
            <select v-model="period" class="period-select" aria-label="时间范围" @change="changePeriod">
              <option value="7">最近 7 天</option><option value="30">最近 30 天</option><option value="90">最近 90 天</option>
            </select>
          </label>
          <label class="filter-field">平台
            <select v-model="platform" class="period-select" aria-label="平台" @change="changePlatform">
              <option>全部平台</option><option>Meta</option><option>Google</option><option>TikTok</option>
            </select>
          </label>
          <label class="filter-field">项目
            <select v-model="project" class="period-select" aria-label="项目" @change="changeProject">
              <option>全部项目</option><option>CANDY BLASTER</option><option>DramaBox</option>
            </select>
          </label>
          <button class="refresh-button" :class="{ refreshing }" type="button" @click="handleRefresh">
            <span class="icon material-symbols-outlined" aria-hidden="true">refresh</span>刷新
          </button>
        </div>
      </header>

      <div class="content replay-content">
        <section class="data-note">
          <div><strong>数据源：ANIFORCE Demo 数据集</strong><span>更新时间：{{ updatedText }}</span></div>
          <span class="quiet-badge">Report / Monitor</span>
        </section>

        <section class="replay-kpis" aria-label="核心指标">
          <article v-for="kpi in kpis" :key="kpi.label" class="replay-kpi">
            <div class="kpi-head"><span>{{ kpi.label }}</span><span class="icon material-symbols-outlined" aria-hidden="true">{{ kpi.icon }}</span></div>
            <div class="kpi-value">{{ kpi.value }}</div>
            <span class="kpi-delta" :class="{ warn: kpi.warning }">{{ kpi.delta }}</span>
          </article>
        </section>

        <section class="replay-card">
          <div class="replay-card-head"><div><h2>趋势监控</h2><p>消耗、转化与 ROAS 随时间变化</p></div><span class="soft-chip">近 7 天</span></div>
          <div class="trend-grid">
            <div class="chart-panel">
              <div class="chart-legend"><span class="legend-item"><i class="legend-dot spend"></i>消耗</span><span class="legend-item"><i class="legend-dot conversions"></i>转化</span><span class="legend-item"><i class="legend-dot roas"></i>ROAS</span></div>
              <svg viewBox="60 24 830 162" preserveAspectRatio="none" role="img" aria-label="近七天消耗、转化和 ROAS 趋势图">
                <g stroke="#ecebea" stroke-width="1"><path d="M52 32H892M52 73H892M52 114H892M52 155H892" /></g>
                <g fill="#20a464" opacity=".8"><rect x="80" y="116" width="22" height="39" rx="3" /><rect x="208" y="106" width="22" height="49" rx="3" /><rect x="336" y="99" width="22" height="56" rx="3" /><rect x="464" y="91" width="22" height="64" rx="3" /><rect x="592" y="78" width="22" height="77" rx="3" /><rect x="720" y="64" width="22" height="91" rx="3" /><rect x="848" y="50" width="22" height="105" rx="3" /></g>
                <path d="M91 106L219 98L347 90L475 82L603 73L731 57L859 48" fill="none" stroke="#4f8fe8" stroke-width="2.2" />
                <path d="M91 138L219 121L347 104L475 116L603 83L731 66L859 57" fill="none" stroke="#dd7d00" stroke-width="2" />
                <g fill="#4f8fe8" stroke="#fff" stroke-width="1.5"><circle cx="91" cy="106" r="3" /><circle cx="219" cy="98" r="3" /><circle cx="347" cy="90" r="3" /><circle cx="475" cy="82" r="3" /><circle cx="603" cy="73" r="3" /><circle cx="731" cy="57" r="3" /><circle cx="859" cy="48" r="3" /></g>
                <g fill="#dd7d00" stroke="#fff" stroke-width="1.5"><circle cx="91" cy="138" r="3" /><circle cx="219" cy="121" r="3" /><circle cx="347" cy="104" r="3" /><circle cx="475" cy="116" r="3" /><circle cx="603" cy="83" r="3" /><circle cx="731" cy="66" r="3" /><circle cx="859" cy="57" r="3" /></g>
                <g fill="#a4a097" font-size="8" text-anchor="middle"><text x="91" y="177">05-21</text><text x="219" y="177">05-22</text><text x="347" y="177">05-23</text><text x="475" y="177">05-24</text><text x="603" y="177">05-25</text><text x="731" y="177">05-26</text><text x="859" y="177">05-27</text></g>
              </svg>
            </div>
            <aside class="chart-summary">
              <div class="summary-box"><span>筛选消耗</span><strong>$24,220</strong><small>来自当前 Campaign 筛选集合</small></div>
              <div class="summary-box"><span>转化</span><strong>4,832</strong><small>安装 / 注册 / 购买合计</small></div>
              <div class="summary-box"><span>平均 ROAS</span><strong>2.42x</strong><small>按商品总价值计算</small></div>
            </aside>
          </div>
        </section>

        <div class="replay-split">
          <section class="replay-card">
            <div class="replay-card-head"><div><h2>漏斗下钻</h2><p>曝光到付费的转化路径</p></div><span class="soft-chip">Funnel</span></div>
            <div class="compact-body funnel-list">
              <div v-for="item in funnel" :key="item.label" class="funnel-row"><strong>{{ item.label }}</strong><span class="funnel-track"><i :style="{ width: `${item.width}%` }"></i></span><strong>{{ item.value }}</strong><small>{{ item.rate }}</small></div>
            </div>
          </section>
          <section class="replay-card">
            <div class="replay-card-head"><div><h2>分群表现</h2><p>国家 / 系统 / 受众 / 版位效率对比</p></div><span class="soft-chip">Segment</span></div>
            <div class="compact-body segment-grid">
              <div v-for="segment in segments" :key="segment.name" class="segment-row">
                <div><strong>{{ segment.name }}</strong><small>{{ segment.detail }}</small></div>
                <button class="quiet-badge" type="button" @click="showToast(`已展开 ${segment.name}`)">展开</button>
              </div>
            </div>
          </section>
        </div>

        <section class="replay-card">
          <div class="replay-card-head"><div><h2>平台表现</h2><p>平台账户、Campaign 数量、消耗、转化与回报</p></div><span class="soft-chip">Platform Account</span></div>
          <div class="platform-grid">
            <article v-for="item in platforms" :key="item.name" class="platform-card" :class="item.className" :style="`--score:${item.score}`">
              <div class="platform-top">
                <div class="platform-heading"><div><h3>{{ item.name }}</h3><p>{{ item.account }} · {{ item.campaigns }} Campaign</p></div><span class="soft-chip">收起</span></div>
                <div class="platform-health"><div class="gauge"><strong>{{ item.score }}</strong></div><div class="health-copy">平台健康度 {{ item.score }}%<div class="health-bar"><i></i></div></div></div>
                <div class="platform-metrics">
                  <div class="platform-metric"><span>Spend</span><strong>{{ item.spend }}</strong></div><div class="platform-metric"><span>转化</span><strong>{{ item.conversions }}</strong></div><div class="platform-metric"><span>CPI</span><strong>{{ item.cpi }}</strong></div><div class="platform-metric"><span>ROAS</span><strong>{{ item.roas }}</strong></div>
                </div>
              </div>
              <div class="daily-table" role="table" :aria-label="`${item.name} 分天表现`">
                <div class="daily-table-head" role="row"><span>日期</span><span>消耗</span><span>转化</span><span>ROAS</span></div>
                <div v-for="row in item.daily" :key="row[0]" class="daily-table-row" role="row"><span>{{ row[0] }}</span><strong>{{ row[1] }}</strong><span>{{ row[2] }}</span><span class="daily-roas">{{ row[3] }}</span></div>
              </div>
              <div v-if="item.insight" class="platform-insight"><span>{{ item.insight }}</span><span class="soft-chip">{{ item.insightValue }}</span></div>
            </article>
          </div>
        </section>
      </div>
    </main>

    <div class="toast" :class="{ show: toastVisible }" role="status" aria-live="polite">{{ toastMessage }}</div>
  </div>
</template>

<style scoped>
.dashboard-shell {
  height: calc(100vh - 100px);
  width: 100%;
  display: flex;
  overflow: hidden;
  background: #fff;
}

.replay-page {
  --canvas: #fff;
  --surface: #f6f5f4;
  --surface-soft: #fafaf9;
  --hairline: #e5e3df;
  --hairline-soft: #ede9e4;
  --hairline-strong: #c8c4be;
  --ink: #1a1a1a;
  --charcoal: #37352f;
  --slate: #5d5b54;
  --steel: #787671;
  --stone: #a4a097;
  --green-soft: #d9f3e1;
  min-width: 0;
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-color: var(--hairline-strong) transparent;
  scrollbar-width: thin;
  background: var(--canvas);
  color: var(--charcoal);
}

.page-bar { min-height: 54px; display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 0 clamp(24px,3vw,48px); border-bottom: 1px solid var(--hairline); background: rgba(255,255,255,.86); }
.page-title { display: flex; align-items: center; gap: 8px; }
.page-title .page-icon { width: 26px; height: 26px; display: grid; place-items: center; border-radius: 6px; }
.page-title h1 { margin: 0; color: var(--ink); font-size: 16px; font-weight: 600; letter-spacing: -.2px; }
.page-actions { display: flex; align-items: center; gap: 7px; }
.period-select { height: 31px; min-width: 112px; padding: 0 29px 0 10px; border: 1px solid var(--hairline-strong); border-radius: 7px; outline: none; background: #fff; color: var(--slate); font-size: 11px; cursor: pointer; }
.content { width: min(100%,1220px); margin: 0 auto; padding: 30px clamp(24px,3vw,48px) 74px; }

.replay-bar {
  min-height: 64px;
  align-items: center;
  padding-inline: max(24px, calc((100% - 1080px) / 2 + 18px));
}
.replay-title { align-items: flex-start; }
.replay-title .page-icon { width: 22px; height: 22px; margin-top: 1px; background: transparent; color: var(--slate); font-size: 16px; }
.replay-title h1 { font-size: 17px; }
.replay-title p { margin: 2px 0 0; color: var(--steel); font-size: 10px; }
.replay-actions { gap: 8px; }
.filter-field { display: grid; gap: 3px; color: var(--stone); font-size: 8px; font-weight: 600; }
.filter-field .period-select { min-width: 92px; }
.refresh-button { height: 31px; min-width: 116px; align-self: end; display: inline-flex; align-items: center; justify-content: center; gap: 6px; padding: 0 12px; border: 1px solid var(--hairline-strong); border-radius: 7px; background: #fff; color: var(--charcoal); font-size: 10px; font-weight: 600; cursor: pointer; }
.refresh-button .icon { font-size: 15px; }
.refreshing .icon { animation: spin .65s ease; }
@keyframes spin { to { transform: rotate(360deg); } }

.replay-content {
  width: 100%;
  max-width: 1080px;
  margin-inline: auto;
  padding: 14px 18px 54px;
}
.data-note { min-height: 42px; display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 8px 12px; border: 1px solid var(--hairline); border-radius: 8px; background: var(--surface-soft); color: var(--slate); font-size: 9px; }
.data-note strong { display: block; margin-bottom: 1px; color: var(--charcoal); }
.quiet-badge { display: inline-flex; align-items: center; min-height: 22px; padding: 2px 8px; border: 1px solid var(--hairline); border-radius: 999px; background: #fff; color: var(--steel); font-size: 8px; font-weight: 600; white-space: nowrap; }
button.quiet-badge { cursor: pointer; font-family: inherit; }

.replay-kpis { display: grid; grid-template-columns: repeat(6,minmax(0,1fr)); gap: 0; margin-top: 12px; border: 1px solid var(--hairline); border-radius: 10px; overflow: hidden; background: #fff; }
.replay-kpi { position: relative; min-width: 0; padding: 12px 16px; border: 0; border-radius: 0; background: #fff; }
.replay-kpi:not(:last-child)::after { content: ""; position: absolute; top: 20%; right: 0; bottom: 20%; width: 1px; background: #f0efed; }
.kpi-head { display: flex; align-items: center; justify-content: space-between; gap: 6px; color: var(--steel); font-size: 9px; font-weight: 600; }
.kpi-head .icon { color: var(--steel); font-size: 14px; font-weight: 400; }
.kpi-value { margin-top: 7px; color: var(--ink); font-size: 18px; line-height: 1.1; font-weight: 650; letter-spacing: -.35px; }
.kpi-delta { width: fit-content; display: inline-flex; align-items: center; margin-top: 7px; padding: 2px 6px; border-radius: 4px; background: #edf8f0; color: #16804a; font-size: 8px; font-weight: 600; }
.kpi-delta.warn { background: #fff6e4; color: #9a6700; }

.replay-card { margin-top: 12px; border: 1px solid var(--hairline); border-radius: 10px; background: #fff; overflow: hidden; }
.replay-card-head { min-height: 42px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 7px 12px; border-bottom: 1px solid var(--hairline-soft); }
.replay-card-head h2 { margin: 0; color: var(--ink); font-size: 13px; font-weight: 600; }
.replay-card-head p { margin: 2px 0 0; color: var(--steel); font-size: 9px; }
.soft-chip { display: inline-flex; align-items: center; min-height: 22px; padding: 2px 8px; border-radius: 5px; background: var(--surface); color: var(--slate); font-size: 8px; font-weight: 600; }

.trend-grid { display: grid; grid-template-columns: minmax(0,1fr) 180px; align-items: start; gap: 8px; padding: 8px; }
.chart-panel { min-width: 0; height: 212px; min-height: 0; padding: 7px 2px 0; overflow: hidden; border: 1px solid var(--hairline-soft); border-radius: 8px; background: #fcfcfb; }
.chart-legend { display: flex; align-items: center; gap: 12px; padding-left: 6px; color: var(--steel); font-size: 8px; }
.legend-item { display: inline-flex; align-items: center; gap: 4px; }
.legend-dot { width: 6px; height: 6px; border-radius: 50%; }
.legend-dot.spend { background: #4f8fe8; }.legend-dot.conversions { background: #20a464; }.legend-dot.roas { background: #dd7d00; }
.chart-panel svg { display: block; width: 100%; height: 180px; margin-top: -2px; overflow: visible; }
.chart-summary { height: 212px; display: grid; grid-template-rows: repeat(3,1fr); gap: 0; border: 1px solid var(--hairline); border-radius: 8px; overflow: hidden; background: #fff; }
.summary-box { min-height: 0; padding: 10px 12px; border-bottom: 1px solid #f0efed; }
.summary-box:last-child { border-bottom: 0; }
.summary-box span { color: var(--steel); font-size: 8px; }
.summary-box strong { display: block; margin: 3px 0 1px; color: var(--ink); font-size: 15px; line-height: 1.1; }
.summary-box small { color: var(--steel); font-size: 8px; }

.replay-split { display: grid; grid-template-columns: .86fr 1.14fr; align-items: start; gap: 12px; }
.replay-split > .replay-card { align-self: start; }
.compact-body { padding: 10px 12px 12px; }
.funnel-list { display: grid; gap: 11px; }
.funnel-row { display: grid; grid-template-columns: 42px minmax(0,1fr) 58px 38px; align-items: center; gap: 8px; font-size: 9px; }
.funnel-track { height: 6px; border-radius: 999px; background: #efefed; overflow: hidden; }
.funnel-track i { display: block; height: 100%; border-radius: inherit; background: #4f8fe8; }
.funnel-row strong { font-size: 9px; }.funnel-row small { color: var(--steel); font-size: 8px; }
.segment-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 7px; }
.segment-row { min-height: 46px; display: grid; grid-template-columns: minmax(0,1fr) auto; align-items: center; gap: 8px; padding: 8px 9px; border: 1px solid var(--hairline-soft); border-radius: 7px; }
.segment-row strong { display: block; color: var(--ink); font-size: 9px; }.segment-row small { display: block; margin-top: 2px; color: var(--steel); font-size: 8px; }

.platform-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); align-items: start; gap: 8px; padding: 10px; }
.platform-card { --accent: #4f8fe8; min-width: 0; align-self: start; border: 1px solid var(--hairline); border-radius: 9px; overflow: hidden; background: #fff; }
.platform-card.google { --accent: #dd7d00; }.platform-card.tiktok { --accent: #16a05d; }
.platform-top { padding: 10px; }
.platform-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.platform-heading h3 { margin: 0; color: var(--ink); font-size: 11px; }.platform-heading p { margin: 2px 0 0; color: var(--steel); font-size: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.platform-health { display: grid; grid-template-columns: 50px 1fr; align-items: center; gap: 9px; margin-top: 9px; }
.gauge { width: 46px; height: 46px; border-radius: 50%; display: grid; place-items: center; background: conic-gradient(var(--accent) calc(var(--score)*1%),var(--hairline) 0); position: relative; }
.gauge::after { content: ""; position: absolute; inset: 6px; border-radius: 50%; background: #fff; }.gauge strong { position: relative; z-index: 1; font-size: 10px; }
.health-copy { min-width: 0; color: var(--steel); font-size: 8px; }.health-bar { height: 5px; margin-top: 6px; border-radius: 999px; background: var(--hairline-soft); overflow: hidden; }.health-bar i { display: block; width: calc(var(--score)*1%); height: 100%; border-radius: inherit; background: var(--accent); }
.platform-metrics { display: grid; grid-template-columns: repeat(4,1fr); gap: 0; margin-top: 9px; border: 1px solid var(--hairline-soft); border-radius: 6px; overflow: hidden; background: var(--surface-soft); }
.platform-metric { position: relative; padding: 7px 8px; }.platform-metric:not(:last-child)::after { content: ""; position: absolute; top: 22%; right: 0; bottom: 22%; width: 1px; background: #f0efed; }
.platform-metric span { display: block; color: var(--steel); font-size: 7px; }.platform-metric strong { display: block; margin-top: 2px; color: var(--ink); font-size: 9px; }
.platform-insight { margin: 0 8px 8px; padding: 7px 8px; display: flex; align-items: center; justify-content: space-between; gap: 8px; border-radius: 6px; background: var(--surface-soft); color: var(--slate); font-size: 8px; }
.daily-table { margin: 0 8px 8px; overflow: hidden; border: 1px solid var(--hairline-soft); border-radius: 7px; background: #fff; }
.daily-table-head,.daily-table-row { display: grid; grid-template-columns: .8fr 1.15fr .9fr .8fr; align-items: center; gap: 8px; min-height: 30px; padding: 0 10px; }
.daily-table-head { min-height: 28px; background: var(--surface-soft); color: var(--steel); font-size: 7px; font-weight: 600; }.daily-table-row { border-top: 1px solid #f1f0ee; color: var(--slate); font-size: 8px; }.daily-table-row:hover { background: #fafaf9; }.daily-table-row strong { color: var(--ink); font-size: 9px; font-weight: 600; }
.daily-roas { display: inline-flex; align-items: center; gap: 5px; color: var(--ink); font-weight: 600; }.daily-roas::before { content: ""; width: 5px; height: 5px; border-radius: 50%; background: var(--accent); }

.toast { position: fixed; z-index: 90; left: 50%; bottom: 52px; max-width: calc(100vw - 32px); padding: 10px 13px; border: 1px solid var(--hairline,#e5e3df); border-radius: 8px; background: #fff; color: #37352f; font-size: 12px; box-shadow: rgba(15,15,15,.16) 0 16px 44px -10px; opacity: 0; pointer-events: none; transform: translate(-50%,8px); transition: opacity .16s ease,transform .16s ease; }
.toast.show { opacity: 1; transform: translate(-50%,0); }

@media (max-width: 1220px) {
  .replay-kpis { grid-template-columns: repeat(3,1fr); }.replay-kpi:nth-child(3)::after,.replay-kpi:nth-child(6)::after { display: none; }.replay-kpi:nth-child(-n+3) { border-bottom: 1px solid #f3f2f0; }
  .platform-grid { grid-template-columns: 1fr; }.platform-card { display: grid; grid-template-columns: 310px minmax(0,1fr); align-items: start; }.platform-card .platform-top { border-right: 1px solid var(--hairline-soft); }.platform-card .daily-table { margin: 8px; }.platform-card .platform-insight { grid-column: 1/-1; }
}
@media (max-width: 900px) {
  .replay-bar { align-items: flex-start; flex-direction: column; padding-top: 10px; padding-bottom: 10px; }.replay-actions { width: 100%; overflow-x: auto; padding-bottom: 2px; }
  .trend-grid,.replay-split { grid-template-columns: 1fr; }.chart-summary { width: 100%; height: auto; grid-template-columns: repeat(3,1fr); grid-template-rows: 1fr; }.summary-box { border-right: 1px solid var(--hairline-soft); border-bottom: 0; }.summary-box:last-child { border-right: 0; }
  .platform-card { display: block; }.platform-card .platform-top { border-right: 0; }
}
@media (max-width: 620px) {
  .replay-content { padding: 12px 12px 52px; }.replay-kpis { grid-template-columns: repeat(2,1fr); }.replay-kpi { border-bottom: 1px solid #f3f2f0; }.replay-kpi:nth-child(3)::after { display: block; }.replay-kpi:nth-child(2n)::after { display: none; }.replay-kpi:nth-last-child(-n+2) { border-bottom: 0; }
  .segment-grid { grid-template-columns: 1fr; }.chart-summary { grid-template-columns: 1fr; }.summary-box { border-right: 0; border-bottom: 1px solid var(--hairline-soft); }.summary-box:last-child { border-bottom: 0; }.funnel-row { grid-template-columns: 36px minmax(0,1fr) 48px; }.funnel-row small { display: none; }.data-note { align-items: flex-start; flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) { *,*::before,*::after { transition-duration: .01ms !important; animation-duration: .01ms !important; } }
</style>
