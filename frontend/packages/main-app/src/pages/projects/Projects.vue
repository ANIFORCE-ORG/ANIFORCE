<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/auth'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import CreateProjectModal from '@/components/projects/CreateProjectModal.vue'
import CreateCampaignModal from '@/components/campaigns/CreateCampaignModal.vue'
import ProjectCardCompact from '@/components/projects/ProjectCardCompact.vue'
import Toast from '@/components/toasts/Toast.vue'
import { getProjects, createProject, updateProject, type Project } from '@/api/projects'
import { createCampaign } from '@/api/campaigns'
import { navItems } from '@/config/navigation'

const router = useRouter()
const auth = useAuthStore()

// Toast 状态
const showToast = ref(false)
const toastMessage = ref('')
const toastType = ref<'success' | 'error' | 'warning' | 'info'>('info')

const showToastMessage = (message: string, type: 'success' | 'error' | 'warning' | 'info' = 'info') => {
  toastMessage.value = message
  toastType.value = type
  showToast.value = true
}

const handleToastClose = () => {
  showToast.value = false
}

const activeSession = ref('sess_g001')
const showCreateModal = ref(false)
const showCampaignModal = ref(false)
const editingProject = ref<Project | null>(null)
const currentProjectId = ref<string | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const projects = ref<Project[]>([])
const searchQuery = ref('')
const filterStatus = ref('all')
const createModalRef = ref<any>(null)
const campaignModalRef = ref<any>(null)
const cardViewType = ref<'compact' | 'detailed'>('compact')
const selectedProjectIds = ref<Set<string>>(new Set())

const sessions = ref([
  { id: 'sess_g001', name: 'Candy Blast投放咨询', active: true },
  { id: 'sess_g002', name: '素材优化建议', active: false },
  { id: 'sess_g003', name: '东南亚市场拓展', active: false },
  { id: 'sess_g004', name: 'DramaBox新剧推广', active: false },
])

const statusFilters = [
  { value: 'all', label: '全部项目' },
  { value: 'active', label: '进行中' },
  { value: 'paused', label: '已暂停' },
  { value: 'completed', label: '已完成' },
]

// 加载项目数据
const loadProjects = async () => {
  loading.value = true
  error.value = null

  try {
    console.log('开始加载项目数据...')
    const data = await getProjects({ limit: 50 })
    projects.value = data
    const availableIds = new Set(data.map(project => project.id))
    selectedProjectIds.value = new Set(
      [...selectedProjectIds.value].filter(projectId => availableIds.has(projectId))
    )
    console.log('项目数据加载成功:', data.length, '条')
  } catch (err: any) {
    error.value = err.message || '加载数据失败'
    console.error('加载数据失败:', err)
  } finally {
    loading.value = false
  }
}

// 组件挂载时加载项目
onMounted(async () => {
  await loadProjects()
})

// 筛选后的项目列表
const filteredProjects = computed(() => {
  let result = projects.value

  // 按状态筛选
  if (filterStatus.value !== 'all') {
    result = result.filter(p => {
      if (filterStatus.value === 'active') {
        return p.status === 'active' || p.status === 'running'
      }
      return p.status === filterStatus.value
    })
  }

  // 按搜索关键词筛选
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p =>
      p.name.toLowerCase().includes(query) ||
      p.tags.some(tag => tag.toLowerCase().includes(query))
    )
  }

  return result
})

const selectedProjectCount = computed(() => selectedProjectIds.value.size)

