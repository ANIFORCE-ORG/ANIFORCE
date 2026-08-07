<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import AdUnitCardDetailed from '@/components/campaigns/AdUnitCardDetailed.vue'
import CreateAdUnitModal from '@/components/campaigns/CreateAdUnitModal.vue'
import { getCampaignDetail, getCampaignMaterials, type Campaign } from '@/api/campaigns'
import { getMaterialImage } from '@/api/materials'
import { navItems } from '@/config/navigation'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const campaignId = ref(route.params.id as string)
const activeSession = ref('sess_g001')
const chatInput = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

const campaign = ref<Campaign | null>(null)
const adUnits = ref<any[]>([])
const showCreateAdUnitModal = ref(false)
const createAdUnitModalRef = ref<any>(null)

const sessions = ref([
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场测试', active: false },
  { id: 'sess_d001', name: 'DramaBox新剧推广', active: false }
])

const messages = ref([
  {
    role: 'assistant',
    author: 'ANIFORCE助手',
    time: '刚刚',
    content: `您好${auth.user?.name || '李明'}！我是ANIFORCE智能助手。\n\n我可以帮您：\n• 分析素材表现\n• 优化投放策略\n• 素材创意建议\n• 预算调整建议\n\n请告诉我您需要什么帮助？`
  }
])

const quickHints = [
  '分析素材表现',
  '优化建议',
  '创意素材推荐',
  '预算调整',
  '添加新素材',
  '数据报表'
]

onMounted(async () => {
  await loadCampaignData()
})

const loadCampaignData = async () => {
  loading.value = true
  error.value = null

  try {
    console.log('加载广告投放详情:', campaignId.value)

    // 加载广告投放详情
    const campaignData = await getCampaignDetail(campaignId.value)
    campaign.value = campaignData
    console.log('广告投放详情加载成功:', campaignData)

    // TODO: 加载关联的 Ad Units
    // const adUnitsData = await getAdUnits(campaignId.value)
    // adUnits.value = adUnitsData

    // 临时模拟数据
    adUnits.value = []
    console.log('Ad Units 加载成功:', adUnits.value.length, '条')
  } catch (err: any) {
    error.value = err.message || '加载数据失败'
    console.error('加载数据失败:', err)
  } finally {
    loading.value = false
  }
}


const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const switchSession = (session: any) => {
  activeSession.value = session.id
  sessions.value.forEach(s => s.active = s.id === session.id)
}

const handleSendMessage = (message: string) => {
  console.log('发送消息:', message)
  chatInput.value = ''
}

const handleHintClick = (hint: string) => {
  chatInput.value = hint
}

const handleBack = () => {
  // 使用router.back()返回上一页，智能返回到来源页面
  router.back()
}

const handleAddAdUnit = () => {
  showCreateAdUnitModal.value = true
}

const handleCloseAdUnitModal = () => {
  showCreateAdUnitModal.value = false
}

const handleSubmitAdUnit = async (data: any) => {
  try {
    // TODO: 调用 API 创建 Ad Unit
    console.log('创建 Ad Unit:', data)

    // 模拟 API 调用
    await new Promise(resolve => setTimeout(resolve, 1000))

    // 成功后关闭弹窗并刷新列表
    showCreateAdUnitModal.value = false
    if (createAdUnitModalRef.value) {
      createAdUnitModalRef.value.resetForm()
    }

    // TODO: 刷新 Ad Units 列表
    console.log('Ad Unit 创建成功')
  } catch (err: any) {
    console.error('创建 Ad Unit 失败:', err)
  } finally {
    if (createAdUnitModalRef.value) {
      createAdUnitModalRef.value.setSubmitting(false)
    }
  }
}

const handleViewAdUnit = (adUnitId: string) => {
  console.log('查看 Ad Unit 详情:', adUnitId)
  // TODO: 跳转到 Ad Unit 详情页面
}

const handleEditAdUnit = (adUnit: any) => {
  console.log('编辑 Ad Unit:', adUnit)
  // TODO: 打开编辑 Ad Unit 的弹窗或页面
}

const getPlatformColor = (platform: string) => {
  const colors: Record<string, string> = {
    'Google': 'text-blue-600',
    'TikTok': 'text-slate-900 dark:text-white',
    'Meta': 'text-blue-500'
  }
  return colors[platform] || 'text-slate-600'
}

// 格式化日期
const formatDate = (dateString?: string) => {
  if (!dateString) return '-'
  try {
    const date = new Date(dateString)
    return date.toISOString().slice(0, 10)
  } catch {
    return dateString
  }
}
</script>

