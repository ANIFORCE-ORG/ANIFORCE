<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import CampaignCardDetailed from '@/components/campaigns/CampaignCardDetailed.vue'
import CreateCampaignModal from '@/components/campaigns/CreateCampaignModal.vue'
import Toast from '@/components/toasts/Toast.vue'
import { getProjectDetail, getProjectCampaigns, type Project } from '@/api/projects'
import { createCampaign, updateCampaign, deleteCampaign } from '@/api/campaigns'
import { navItems } from '@/config/navigation'

const router = useRouter()
const route = useRoute()

const projectId = ref(route.params.id as string)
const activeSession = ref('sess_g001')
const loading = ref(false)
const error = ref<string | null>(null)

const project = ref<Project | null>(null)
const campaigns = ref<any[]>([])
const showCampaignModal = ref(false)
const campaignModalRef = ref<any>(null)
const editingCampaign = ref<any>(null)

// Toast 状态管理
const showToast = ref(false)
const toastMessage = ref('')
const toastType = ref<'success' | 'error' | 'warning' | 'info'>('info')

const sessions = ref([
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场测试', active: false },
  { id: 'sess_d001', name: 'DramaBox新剧推广', active: false }
])

onMounted(async () => {
  await loadProjectData()
})

const loadProjectData = async () => {
  loading.value = true
  error.value = null

  try {
    console.log('加载项目详情:', projectId.value)

    // 加载项目详情
    const projectData = await getProjectDetail(projectId.value)
    project.value = projectData
    console.log('项目详情加载成功:', projectData)

    // 加载关联的广告投放
    const campaignsData = await getProjectCampaigns(projectId.value)
    campaigns.value = campaignsData
    console.log('关联广告投放加载成功:', campaignsData.length, '条')
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

const handleBack = () => {
  router.push('/projects')
}

const formatMoney = (value?: number) => {
  return typeof value === 'number' ? `$${value.toLocaleString()}` : '-'
}

const getProjectStatusLabel = (status?: string) => {
  const labels: Record<string, string> = {
    active: '进行中',
    running: '进行中',
    paused: '已暂停',
    completed: '已完成',
    draft: '草稿'
  }
  return status ? (labels[status] || status) : '-'
}

const handleCreateCampaign = () => {
  showCampaignModal.value = true
}

const handleSubmitCampaign = async (data: any) => {
  try {
    const isEdit = !!data.id
    console.log(`=== ${isEdit ? '更新' : '创建'} Campaign 请求 ===`)
    console.log('Campaign 数据:', JSON.stringify(data, null, 2))

    let result
    if (isEdit) {
      // 编辑模式：更新 Campaign
      console.log('Campaign ID:', data.id)
      result = await updateCampaign(data.id, data)
      console.log('Campaign 更新成功:', result)

      // 显示成功提示
      toastMessage.value = 'Campaign 更新成功！'
      toastType.value = 'success'
      showToast.value = true
    } else {
      // 创建模式：创建新 Campaign
      console.log('关联项目 ID:', projectId.value)

      if (!projectId.value) {
        console.error('项目 ID 缺失，无法创建 Campaign')
        toastMessage.value = '项目 ID 缺失，无法创建 Campaign'
        toastType.value = 'error'
        showToast.value = true
        return
      }

      // 添加 project_id（字段映射已在 CreateCampaignModal 中完成）
      const requestData = {
        project_id: projectId.value,
        ...data
      }

      console.log('请求数据:', JSON.stringify(requestData, null, 2))
      result = await createCampaign(requestData)
      console.log('Campaign 创建成功:', result)

      // 显示成功提示
      toastMessage.value = 'Campaign 创建成功！'
      toastType.value = 'success'
      showToast.value = true
    }

    // 关闭 Campaign 模态框
    showCampaignModal.value = false
    editingCampaign.value = null

    // 刷新 Campaign 列表
    await loadCampaigns()
  } catch (err: any) {
    console.error(`=== ${data.id ? '更新' : '创建'} Campaign 失败 ===`, err)

    // 显示错误提示
    toastMessage.value = `${data.id ? '更新' : '创建'} Campaign 失败：${err.message || '未知错误'}`
    toastType.value = 'error'
    showToast.value = true

    // 重置提交状态
    if (campaignModalRef.value) {
      campaignModalRef.value.setSubmitting(false)
    }
  } finally {
    // 确保重置提交状态
    if (campaignModalRef.value) {
      campaignModalRef.value.setSubmitting(false)
    }
  }
}

const loadCampaigns = async () => {
  try {
    const data = await getProjectCampaigns(projectId.value)
    campaigns.value = data
    console.log('Campaign 列表加载成功:', data.length, '条')
  } catch (err: any) {
    console.error('加载 Campaign 列表失败:', err)
  }
}

const handleViewCampaign = (campaignId: string) => {
  router.push(`/campaigns/${campaignId}`)
}

const handleAddCreative = (campaignId: string) => {
  console.log('添加素材:', campaignId)
}

const handleEditCampaign = (campaign: any) => {
  console.log('编辑 Campaign:', campaign)
  editingCampaign.value = campaign
  showCampaignModal.value = true
}

const handleDeleteCampaign = async (campaignId: string) => {
  // 显示确认对话框
  const confirmed = confirm('确定要删除这个 Campaign 吗？此操作无法撤销。')
  
  if (!confirmed) {
    return
  }
  
  try {
    console.log('删除 Campaign:', campaignId)
    await deleteCampaign(campaignId)
    
    // 显示成功提示
    toastMessage.value = 'Campaign 删除成功！'
    toastType.value = 'success'
    showToast.value = true
    
    // 重新加载 Campaign 列表
    await loadCampaigns()
  } catch (err: any) {
    console.error('删除 Campaign 失败:', err)
    toastMessage.value = err.message || '删除 Campaign 失败'
    toastType.value = 'error'
    showToast.value = true
  }
}

const handleCloseToast = () => {
  showToast.value = false
}
</script>

<template>
  <div class="project-detail-shell">
    <!-- 左侧功能导航抽屉 -->
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      active-panel="projects"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <main class="project-detail-main">
      <header class="detail-page-bar">
        <button class="detail-back-button" @click="handleBack">
          <span class="material-symbols-outlined">arrow_back</span>
          返回项目列表
        </button>
      </header>

      <div class="detail-scroll-area">
        <div class="detail-content">
          <section class="project-panel">
            <div class="project-head">
              <h1>{{ project?.name || '-' }}</h1>
              <span class="project-divider"></span>
              <div class="project-summary">
                <h2>项目信息</h2>
                <p>{{ project?.description || '暂无描述' }}</p>
              </div>
            </div>

            <dl class="property-grid">
              <div class="property">
                <dt>产品类型</dt>
                <dd>{{ project?.game_type || '-' }}</dd>
              </div>
              <div class="property">
                <dt>目标市场</dt>
                <dd>{{ project?.target_market || '-' }}</dd>
              </div>
              <div class="property">
                <dt>总预算</dt>
                <dd>{{ formatMoney(project?.total_budget) }}</dd>
              </div>
              <div class="property">
                <dt>已消耗</dt>
                <dd>{{ formatMoney(project?.spent) }}</dd>
              </div>
              <div class="property">
                <dt>标签</dt>
                <dd :class="{ muted: !project?.tags?.length }">
                  {{ project?.tags?.length ? project.tags.join(' · ') : '—' }}
                </dd>
              </div>
              <div class="property">
                <dt>开始 / 结束</dt>
                <dd>{{ project?.start_date || '-' }} / {{ project?.end_date || '-' }}</dd>
              </div>
              <div class="property">
                <dt>负责人</dt>
                <dd>{{ project?.manager || '-' }}</dd>
              </div>
              <div class="property">
                <dt>状态</dt>
                <dd>
                  <span
                    class="status-chip detail-status"
                    :data-status="project?.status"
                  >
                    {{ getProjectStatusLabel(project?.status) }}
                  </span>
                </dd>
              </div>
            </dl>
          </section>

          <section class="campaign-section">
            <div class="section-head">
              <h2>广告 Campaigns ({{ campaigns.length }})</h2>
              <button class="primary-button" @click="handleCreateCampaign">
                <span class="material-symbols-outlined">add</span>
                <span>创建广告任务</span>
              </button>
            </div>

            <div class="campaign-list">
              <CampaignCardDetailed
                v-for="campaign in campaigns"
                :key="campaign.id"
                :campaign="campaign"
                @view="handleViewCampaign"
                @add-creative="handleAddCreative"
                @edit="handleEditCampaign"
                @delete="handleDeleteCampaign"
              />
            </div>

            <div v-if="!loading && !error && campaigns.length === 0" class="campaign-empty">
              当前项目暂无广告 Campaign
            </div>

            <div v-else-if="loading" class="campaign-empty">
              正在加载项目详情…
            </div>

            <div v-else-if="error" class="campaign-empty campaign-error">
              {{ error }}
            </div>
          </section>
        </div>
      </div>
    </main>

    <!-- Campaign 创建/编辑模态框 -->
    <CreateCampaignModal
      ref="campaignModalRef"
      :show="showCampaignModal"
      :initial-data="editingCampaign"
      @close="showCampaignModal = false; editingCampaign = null"
      @submit="handleSubmitCampaign"
    />

    <!-- Toast 提示组件 -->
    <Toast
      :show="showToast"
      :message="toastMessage"
      :type="toastType"
      @close="handleCloseToast"
    />
  </div>
</template>

<style scoped>
.project-detail-shell {
  --detail-surface: #f6f5f4;
  --detail-surface-soft: #fafaf9;
  --detail-hairline: #e5e3df;
  --detail-hairline-soft: #ede9e4;
  --detail-hairline-strong: #c8c4be;
  --detail-ink: #1a1a1a;
  --detail-charcoal: #37352f;
  --detail-slate: #5d5b54;
  --detail-steel: #787671;
  --detail-stone: #a4a097;
  display: flex;
  width: 100%;
  height: calc(100vh - 100px);
  overflow: hidden;
  background: #fff;
  color: var(--detail-charcoal);
}

.project-detail-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}

.detail-page-bar {
  min-height: 54px;
  display: flex;
  align-items: center;
  padding: 0 clamp(24px, 3vw, 48px);
  border-bottom: 1px solid var(--detail-hairline);
  background: rgba(255, 255, 255, 0.88);
}

.detail-back-button {
  min-height: 31px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 8px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--detail-slate);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
}