const handleProjectSelect = (project: Project, selected: boolean) => {
  const nextSelectedIds = new Set(selectedProjectIds.value)

  if (selected) {
    nextSelectedIds.add(project.id)
  } else {
    nextSelectedIds.delete(project.id)
  }

  selectedProjectIds.value = nextSelectedIds
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

const handleSearch = () => {
  // 筛选逻辑在 computed 中处理
}

const handleCreateProject = () => {
  editingProject.value = null
  showCreateModal.value = true
}

const handleEditProject = (project: Project) => {
  editingProject.value = project
  showCreateModal.value = true
}

const handleCreateTask = (project: Project) => {
  // 设置当前项目ID并打开Campaign模态框
  currentProjectId.value = project.id
  showCampaignModal.value = true
}

const handleCloseModal = () => {
  showCreateModal.value = false
  editingProject.value = null
}

const handleSubmitProject = async (data: any) => {
  try {
    if (editingProject.value) {
      // 编辑模式：更新现有项目
      console.log('=== 更新项目请求 ===')
      console.log('项目ID:', editingProject.value.id)
      console.log('表单数据:', JSON.stringify(data, null, 2))

      const updatedProject = await updateProject(editingProject.value.id, data)
      console.log('项目更新成功:', updatedProject)

      // 更新项目列表中的项目
      const index = projects.value.findIndex(p => p.id === editingProject.value!.id)
      if (index !== -1) {
        projects.value[index] = updatedProject
      }

      // 显示成功提示
      showToastMessage('项目更新成功！', 'success')

      // 关闭弹窗并重置表单
      showCreateModal.value = false
      editingProject.value = null
      createModalRef.value?.resetForm()
    } else {
      // 创建模式：创建新项目
      console.log('=== 创建项目请求 ===')
      console.log('表单数据:', JSON.stringify(data, null, 2))

      // 添加额外的后端必需字段
      const requestData = {
        ...data,  // 已包含: name, product, target_market, status, start_date, end_date, total_budget, description
        manager: auth.user?.name || '未知',
        game_type: data.product,  // 使用产品作为游戏类型
        tags: []
      }

      console.log('请求数据:', JSON.stringify(requestData, null, 2))

      const newProject = await createProject(requestData)
      console.log('项目创建成功:', newProject)

      // 添加到项目列表
      projects.value.unshift(newProject)

      // 关闭项目模态框
      showCreateModal.value = false

      // 保存项目ID并打开Campaign模态框
      currentProjectId.value = newProject.id
      showCampaignModal.value = true

      // 显示成功提示
      showToastMessage('项目创建成功！请继续创建 Campaign', 'success')

      // 重置表单
      createModalRef.value?.resetForm()
    }
  } catch (err: any) {
    console.error('=== 创建项目失败 ===')
    console.error('错误对象:', err)
    console.error('错误响应:', err.response)
    console.error('错误数据:', err.response?.data)

    // 解析错误信息
    let errorMessage = '创建项目失败，请重试'

    if (err.response?.data?.detail) {
      // FastAPI 返回的错误格式
      if (Array.isArray(err.response.data.detail)) {
        // Pydantic 验证错误格式
        const errors = err.response.data.detail.map((e: any) =>
          `${e.loc.join('.')}: ${e.msg}`
        ).join('; ')
        errorMessage = `数据验证失败: ${errors}`
      } else if (typeof err.response.data.detail === 'string') {
        errorMessage = err.response.data.detail
      } else {
        errorMessage = JSON.stringify(err.response.data.detail)
      }
    } else if (err.message) {
      errorMessage = err.message
    } else if (typeof err === 'string') {
      errorMessage = err
    }

    console.error('最终错误信息:', errorMessage)

    // 使用 Toast 显示错误
    showToastMessage(errorMessage, 'error')
  } finally {
    createModalRef.value?.setSubmitting(false)
  }
}

const handleCloseCampaignModal = () => {
  showCampaignModal.value = false
  currentProjectId.value = null
}

const handleSubmitCampaign = async (data: any) => {
  try {
    console.log('=== 创建 Campaign 请求 ===')
    console.log('Campaign 数据:', JSON.stringify(data, null, 2))
    console.log('关联项目 ID:', currentProjectId.value)

    if (!currentProjectId.value) {
      showToastMessage('项目 ID 缺失，无法创建 Campaign', 'error')
      return
    }

    // 添加 project_id（字段映射已在 CreateCampaignModal 中完成）
    const requestData = {
      project_id: currentProjectId.value,
      ...data
    }

    console.log('请求数据:', JSON.stringify(requestData, null, 2))

    const newCampaign = await createCampaign(requestData)
    console.log('Campaign 创建成功:', newCampaign)

    // 显示成功提示
    showToastMessage('Campaign 创建成功！', 'success')

    // 关闭 Campaign 模态框
    showCampaignModal.value = false
    currentProjectId.value = null

    // 刷新项目列表
    await loadProjects()
  } catch (err: any) {
    console.error('=== 创建 Campaign 失败 ===', err)

    // 解析错误信息
    let errorMessage = '创建 Campaign 失败，请重试'
    if (err.response?.data?.detail) {
      if (Array.isArray(err.response.data.detail)) {
        const errors = err.response.data.detail.map((e: any) =>
          `${e.loc.join('.')}: ${e.msg}`
        ).join('; ')
        errorMessage = `数据验证失败: ${errors}`
      } else if (typeof err.response.data.detail === 'string') {
        errorMessage = err.response.data.detail
      }
    } else if (err.message) {
      errorMessage = err.message
    }

    showToastMessage(errorMessage, 'error')

    // 重置提交状态
    if (campaignModalRef.value) {
      campaignModalRef.value.setSubmitting(false)
    }
  } finally {
    // 确保提交状态被重置
    if (campaignModalRef.value) {
      campaignModalRef.value.setSubmitting(false)
    }
  }
}
</script>

<template>
  <!-- 三栏布局容器 -->
  <div class="projects-shell">
    <!-- 左侧功能导航抽屉 -->
    <SidebarNav
      :nav-items="navItems"
      :sessions="sessions"
      @switch-panel="switchPanel"
      @switch-session="switchSession"
    />

    <!-- 中间项目展示区 -->
    <main class="projects-main">
      <!-- Header -->
      <div class="projects-page-bar">
        <div>
          <h1 class="projects-page-title">项目管理</h1>
          <p class="projects-page-description">浏览、筛选并打开当前账号下的投放项目。</p>
        </div>
        <div class="projects-page-actions">
          <!-- View Toggle -->
          <div class="projects-view-switch" aria-label="项目视图切换">
            <button
              type="button"
              class="projects-view-button"
              :class="{ active: cardViewType === 'compact' }"
              aria-label="网格视图"
              :aria-pressed="cardViewType === 'compact'"
              @click="cardViewType = 'compact'"
            >
              <span class="material-symbols-outlined">grid_view</span>
            </button>
            <button
              type="button"
              class="projects-view-button"
              :class="{ active: cardViewType === 'detailed' }"
              aria-label="列表视图"
              :aria-pressed="cardViewType === 'detailed'"
              @click="cardViewType = 'detailed'"
            >
              <span class="material-symbols-outlined">view_list</span>
            </button>
          </div>
          <button
            type="button"
            class="projects-create-button"
            @click="handleCreateProject"
          >
            <span class="material-symbols-outlined">add</span>
            <span class="projects-create-label">创建项目</span>
          </button>
        </div>
      </div>

      <!-- Search & Filter Bar -->
      <div class="projects-toolbar">
        <div class="projects-search-field">
          <span class="material-symbols-outlined">search</span>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="搜索项目名称或标签..."
            aria-label="搜索项目名称或标签"
            @input="handleSearch"
          />
        </div>
        <select
          v-model="filterStatus"
          class="projects-status-filter"
          aria-label="按项目状态筛选"
          @change="handleSearch"
        >
          <option v-for="filter in statusFilters" :key="filter.value" :value="filter.value">
            {{ filter.label }}
          </option>
        </select>
      </div>

      <!-- Projects List -->
      <div class="projects-scroll-area">
        <div class="projects-content">
          <div class="projects-content-meta" aria-live="polite">
            <span>共 {{ filteredProjects.length }} 个项目</span>
            <span v-if="selectedProjectCount > 0" class="projects-selection-meta">
              已选择 {{ selectedProjectCount }} 个
            </span>
          </div>

          <div
            v-if="filteredProjects.length > 0"
            class="projects-grid"
            :class="{ 'is-list': cardViewType === 'detailed' }"
          >
            <ProjectCardCompact
              v-for="project in filteredProjects"
              :key="project.id"
              :project="project"
              :selected="selectedProjectIds.has(project.id)"
              :view-type="cardViewType"
              @edit="handleEditProject"
              @create-task="handleCreateTask"
              @view-tasks="console.log('View tasks:', $event)"
              @select="handleProjectSelect"
            />
          </div>

          <!-- Empty State -->
          <div v-else class="projects-empty-state">
            <span class="material-symbols-outlined">folder_off</span>
            <p>未找到匹配的项目</p>
            <span>尝试调整搜索关键词或项目状态。</span>
          </div>
        </div>
      </div>
    </main>

    <!-- 创建项目弹窗 -->
    <CreateProjectModal
      ref="createModalRef"
      :show="showCreateModal"
      :editing-project="editingProject"
      @close="handleCloseModal"
      @submit="handleSubmitProject"
    />

    <!-- 创建 Campaign 弹窗 -->
    <CreateCampaignModal
      ref="campaignModalRef"
      :show="showCampaignModal"
      :project-id="currentProjectId || undefined"
      @close="handleCloseCampaignModal"
      @submit="handleSubmitCampaign"
    />

    <!-- Toast 提示 -->
    <Toast
      :show="showToast"
      :message="toastMessage"
      :type="toastType"
      :duration="5000"
      @close="handleToastClose"
    />
  </div>
</template>

<style scoped>
.projects-shell {
  display: flex;
  width: 100%;
  height: calc(100vh - 100px);
  overflow: hidden;
  background: #f7f7f5;
}

.projects-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
  color: #191919;
}