<template>
  <div class="campaign-detail-notion">
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      active-panel="campaigns"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="campaign-workspace">
      <header class="campaign-page-bar">
        <button class="campaign-back" type="button" @click="handleBack">
          <span class="material-symbols-outlined">arrow_back</span>
          返回广告列表
        </button>
      </header>

      <div class="campaign-content">
        <section class="campaign-panel" aria-labelledby="campaign-page-title">
          <div class="campaign-head">
            <h1 id="campaign-page-title">{{ campaign?.name || '-' }}</h1>
            <span class="campaign-divider"></span>
            <div class="campaign-heading-copy">
              <h2>Campaign 信息</h2>
              <p>所属项目：{{ campaign?.project_name || '暂无' }}</p>
            </div>
          </div>

          <dl class="campaign-properties">
            <div class="campaign-property"><dt>平台</dt><dd>{{ campaign?.platform || '-' }}</dd></div>
            <div class="campaign-property"><dt>广告账户</dt><dd :title="campaign?.account_id || '-'">{{ campaign?.account_id || '-' }}</dd></div>
            <div class="campaign-property"><dt>预算优化</dt><dd>{{ campaign?.campaign_budget_optimization || '-' }}</dd></div>
            <div class="campaign-property"><dt>预算</dt><dd>${{ campaign?.budget?.toLocaleString() || '0' }}</dd></div>
            <div class="campaign-property"><dt>Buying Type</dt><dd>{{ campaign?.buying_type || '-' }}</dd></div>
            <div class="campaign-property"><dt>开始 / 结束</dt><dd>{{ formatDate(campaign?.start_date) }} / {{ formatDate(campaign?.end_date) }}</dd></div>
            <div class="campaign-property"><dt>状态</dt><dd><span class="status-chip" :data-status="campaign?.status || 'draft'">{{ campaign?.status || '-' }}</span></dd></div>
          </dl>
        </section>

        <section aria-labelledby="adset-title">
          <div class="campaign-section-head">
            <h2 id="adset-title">广告单元 Ad Sets ({{ adUnits.length }})</h2>
            <button class="campaign-action" type="button" @click="handleAddAdUnit">
              <span class="material-symbols-outlined">add</span><span>创建新广告单元</span>
            </button>
          </div>

          <div v-if="adUnits.length" class="adunit-list">
            <AdUnitCardDetailed
              v-for="adUnit in adUnits"
              :key="adUnit.id"
              :ad-unit="adUnit"
              @view="handleViewAdUnit"
              @edit="handleEditAdUnit"
            />
          </div>

          <div v-else class="campaign-empty-state">
            <div class="campaign-empty-inner">
              <div class="campaign-empty-icon"><span class="material-symbols-outlined">campaign</span></div>
              <h3>暂无广告单元</h3>
              <p>广告单元用于设置受众、预算、排期和版位。创建后即可继续添加广告素材。</p>
              <button class="campaign-action" type="button" @click="handleAddAdUnit">
                <span class="material-symbols-outlined">add</span>创建首个广告单元
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>

    <ChatPanel
      :session-id="activeSession"
      :quick-hints="quickHints"
      initial-collapsed
      compact-collapsed
    />

    <CreateAdUnitModal
      ref="createAdUnitModalRef"
      :show="showCreateAdUnitModal"
      :campaign-id="campaignId"
      :campaign-buying-type="campaign?.buying_type"
      :campaign-objective="campaign?.objective"
      :campaign-budget-optimization="campaign?.campaign_budget_optimization"
      @close="handleCloseAdUnitModal"
      @submit="handleSubmitAdUnit"
    />
  </div>
</template>