.detail-back-button:hover {
  background: var(--detail-surface);
  color: var(--detail-ink);
}

.detail-back-button .material-symbols-outlined {
  font-size: 16px;
}

.detail-scroll-area {
  flex: 1;
  overflow-y: auto;
}

.detail-content {
  width: min(100%, 1240px);
  margin: 0 auto;
  padding: 24px clamp(24px, 3vw, 48px) 78px;
}

.project-panel {
  padding: 18px 20px 20px;
  border: 1px solid var(--detail-hairline);
  border-radius: 12px;
  background: #fff;
}

.project-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--detail-hairline-soft);
  white-space: nowrap;
}

.project-head h1 {
  margin: 0;
  color: var(--detail-ink);
  font-size: 17px;
  font-weight: 650;
  letter-spacing: -0.35px;
}

.project-divider {
  width: 1px;
  height: 15px;
  align-self: center;
  background: var(--detail-hairline-strong);
}

.project-summary {
  min-width: 0;
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.project-summary h2 {
  margin: 0;
  color: var(--detail-slate);
  font-size: 10px;
  font-weight: 600;
}

.project-summary p {
  margin: 0;
  overflow: hidden;
  color: var(--detail-steel);
  font-size: 10px;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.property-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.property {
  min-width: 0;
  min-height: 57px;
  padding: 10px 12px;
  border: 1px solid var(--detail-hairline);
  border-radius: 8px;
  background: var(--detail-surface-soft);
}

.property dt {
  margin: 0;
  color: var(--detail-steel);
  font-size: 9px;
  line-height: 1.3;
}

.property dd {
  margin: 4px 0 0;
  overflow-wrap: anywhere;
  color: var(--detail-ink);
  font-size: 11px;
  font-weight: 600;
  line-height: 1.35;
}

.property dd.muted {
  color: var(--detail-stone);
  font-weight: 500;
}

.detail-status {
  min-height: 22px;
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 6px;
  background: var(--detail-surface);
  color: var(--detail-slate);
  font-size: 10px;
  font-weight: 600;
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin: 28px 0 11px;
}

.section-head h2 {
  margin: 0;
  color: var(--detail-ink);
  font-size: 14px;
  font-weight: 600;
}

.primary-button {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 13px;
  border: 1px solid var(--detail-charcoal);
  border-radius: 8px;
  background: var(--detail-charcoal);
  color: #fff;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
}

.primary-button:hover {
  border-color: var(--detail-ink);
  background: var(--detail-ink);
}

.primary-button .material-symbols-outlined {
  font-size: 16px;
}

.campaign-list {
  display: grid;
  gap: 9px;
}

.campaign-empty {
  min-height: 120px;
  display: grid;
  place-items: center;
  border: 1px dashed var(--detail-hairline-strong);
  border-radius: 12px;
  background: var(--detail-surface-soft);
  color: var(--detail-steel);
  font-size: 11px;
}

.campaign-error {
  border-color: #e8b8b5;
  color: #c93c37;
}

@media (max-width: 1000px) {
  .property-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .detail-page-bar {
    padding: 0 14px;
  }

  .detail-content {
    padding: 18px 14px 58px;
  }
}

@media (max-width: 520px) {
  .project-panel {
    padding: 15px;
  }

  .project-head {
    display: grid;
    grid-template-columns: 1fr;
    gap: 5px;
    white-space: normal;
  }

  .project-divider {
    display: none;
  }

  .project-summary {
    display: block;
  }

  .project-summary p {
    margin-top: 3px;
    white-space: normal;
  }

  .property-grid {
    grid-template-columns: 1fr;
  }

  .section-head {
    align-items: flex-start;
  }

  .section-head .primary-button span:last-child {
    display: none;
  }
}
</style>