.projects-page-bar {
  min-height: 92px;
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 20px clamp(24px, 3vw, 48px);
  border-bottom: 1px solid #e7e5e2;
}

.projects-page-title {
  margin: 0;
  color: #191919;
  font-size: 24px;
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.025em;
}

.projects-page-description {
  margin: 5px 0 0;
  color: #787774;
  font-size: 12px;
  line-height: 1.55;
}

.projects-page-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.projects-view-switch {
  display: flex;
  align-items: center;
  padding: 3px;
  border: 1px solid #e7e5e2;
  border-radius: 8px;
  background: #f7f7f5;
}

.projects-view-button {
  width: 34px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #787774;
  cursor: pointer;
  transition: background-color 0.16s ease, color 0.16s ease, box-shadow 0.16s ease;
}

.projects-view-button .material-symbols-outlined {
  font-size: 18px;
}

.projects-view-button:hover {
  color: #37352f;
  background: rgba(55, 53, 47, 0.06);
}

.projects-view-button.active {
  color: #191919;
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(15, 15, 15, 0.08);
}

.projects-create-button {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 14px;
  border: 1px solid #137fec;
  border-radius: 7px;
  background: #137fec;
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(19, 127, 236, 0.16);
  transition: background-color 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
}

.projects-create-button:hover {
  border-color: #0c6cd4;
  background: #0c6cd4;
}