<style scoped>
.campaign-detail-notion {
  --c-surface: #f6f5f4;
  --c-surface-soft: #fafaf9;
  --c-line: #e5e3df;
  --c-line-soft: #ede9e4;
  --c-line-strong: #c8c4be;
  --c-ink: #1a1a1a;
  --c-charcoal: #37352f;
  --c-slate: #5d5b54;
  --c-steel: #787671;
  --c-stone: #a4a097;
  width: 100%;
  height: calc(100vh - 100px);
  display: flex;
  overflow: hidden;
  background: #fff;
  color: var(--c-charcoal);
  font-family: "Notion Sans", "Avenir Next", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
.campaign-workspace { min-width: 0; flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #fff; }
.campaign-page-bar { min-height: 54px; flex: 0 0 auto; display: flex; align-items: center; padding: 0 clamp(24px,3vw,48px); border-bottom: 1px solid var(--c-line); background: rgba(255,255,255,.88); }
.campaign-back { min-height: 31px; display: inline-flex; align-items: center; gap: 7px; padding: 0 8px; border: 0; border-radius: 6px; background: transparent; color: var(--c-slate); font-size: 11px; font-weight: 500; cursor: pointer; }
.campaign-back:hover { background: var(--c-surface); color: var(--c-ink); }
.campaign-back .material-symbols-outlined { font-size: 16px; }
.campaign-content { width: min(100%,1240px); margin: 0 auto; padding: 24px clamp(24px,3vw,48px) 78px; overflow-y: auto; }
.campaign-panel { border: 1px solid var(--c-line); border-radius: 12px; background: #fff; overflow: hidden; }
.campaign-head { min-height: 54px; display: flex; align-items: center; gap: 12px; padding: 0 18px; border-bottom: 1px solid var(--c-line-soft); }
.campaign-head h1 { margin: 0; color: var(--c-ink); font-size: 17px; font-weight: 650; letter-spacing: -.35px; }
.campaign-divider { width: 1px; height: 16px; background: var(--c-line-strong); }
.campaign-heading-copy { min-width: 0; display: flex; align-items: baseline; gap: 9px; }
.campaign-heading-copy h2 { margin: 0; color: var(--c-charcoal); font-size: 12px; font-weight: 600; }
.campaign-heading-copy p { margin: 0; overflow: hidden; color: var(--c-steel); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.campaign-properties { display: grid; grid-template-columns: .7fr 1.35fr 1.25fr .65fr .8fr 1.25fr .75fr; margin: 0; padding: 0 18px; }
.campaign-property { min-width: 0; padding: 13px 14px 14px; border-right: 1px solid var(--c-line-soft); }
.campaign-property:first-child { padding-left: 0; }
.campaign-property:last-child { padding-right: 0; border-right: 0; }
.campaign-property dt { margin: 0; color: var(--c-steel); font-size: 9px; line-height: 1.3; }
.campaign-property dd { margin: 4px 0 0; overflow: hidden; color: var(--c-ink); font-size: 10px; font-weight: 600; line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }
.campaign-property .status-chip { min-height: 20px; padding: 2px 7px; border-radius: 6px; font-size: 8px; }
.campaign-section-head { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin: 28px 0 11px; }
.campaign-section-head h2 { margin: 0; color: var(--c-ink); font-size: 14px; font-weight: 600; }
.campaign-action { min-height: 34px; display: inline-flex; align-items: center; justify-content: center; gap: 7px; padding: 0 13px; border: 1px solid var(--c-charcoal); border-radius: 8px; background: var(--c-charcoal); color: #fff; font-size: 11px; font-weight: 500; cursor: pointer; }
.campaign-action:hover { border-color: var(--c-ink); background: var(--c-ink); }
.campaign-action .material-symbols-outlined { font-size: 16px; }
.adunit-list { display: grid; gap: 12px; }
.campaign-empty-state { min-height: 270px; display: grid; place-items: center; border-top: 1px solid var(--c-line-soft); }
.campaign-empty-inner { width: min(620px,100%); padding: 48px 18px; text-align: center; }
.campaign-empty-icon { width: 42px; height: 42px; display: grid; place-items: center; margin: 0 auto 14px; border: 1px solid var(--c-line); border-radius: 10px; background: var(--c-surface-soft); color: var(--c-stone); }
.campaign-empty-icon .material-symbols-outlined { font-size: 21px; }
.campaign-empty-state h3 { margin: 0; color: var(--c-charcoal); font-size: 13px; font-weight: 600; }
.campaign-empty-state p { margin: 7px auto 17px; overflow: hidden; color: var(--c-steel); font-size: 10px; line-height: 1.55; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 1000px) {
  .campaign-properties { grid-template-columns: repeat(4,minmax(0,1fr)); }
  .campaign-property { border-bottom: 1px solid var(--c-line-soft); }
  .campaign-property:nth-child(4n) { border-right: 0; }
}
@media (max-width: 760px) {
  .campaign-properties { grid-template-columns: repeat(2,minmax(0,1fr)); }
  .campaign-property:nth-child(odd) { padding-left: 0; }
  .campaign-property:nth-child(even) { padding-right: 0; border-right: 0; }
}
@media (max-width: 520px) {
  .campaign-page-bar { padding: 0 14px; }
  .campaign-content { padding: 18px 14px 58px; }
  .campaign-head { min-height: auto; display: grid; gap: 4px; padding: 15px; }
  .campaign-divider { display: none; }
  .campaign-heading-copy { display: block; }
  .campaign-heading-copy p { margin-top: 3px; white-space: normal; }
  .campaign-properties { grid-template-columns: 1fr; padding: 0 15px; }
  .campaign-property,.campaign-property:nth-child(odd),.campaign-property:nth-child(even) { padding: 11px 0; border-right: 0; border-bottom: 1px solid var(--c-line-soft); }
  .campaign-property:last-child { border-bottom: 0; }
  .campaign-section-head .campaign-action span:last-child { display: none; }
  .campaign-empty-state p { white-space: normal; }
}
</style>
