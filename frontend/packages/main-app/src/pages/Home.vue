<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import ChatPanel from '@/components/layout/ChatPanel.vue'
import { navItems } from '@/config/navigation'
import { useWorkspaceSessions } from '@/composables/useWorkspaceSessions'
import { getProjects, createProject, type Project } from '@/api/projects'
import { platformApi, type PlatformConnectionResponse } from '@/api/platform'
import {
  bindProjectPlatformAccount,
  getPlatformAccounts,
  syncPlatformAccounts,
  type PlatformAccount,
} from '@/api/platformAccounts'

type StepStatus = 'completed' | 'in_progress' | 'blocked' | 'not_started'

const router = useRouter()
const workspaceSessions = useWorkspaceSessions('new-task')

const loading = ref(true)
const projects = ref<Project[]>([])
const selectedProjectId = ref('')
const connections = ref<PlatformConnectionResponse[]>([])
const accounts = ref<PlatformAccount[]>([])
const selectedAccountId = ref('')
const accountApiUnavailable = ref(false)
const usingDemoProject = ref(false)
const usingDemoAccount = ref(false)
const savingProject = ref(false)
const syncingAccounts = ref(false)
const bindingAccount = ref(false)

const newProjectName = ref('')
const productType = ref('game')
const targetMarket = ref('US')

const selectedProject = computed(() =>
  projects.value.find(project => project.id === selectedProjectId.value) || null
)

const activeMetaConnection = computed(() =>
  connections.value.find(connection => connection.platform === 'Meta' && connection.status === 'active') || null
)

const selectedAccount = computed(() =>
  accounts.value.find(account => account.id === selectedAccountId.value) || null
)

const materialReady = computed(() => false)
const hasPlatformReady = computed(() => Boolean(activeMetaConnection.value || usingDemoAccount.value))

const setupSteps = computed<Array<{
  id: string
  title: string
  description: string
  status: StepStatus
}>>(() => [
  {
    id: 'project',
    title: '业务项目',
    description: selectedProject.value ? selectedProject.value.name : '创建或选择一个业务项目。',
    status: selectedProject.value ? 'completed' : 'in_progress',
  },
  {
    id: 'platform',
    title: '广告平台',
    description: hasPlatformReady.value ? 'Meta 已授权或使用 Demo 账户，可以继续创建草稿。' : '连接 Meta 广告账户，后续再扩展 Google 和 TikTok。',
    status: hasPlatformReady.value ? 'completed' : 'not_started',
  },
  {
    id: 'account',
    title: '广告账户',
    description: selectedAccount.value ? selectedAccount.value.account_name : '选择一个已授权广告账户并绑定到项目。',
    status: selectedAccount.value ? 'completed' : 'not_started',
  },
  {
    id: 'assets',
    title: '投放前置资产',
    description: '第一版先校验广告账户；Page、Pixel/Dataset、App 作为发布前检查项。',
    status: selectedAccount.value ? 'completed' : 'not_started',
  },
  {
    id: 'creative',
    title: '素材准备',
    description: materialReady.value ? '已有可用素材。' : '可以先创建草稿，提交发布前再补齐素材。',
    status: selectedAccount.value ? 'in_progress' : 'not_started',
  },
  {
    id: 'campaign',
    title: '创建计划',
    description: '带着项目、平台和广告账户进入创建计划页。',
    status: selectedProject.value && selectedAccount.value ? 'in_progress' : 'not_started',
  },
])

const completedCount = computed(() =>
  setupSteps.value.filter(step => step.status === 'completed').length
)

const canCreateCampaign = computed(() =>
  Boolean(selectedProject.value && selectedAccount.value)
)

const switchPanel = (item: any) => {
  if (item.path) router.push(item.path)
}