.projects-create-button:active {
  transform: translateY(1px);
}

.projects-create-button .material-symbols-outlined {
  font-size: 18px;
}

.projects-toolbar {
  flex: 0 0 auto;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 132px;
  align-items: center;
  gap: 12px;
  padding: 12px clamp(24px, 3vw, 48px);
  border-bottom: 1px solid #e7e5e2;
  background: #ffffff;
}

.projects-search-field {
  position: relative;
  min-width: 0;
}

.projects-search-field .material-symbols-outlined {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #9b9a97;
  font-size: 17px;
  pointer-events: none;
}

.projects-search-field input,
.projects-status-filter {
  width: 100%;
  height: 38px;
  border: 1px solid #dedbd7;
  border-radius: 7px;
  background: #ffffff;
  color: #37352f;
  font-size: 12px;
  outline: none;
  transition: border-color 0.16s ease, box-shadow 0.16s ease;
}

.projects-search-field input {
  padding: 0 13px 0 38px;
}

.projects-search-field input::placeholder {
  color: #aaa8a4;
}

.projects-status-filter {
  padding: 0 32px 0 12px;
  cursor: pointer;
}

.projects-search-field input:focus,
.projects-status-filter:focus {
  border-color: #98c3f0;
  box-shadow: 0 0 0 3px rgba(19, 127, 236, 0.12);
}

.projects-scroll-area {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  background: #ffffff;
}

.projects-content {
  width: min(100%, 1320px);
  margin: 0 auto;
  padding: 22px clamp(24px, 3vw, 48px) 78px;
}

.projects-content-meta {
  min-height: 24px;
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  color: #9b9a97;
  font-size: 11px;
}

.projects-selection-meta {
  padding-left: 12px;
  border-left: 1px solid #dedbd7;
  color: #137fec;
  font-weight: 600;
}

.projects-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.projects-grid.is-list {
  grid-template-columns: 1fr;
  gap: 12px;
}

.projects-empty-state {
  min-height: 250px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 7px;
  border: 1px dashed #d8d5d0;
  border-radius: 12px;
  background: #fafaf9;
  color: #9b9a97;
  text-align: center;
}

.projects-empty-state .material-symbols-outlined {
  margin-bottom: 3px;
  color: #b4b2ae;
  font-size: 42px;
}

.projects-empty-state p {
  margin: 0;
  color: #37352f;
  font-size: 13px;
  font-weight: 600;
}

.projects-empty-state span:last-child {
  font-size: 11px;
}

.dark .projects-main,
.dark .projects-toolbar,
.dark .projects-scroll-area {
  background: #191919;
  color: #f3f3f2;
}

.dark .projects-page-bar,
.dark .projects-toolbar {
  border-color: #373737;
}

.dark .projects-page-title {
  color: #f3f3f2;
}

.dark .projects-page-description,
.dark .projects-content-meta {
  color: #a6a6a2;
}

.dark .projects-view-switch,
.dark .projects-empty-state {
  border-color: #464646;
  background: #242424;
}

.dark .projects-view-button.active,
.dark .projects-search-field input,
.dark .projects-status-filter {
  background: #2f2f2f;
  color: #f3f3f2;
}

.dark .projects-search-field input,
.dark .projects-status-filter {
  border-color: #464646;
}

.dark .projects-empty-state p {
  color: #f3f3f2;
}

@media (max-width: 1180px) {
  .projects-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .projects-page-bar {
    min-height: 78px;
    padding: 16px 20px;
  }

  .projects-page-description {
    display: none;
  }

  .projects-toolbar {
    padding: 12px 20px;
  }

  .projects-content {
    padding: 18px 20px 60px;
  }

  .projects-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .projects-page-title {
    font-size: 20px;
  }

  .projects-view-switch {
    display: none;
  }

  .projects-create-button {
    width: 38px;
    padding: 0;
  }

  .projects-create-label {
    display: none;
  }

  .projects-toolbar {
    grid-template-columns: 1fr;
  }

  .projects-status-filter {
    display: none;
  }
}
</style>