const loadProjects = async () => {
  try {
    projects.value = await getProjects({ limit: 20 })
    if (!selectedProjectId.value && projects.value.length > 0) {
      selectedProjectId.value = projects.value[0].id
    }
  } catch (err) {
    usingDemoProject.value = true
    const demoProject = {
      id: 'demo-project-001',
      name: 'Demo 广告项目',
      game_type: 'game',
      target_market: 'US',
      tags: ['demo'],
      total_budget: 0,
      spent: 0,
      status: 'draft',
      manager: 'Demo',
      start_date: '',
      end_date: '',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    projects.value = [demoProject]
    selectedProjectId.value = demoProject.id
    console.error('加载项目失败:', err)
  }
}

const loadConnections = async () => {
  try {
    connections.value = await platformApi.getAllConnections()
  } catch (err) {
    usingDemoAccount.value = true
    console.error('加载平台连接失败:', err)
  }
}

const loadAccounts = async () => {
  accountApiUnavailable.value = false
  try {
    accounts.value = await getPlatformAccounts({ platform: 'meta', status: 'active' })
    if (!selectedAccountId.value && accounts.value.length > 0) {
      selectedAccountId.value = accounts.value[0].id
    }
  } catch (err) {
    accountApiUnavailable.value = true
    usingDemoAccount.value = true
    accounts.value = [
      {
        id: 'demo-meta-account-001',
        platform: 'meta',
        account_id: 'act_demo_001',
        account_name: 'Demo Meta Ad Account',
        business_name: 'Demo Business',
        auth_status: 'demo',
        account_status: 'active',
        currency: 'USD',
        timezone: 'America/Los_Angeles',
        last_sync_at: new Date().toISOString(),
      },
    ]
    selectedAccountId.value = accounts.value[0].id
    console.error('加载广告账户失败:', err)
  }
}

const handleCreateProject = async () => {
  if (!newProjectName.value.trim() || savingProject.value) return
  savingProject.value = true
  try {
    const project = await createProject({
      name: newProjectName.value.trim(),
      game_type: productType.value,
      target_market: targetMarket.value,
      total_budget: 0,
      tags: [],
    })
    projects.value.unshift(project)
    selectedProjectId.value = project.id
    newProjectName.value = ''
  } catch (err) {
    usingDemoProject.value = true
    const project = {
      id: `demo-project-${Date.now()}`,
      name: newProjectName.value.trim(),
      game_type: productType.value,
      target_market: targetMarket.value,
      tags: ['demo'],
      total_budget: 0,
      spent: 0,
      status: 'draft',
      manager: 'Demo',
      start_date: '',
      end_date: '',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    projects.value.unshift(project)
    selectedProjectId.value = project.id
    newProjectName.value = ''
    console.error('创建项目失败:', err)
  } finally {
    savingProject.value = false
  }
}

const handleSyncAccounts = async () => {
  if (syncingAccounts.value) return
  syncingAccounts.value = true
  try {
    await syncPlatformAccounts('meta')
    await loadAccounts()
  } catch (err) {
    accountApiUnavailable.value = true
    usingDemoAccount.value = true
    accounts.value = [
      {
        id: 'demo-meta-account-001',
        platform: 'meta',
        account_id: 'act_demo_001',
        account_name: 'Demo Meta Ad Account',
        business_name: 'Demo Business',
        auth_status: 'demo',
        account_status: 'active',
        currency: 'USD',
        timezone: 'America/Los_Angeles',
        last_sync_at: new Date().toISOString(),
      },
    ]
    selectedAccountId.value = accounts.value[0].id
    console.error('同步广告账户失败:', err)
  } finally {
    syncingAccounts.value = false
  }
}

const handleBindAccount = async () => {
  if (!selectedProject.value || !selectedAccount.value || bindingAccount.value) return
  bindingAccount.value = true
  try {
    await bindProjectPlatformAccount(selectedProject.value.id, selectedAccount.value.id)
  } catch (err) {
    console.error('绑定广告账户失败:', err)
  } finally {
    bindingAccount.value = false
  }
}

const goPlatformConnections = () => {
  router.push('/platform-connections')
}

const goMaterials = () => {
  router.push('/material')
}

const goCreateCampaign = () => {
  if (!selectedProject.value || !selectedAccount.value) return
  router.push({
    path: '/campaigns/create',
    query: {
      projectId: selectedProject.value.id,
      platform: 'Meta',
      platformAccountId: selectedAccount.value.id,
    },
  })
}

const statusClass = (status: StepStatus) => {
  const classes: Record<StepStatus, string> = {
    completed: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    in_progress: 'border-slate-300 bg-white text-slate-900',
    blocked: 'border-slate-200 bg-slate-100 text-slate-500',
    not_started: 'border-slate-200 bg-slate-50 text-slate-500',
  }
  return classes[status]
}

const statusText = (status: StepStatus) => {
  const labels: Record<StepStatus, string> = {
    completed: '已完成',
    in_progress: '进行中',
    blocked: '需先完成前置步骤',
    not_started: '未开始',
  }
  return labels[status]
}

onMounted(async () => {
  loading.value = true
  await Promise.all([loadProjects(), loadConnections()])
  if (activeMetaConnection.value) {
    await loadAccounts()
  } else if (usingDemoAccount.value) {
    await loadAccounts()
  }
  loading.value = false
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav
      :nav-items="navItems"
      :sessions="workspaceSessions.sessions.value"
      active-panel="new-task"
      @switch-panel="switchPanel"
      @switch-session="workspaceSessions.switchSession"
    />

    <main class="min-w-0 flex-1 overflow-y-auto bg-white dark:bg-slate-900">
      <div class="mx-auto max-w-7xl px-6 py-8">
        <div class="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p class="text-sm font-semibold text-primary">新任务</p>
            <h1 class="mt-2 text-3xl font-black tracking-tight text-slate-950 dark:text-white">
              配置你的第一个广告工作流
            </h1>
            <p class="mt-3 max-w-3xl text-sm leading-7 text-slate-600 dark:text-slate-400">
              在创建广告计划前，先完成项目、平台授权和广告账户绑定。真实发布会进入异步任务，第一阶段先确保草稿创建路径稳定。
            </p>
          </div>

          <div class="rounded-lg border border-slate-200 bg-slate-50 px-5 py-4 dark:border-slate-800 dark:bg-slate-950">
            <p class="text-xs font-semibold text-slate-500 dark:text-slate-400">配置进度</p>
            <div class="mt-2 flex items-end gap-2">
              <span class="text-3xl font-black text-slate-950 dark:text-white">{{ completedCount }}</span>
              <span class="pb-1 text-sm text-slate-500">/ {{ setupSteps.length }}</span>
            </div>
          </div>
        </div>

        <div v-if="loading" class="mt-10 rounded-lg border border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-950">
          正在加载配置状态...
        </div>

        <div v-else class="mt-8 grid gap-6 xl:grid-cols-[0.75fr_1.25fr]">
          <div v-if="usingDemoProject || usingDemoAccount" class="xl:col-span-2 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm leading-6 text-blue-800">
            当前后端项目、平台或广告账户接口不可用，已启用 Demo 配置，方便完整测试前端流程。真实授权和账户绑定需等后端接口补齐后联调。
          </div>
          <aside class="space-y-3">
            <article
              v-for="(step, index) in setupSteps"
              :key="step.id"
              class="rounded-md border px-4 py-3"
              :class="statusClass(step.status)"
            >
              <div class="flex items-start justify-between gap-4">
                <div>
                  <p class="text-xs font-black opacity-70">0{{ index + 1 }}</p>
                  <h2 class="mt-1 text-sm font-black">{{ step.title }}</h2>
                  <p class="mt-1 text-xs leading-5 opacity-80">{{ step.description }}</p>
                </div>
                <span class="shrink-0 whitespace-nowrap rounded-md bg-white/70 px-2.5 py-1 text-xs font-bold">
                  {{ statusText(step.status) }}
                </span>
              </div>
            </article>
          </aside>

          <section class="space-y-5">
            <div class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <h2 class="text-base font-black text-slate-950 dark:text-white">1. 业务项目</h2>
                  <p class="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
                    项目是素材、账户和计划的业务容器。一个项目后续可以包含多个投放活动。
                  </p>
                </div>
                <select
                  v-if="projects.length"
                  v-model="selectedProjectId"
                  class="min-w-[220px] rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                >
                  <option v-for="project in projects" :key="project.id" :value="project.id">
                    {{ project.name }}
                  </option>
                </select>
              </div>

              <div class="mt-4 grid gap-3 md:grid-cols-[1fr_150px_150px_auto]">
                <input
                  v-model="newProjectName"
                  class="rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                  placeholder="创建新项目，例如 Candy Blast 全球推广"
                />
                <select v-model="productType" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white">
                  <option value="game">游戏</option>
                  <option value="ecommerce">电商</option>
                  <option value="app">应用</option>
                  <option value="other">其他</option>
                </select>
                <select v-model="targetMarket" class="rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-900 dark:text-white">
                  <option value="US">美国</option>
                  <option value="JP">日本</option>
                  <option value="KR">韩国</option>
                  <option value="SEA">东南亚</option>
                </select>
                <button
                  class="whitespace-nowrap rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white dark:text-slate-950"
                  :disabled="!newProjectName.trim() || savingProject"
                  @click="handleCreateProject"
                >
                  {{ savingProject ? '创建中' : '创建项目' }}
                </button>
              </div>
            </div>

            <div class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 class="text-base font-black text-slate-950 dark:text-white">2. 广告平台授权</h2>
                  <p class="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
                    第一阶段优先打通 Meta。Google 和 TikTok 保持展示，后续接入同一账户模型。
                  </p>
                </div>
                <button
                  class="whitespace-nowrap rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  @click="goPlatformConnections"
                >
                  去授权平台
                </button>
              </div>

              <div class="mt-5 grid gap-3 md:grid-cols-3">
                <div
                  v-for="platform in ['Meta', 'Google', 'TikTok']"
                  :key="platform"
                  class="rounded-md border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900"
                >
                  <div class="flex items-center justify-between gap-2">
                    <p class="font-black text-slate-950 dark:text-white">{{ platform }}</p>
                    <span
                      class="h-2.5 w-2.5 rounded-full"
                      :class="platform === 'Meta' && hasPlatformReady ? 'bg-emerald-500' : 'bg-slate-300'"
                    ></span>
                  </div>
                  <p class="mt-3 text-sm text-slate-500 dark:text-slate-400">
                    {{ platform === 'Meta' && hasPlatformReady ? (usingDemoAccount ? 'Demo 账户' : '已授权') : '未完成授权' }}
                  </p>
                </div>
              </div>
            </div>

            <div class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
              <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 class="text-base font-black text-slate-950 dark:text-white">3. 广告账户绑定</h2>
                  <p class="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
                    创建计划前必须选择一个已授权广告账户。账户资产完整度会在真实发布前继续校验。
                  </p>
                </div>
                <button
                  class="whitespace-nowrap rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  :disabled="syncingAccounts"
                  @click="handleSyncAccounts"
                >
                  {{ syncingAccounts ? '同步中' : '同步账户' }}
                </button>
              </div>

              <div v-if="!activeMetaConnection && !usingDemoAccount" class="mt-5 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                未检测到真实 Meta 授权。你可以先点击“同步账户”启用 Demo 广告账户测试创建草稿流程。
              </div>
              <div v-else-if="accountApiUnavailable && accounts.length === 0" class="mt-5 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                广告账户列表接口暂不可用。已使用 Demo 广告账户继续流程，真实账户需要后端补齐 `GET /platform-accounts?platform=meta&status=active`。
              </div>
              <div v-else-if="accounts.length === 0" class="mt-5 rounded-md border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
                暂无可用广告账户。请先同步账户，或检查 Meta 授权范围。
              </div>
              <div v-else class="mt-5 grid gap-3 md:grid-cols-[1fr_auto]">
                <select
                  v-model="selectedAccountId"
                  class="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
                >
                  <option v-for="account in accounts" :key="account.id" :value="account.id">
                    {{ account.account_name }} · {{ account.account_id }}
                  </option>
                </select>
                <button
                  class="whitespace-nowrap rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40 dark:bg-white dark:text-slate-950"
                  :disabled="!selectedProject || !selectedAccount || bindingAccount"
                  @click="handleBindAccount"
                >
                  {{ bindingAccount ? '绑定中' : '绑定到账户' }}
                </button>
              </div>
            </div>

            <div class="grid gap-5 lg:grid-cols-2">
              <div class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
                <h2 class="text-base font-black text-slate-950 dark:text-white">4. 投放前置资产</h2>
                <div class="mt-4 space-y-3">
                  <div class="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm dark:bg-slate-900">
                    <span>广告账户授权</span>
                    <span class="font-bold text-emerald-600">{{ selectedAccount ? '已完成' : '待完成' }}</span>
                  </div>
                  <div class="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm dark:bg-slate-900">
                    <span>Page / IG / Pixel / App</span>
                    <span class="font-bold text-amber-600">发布前检查</span>
                  </div>
                </div>
              </div>

              <div class="rounded-md border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950">
                <h2 class="text-base font-black text-slate-950 dark:text-white">5. 素材准备</h2>
                <p class="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
                  可以先创建投放草稿。提交发布前需要补齐素材文件、文案、链接和 CTA。
                </p>
                <button
                  class="mt-4 whitespace-nowrap rounded-md border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
                  @click="goMaterials"
                >
                  去素材库
                </button>
              </div>
            </div>

            <div class="rounded-md border border-slate-200 bg-slate-950 p-4 text-white">
              <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 class="text-base font-black">6. 创建第一条广告计划草稿</h2>
                  <p class="mt-1 text-xs leading-5 text-slate-300">
                    草稿会带入当前项目、Meta 平台和广告账户。真实发布任务等后端接口补齐后再开放。
                  </p>
                </div>
                <button
                  class="whitespace-nowrap rounded-md bg-white px-5 py-2.5 text-sm font-bold text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
                  :disabled="!canCreateCampaign"
                  @click="goCreateCampaign"
                >
                  创建计划
                </button>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
    <ChatPanel
      :session-id="workspaceSessions.activeSessionId.value"
      :quick-hints="['继续配置广告账户', '解释这 6 步需要做什么', '帮我创建第一条计划草稿']"
    />
  </div>
</template>
