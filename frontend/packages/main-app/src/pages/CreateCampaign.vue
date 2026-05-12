<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import SelectGroupModal from '@/components/campaigns/SelectGroupModal.vue'
import SelectMaterialModal from '@/components/campaigns/SelectMaterialModal.vue'
import { getProjectCampaigns, getProjectDetail, getProjectPlatformAccounts, type Project } from '@/api/projects'
import { batchCreateProjectCampaigns, type CampaignMaterialBindingInput } from '@/api/campaigns'
import { type Material, getMaterialImage } from '@/api/materials'
import { getPlatformAccounts, type PlatformAccount } from '@/api/platformAccounts'

const router = useRouter()
const route = useRoute()

const projectId = ref(route.query.projectId as string || '')

const currentStep = ref(1)
const totalSteps = 4
const contentScrollRef = ref<HTMLElement | null>(null)

// 导航配置
const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
  { id: 'accounts', icon: 'account_balance_wallet', label: '广告账户', path: '/platform-accounts' },
  { id: 'materials', icon: 'video_library', label: '创意素材', path: '/material' },
  { id: 'reports', icon: 'bar_chart', label: '数据报表', path: '/monitor' },
]

const switchPanel = (item: any) => {
  if (item.path) {
    router.push(item.path)
  }
}

const steps = [
  { id: 1, name: '准备', icon: 'settings', description: '选择分组和平台' },
  { id: 2, name: '创建', icon: 'edit', description: '设置广告目标' },
  { id: 3, name: '执行', icon: 'rocket_launch', description: '选择素材和定向' },
  { id: 4, name: '确认', icon: 'check_circle', description: '确认并提交' }
]

// 准备阶段数据
const selectedGroup = ref<Project | null>(null)
const projectCampaigns = ref<any[]>([])
const selectedPlatform = ref('')
const platformAccounts = ref<PlatformAccount[]>([])
const projectPlatformAccounts = ref<PlatformAccount[]>([])
const selectedPlatformAccountId = ref('')
const showGroupModal = ref(false)
const showMaterialModal = ref(false)
const platforms = [
  { id: 'Meta', name: 'Meta Ads', icon: 'f', description: 'Facebook/Instagram 广告', available: true },
  { id: 'Google', name: 'Google Ads', icon: 'G', description: '待接入：搜索广告、展示广告、应用广告', available: false },
  { id: 'TikTok', name: 'TikTok Ads', icon: '♪', description: '待接入：信息流广告、开屏广告、挑战赛', available: false }
]

const accountChecks = [
  { id: 'account', label: '广告账户已开户', checked: true },
  { id: 'conversion', label: '转化像素已配置', checked: true },
  { id: 'app', label: '应用已绑定', checked: true },
  { id: 'payment', label: '支付方式已设置', checked: true }
]

const availablePlatformAccounts = computed(() => {
  const platform = selectedPlatform.value.toLowerCase()
  const scopedAccounts = projectPlatformAccounts.value.length > 0
    ? projectPlatformAccounts.value
    : platformAccounts.value
  return scopedAccounts.filter(account =>
    account.platform === platform &&
    account.status === 'active' &&
    account.has_token
  )
})

// 创建阶段数据
const campaignObjective = ref('install')
const objectives = [
  { id: 'install', name: '应用安装', description: '增加应用下载量', icon: 'download' },
  { id: 'conversion', name: '转化率', description: '优化应用内转化', icon: 'shopping_cart' },
  { id: 'engagement', name: '品牌曝光', description: '提升品牌知名度', icon: 'visibility' },
  { id: 'retention', name: '用户留存', description: '提升用户活跃度', icon: 'group' }
]

const budgetType = ref('daily')
const campaignBudget = ref(10000)

const biddingStrategy = ref('auto')
const biddingStrategies = [
  { id: 'auto', name: '自动出价', description: '系统自动优化，获取最多转化' },
  { id: 'target_cpa', name: '目标CPA', description: '以目标单次转化成本优化' },
  { id: 'target_roas', name: '目标ROAS', description: '以目标回报率优化投放' },
  { id: 'manual', name: '手动出价', description: '完全控制每次出价上限' }
]

const targetCPA = ref(8.0)
const startDate = ref('')
const endDate = ref('')

const formatMoney = (value?: number) => `$${Math.round(value || 0).toLocaleString()}`

const flightDays = computed(() => {
  if (!startDate.value || !endDate.value) return 0
  const start = new Date(startDate.value)
  const end = new Date(endDate.value)
  const diff = Math.floor((end.getTime() - start.getTime()) / 86400000) + 1
  return Number.isFinite(diff) ? Math.max(diff, 0) : 0
})

const allocatedBudget = computed(() => {
  return projectCampaigns.value.reduce((sum, campaign) => sum + (campaign.budget || 0), 0)
})

const projectSpent = computed(() => selectedGroup.value?.spent || 0)
const projectTotalBudget = computed(() => selectedGroup.value?.total_budget || 0)
const projectUnallocatedBudget = computed(() => Math.max(projectTotalBudget.value - allocatedBudget.value, 0))
const projectRemainingCash = computed(() => Math.max(projectTotalBudget.value - projectSpent.value, 0))
const projectedTotalBudget = computed(() => {
  if (budgetType.value === 'daily' && flightDays.value > 0) {
    return campaignBudget.value * flightDays.value
  }
  return campaignBudget.value
})

const budgetErrors = computed(() => {
  const errors: string[] = []
  if (campaignBudget.value <= 0) errors.push('请输入大于 0 的预算')
  if (!startDate.value || !endDate.value) errors.push('请选择完整投放时间')
  if (startDate.value && endDate.value && flightDays.value <= 0) errors.push('结束日期不能早于开始日期')
  if (projectTotalBudget.value > 0 && projectedTotalBudget.value > projectUnallocatedBudget.value) {
    errors.push(`计划预算超出项目未分配预算，可用额度 ${formatMoney(projectUnallocatedBudget.value)}`)
  }
  if (projectRemainingCash.value > 0 && projectedTotalBudget.value > projectRemainingCash.value) {
    errors.push(`计划预算高于项目现金剩余额度 ${formatMoney(projectRemainingCash.value)}`)
  }
  return errors
})

const budgetPacingHint = computed(() => {
  if (!flightDays.value || !projectTotalBudget.value) return '选择时间后可计算预算节奏'
  const daily = budgetType.value === 'daily' ? campaignBudget.value : projectedTotalBudget.value / flightDays.value
  const remainingDays = Math.max(flightDays.value, 1)
  const projectDailyCapacity = projectRemainingCash.value / remainingDays
  if (daily > projectDailyCapacity * 1.2) return '日消耗目标高于项目剩余额度节奏，建议降低预算或缩短投放目标'
  if (daily < projectDailyCapacity * 0.35) return '日消耗目标偏保守，若素材表现达标可预留自动加预算空间'
  return '预算节奏与项目剩余额度匹配'
})

const loadProjectCampaigns = async (projectId: string) => {
  try {
    projectCampaigns.value = await getProjectCampaigns(projectId)
  } catch (err) {
    console.error('加载项目广告计划失败:', err)
    projectCampaigns.value = []
  }
}

const loadProjectPlatformAccounts = async (projectId: string) => {
  try {
    const links = await getProjectPlatformAccounts(projectId)
    projectPlatformAccounts.value = links
      .map(link => link.account)
      .filter(Boolean) as PlatformAccount[]
  } catch (err) {
    console.error('加载项目绑定广告账户失败:', err)
    projectPlatformAccounts.value = []
  }
}

const loadPlatformAccounts = async () => {
  try {
    platformAccounts.value = await getPlatformAccounts()
  } catch (err) {
    console.error('加载平台账户失败:', err)
  }
}

// 执行阶段数据
const selectedMaterials = ref<Material[]>([])
const materialThumbnails = ref<Record<string, string>>({})
const materialBindingDrafts = ref<Record<string, {
  title: string
  description: string
  copy: string
}>>({})

const removeMaterial = (materialId: string) => {
  const index = selectedMaterials.value.findIndex(m => m.id === materialId)
  if (index > -1) {
    selectedMaterials.value.splice(index, 1)
    delete materialBindingDrafts.value[materialId]
  }
}

const ensureMaterialBindingDraft = (material: Material) => {
  if (!materialBindingDrafts.value[material.id]) {
    materialBindingDrafts.value[material.id] = {
      title: material.name || '素材标题',
      description: `用于 ${selectedGroup.value?.target_market || '目标市场'} 的投放素材`,
      copy: '',
    }
  }
}

const buildMaterialBindings = (): CampaignMaterialBindingInput[] => {
  return selectedMaterials.value.map((material, index) => {
    ensureMaterialBindingDraft(material)
    const draft = materialBindingDrafts.value[material.id]
    return {
      material_id: material.id,
      title: draft.title,
      description: draft.description,
      copy: draft.copy,
      source: 'manual',
      sort_order: index + 1,
      status: 'ready',
    }
  })
}

// 加载素材缩略图
const loadMaterialThumbnails = async (materials: Material[]) => {
  for (const material of materials) {
    if (!materialThumbnails.value[material.id]) {
      try {
        const imageData = await getMaterialImage(material.id, true)
        materialThumbnails.value[material.id] = imageData.data
      } catch (err) {
        console.error(`加载素材${material.id}缩略图失败:`, err)
      }
    }
  }
}

// 监听selectedMaterials变化，自动加载缩略图
watch(selectedMaterials, (newMaterials) => {
  if (newMaterials.length > 0) {
    loadMaterialThumbnails(newMaterials)
  }
}, { deep: true })

const targetRegions = ref<string[]>([])
const regions = ['美国', '英国', '加拿大', '澳洲', '日本', '韩国', '新加坡', '泰国', '印度', '巴西']

const ageRange = ref({ min: 18, max: 65 })
const gender = ref('all')

const targetInterests = ref<string[]>([])
const interests = ['游戏', '短视频', '电商购物', '社交媒体', '音乐', '电影', '旅行', '科技数码', '时尚美妆', '烹饪美食', '教育']

// 验证逻辑
const canProceedStep1 = computed(() => {
  if (!selectedGroup.value || !selectedPlatform.value) return false
  const platform = platforms.find(item => item.id === selectedPlatform.value)
  if (!platform?.available) return false
  if (selectedPlatform.value === 'Meta') {
    return Boolean(selectedPlatformAccountId.value)
  }
  return true
})

const canProceedStep2 = computed(() => {
  return campaignObjective.value !== '' && budgetErrors.value.length === 0
})

const canProceedStep3 = computed(() => {
  return selectedMaterials.value.length > 0
})

const canProceed = computed(() => {
  if (currentStep.value === 1) return canProceedStep1.value
  if (currentStep.value === 2) return canProceedStep2.value
  if (currentStep.value === 3) return canProceedStep3.value
  return true
})

const scrollStepToTop = () => {
  requestAnimationFrame(() => {
    contentScrollRef.value?.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

const nextStep = () => {
  if (currentStep.value < totalSteps && canProceed.value) {
    currentStep.value++
    scrollStepToTop()
  }
}

const prevStep = () => {
  if (currentStep.value > 1) {
    currentStep.value--
    scrollStepToTop()
  }
}

const toggleRegion = (region: string) => {
  const index = targetRegions.value.indexOf(region)
  if (index > -1) {
    targetRegions.value.splice(index, 1)
  } else {
    targetRegions.value.push(region)
  }
}

const toggleInterest = (interest: string) => {
  const index = targetInterests.value.indexOf(interest)
  if (index > -1) {
    targetInterests.value.splice(index, 1)
  } else {
    targetInterests.value.push(interest)
  }
}

const submitting = ref(false)

const handleSubmit = async () => {
  if (!selectedGroup.value) {
    alert('请选择所属分组')
    return
  }
  
  if (!selectedPlatform.value) {
    alert('请选择投放平台')
    return
  }

  const selectedPlatformConfig = platforms.find(platform => platform.id === selectedPlatform.value)
  if (!selectedPlatformConfig?.available) {
    alert('当前版本仅开放 Meta Campaign 创建链路')
    return
  }
  
  submitting.value = true
  
  try {
    if (budgetErrors.value.length > 0) {
      alert(budgetErrors.value[0])
      return
    }

    // 构建广告计划名称
    const campaignName = `${selectedGroup.value.name} - ${platforms.find(p => p.id === selectedPlatform.value)?.name}`

    if (selectedPlatform.value === 'Meta' && !selectedPlatformAccountId.value) {
      alert('请选择 Meta 广告账户')
      return
    }

    const result = await batchCreateProjectCampaigns(selectedGroup.value.id, {
      plan_count: 1,
      name_template: campaignName,
      platform: selectedPlatform.value,
      platform_account_id: selectedPlatformAccountId.value || undefined,
      objective: campaignObjective.value === 'engagement' ? 'OUTCOME_AWARENESS' : 'OUTCOME_TRAFFIC',
      budget: projectedTotalBudget.value,
      budget_type: budgetType.value as 'daily' | 'total',
      status: 'draft',
      bidding_strategy: biddingStrategy.value,
      target_cpa: biddingStrategy.value === 'target_cpa' ? targetCPA.value : undefined,
      start_date: startDate.value,
      end_date: endDate.value,
      targeting: {
        regions: targetRegions.value,
        age_range: ageRange.value,
        gender: gender.value,
        interests: targetInterests.value,
      },
      materials: buildMaterialBindings(),
      auto_optimize_enabled: true,
    })
    
    console.log('广告计划创建成功:', result)
    
    // 跳转回项目详情页
    router.push(`/projects/${selectedGroup.value.id}`)
  } catch (err: any) {
    console.error('创建广告计划失败:', err)
    alert(err.message || '创建广告计划失败，请重试')
  } finally {
    submitting.value = false
  }
}

const handleBack = () => {
  router.back()
}

const handleOpenGroupModal = () => {
  showGroupModal.value = true
}

const handleCloseGroupModal = () => {
  showGroupModal.value = false
}

const handleSelectGroup = (project: Project) => {
  selectedGroup.value = project
  loadProjectCampaigns(project.id)
  loadProjectPlatformAccounts(project.id)
  selectedPlatformAccountId.value = ''
  console.log('选择分组:', project)
}

const handleOpenMaterialModal = () => {
  showMaterialModal.value = true
}

const handleCloseMaterialModal = () => {
  showMaterialModal.value = false
}

const handleSelectMaterials = (materials: Material[]) => {
  selectedMaterials.value = materials
  materials.forEach(ensureMaterialBindingDraft)
  console.log('选择素材:', materials)
  // 关闭弹窗后自动关闭
  showMaterialModal.value = false
}

// 页面加载时，如果有projectId参数，自动加载该项目作为默认分组
onMounted(async () => {
  await loadPlatformAccounts()
  if (projectId.value) {
    try {
      const project = await getProjectDetail(projectId.value)
      selectedGroup.value = project
      await loadProjectCampaigns(project.id)
      await loadProjectPlatformAccounts(project.id)
      console.log('自动设置默认分组:', project.name)
    } catch (err) {
      console.error('加载项目详情失败:', err)
    }
  }
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <!-- 左侧导航栏 -->
    <SidebarNav
      :nav-items="navItems"
      active-id="campaigns"
      @switch-panel="switchPanel"
    />

    <!-- 主内容区 -->
    <div class="flex-1 flex flex-col bg-slate-50 dark:bg-slate-950 overflow-hidden">
      <!-- Header -->
      <div class="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
      <div class="max-w-7xl mx-auto px-6 py-4">
        <div class="flex items-center gap-4">
          <button
            @click="handleBack"
            class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">arrow_back</span>
          </button>
          <h1 class="text-xl font-bold text-slate-900 dark:text-white">新建计划</h1>
          </div>
        </div>
      </div>

      <!-- Steps Navigation -->
    <div class="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
      <div class="max-w-7xl mx-auto px-6 py-6">
        <div class="flex items-center justify-between">
          <div
            v-for="(step, index) in steps"
            :key="step.id"
            class="flex items-center flex-1"
          >
            <!-- Step Circle -->
            <div class="flex flex-col items-center">
              <div
                class="w-12 h-12 rounded-full flex items-center justify-center transition-all"
                :class="currentStep >= step.id 
                  ? 'bg-primary text-white' 
                  : 'bg-slate-200 dark:bg-slate-700 text-slate-400'"
              >
                <span class="material-symbols-outlined">{{ step.icon }}</span>
              </div>
              <div class="mt-2 text-center">
                <div
                  class="text-sm font-medium"
                  :class="currentStep >= step.id 
                    ? 'text-primary' 
                    : 'text-slate-400'"
                >
                  {{ step.name }}
                </div>
              </div>
            </div>

            <!-- Connector Line -->
            <div
              v-if="index < steps.length - 1"
              class="flex-1 h-0.5 mx-4 transition-all"
              :class="currentStep > step.id 
                ? 'bg-primary' 
                : 'bg-slate-200 dark:bg-slate-700'"
            ></div>
          </div>
        </div>
      </div>
    </div>

      <!-- Content -->
      <div ref="contentScrollRef" class="flex-1 overflow-y-auto">
        <div class="max-w-7xl mx-auto px-6 py-8">
      <!-- Step 1: 准备 -->
      <div v-if="currentStep === 1" class="space-y-6">
        <!-- 选择所属分组 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">folder</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">选择所属项目</h3>
          </div>
          <button
            class="w-full px-4 py-3 rounded-md border-2 border-dashed transition-colors text-left"
            :class="selectedGroup 
              ? 'border-primary bg-primary/5 text-slate-900 dark:text-white' 
              : 'border-primary/30 text-primary hover:bg-primary/5'"
            @click="handleOpenGroupModal"
          >
            <div v-if="selectedGroup">
              <div class="font-semibold">{{ selectedGroup.name }}</div>
              <div class="text-sm text-slate-500 dark:text-slate-400 mt-1">
                {{ selectedGroup.game_type }} · 总预算 {{ formatMoney(selectedGroup.total_budget) }} · 已消耗 {{ formatMoney(selectedGroup.spent) }}
              </div>
            </div>
            <div v-else class="text-center text-primary">
              请选择分组
            </div>
          </button>
          <div v-if="selectedGroup" class="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
            <div class="rounded-md bg-slate-50 dark:bg-slate-800 px-3 py-2">
              <div class="text-xs text-slate-500 dark:text-slate-400">项目总预算</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(projectTotalBudget) }}</div>
            </div>
            <div class="rounded-md bg-slate-50 dark:bg-slate-800 px-3 py-2">
              <div class="text-xs text-slate-500 dark:text-slate-400">已分配计划</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(allocatedBudget) }}</div>
            </div>
            <div class="rounded-md bg-slate-50 dark:bg-slate-800 px-3 py-2">
              <div class="text-xs text-slate-500 dark:text-slate-400">未分配额度</div>
              <div class="text-sm font-semibold text-emerald-600">{{ formatMoney(projectUnallocatedBudget) }}</div>
            </div>
            <div class="rounded-md bg-slate-50 dark:bg-slate-800 px-3 py-2">
              <div class="text-xs text-slate-500 dark:text-slate-400">现金剩余额度</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(projectRemainingCash) }}</div>
            </div>
          </div>
        </div>

        <!-- 投放平台 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">ads_click</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">投放平台</h3>
          </div>
          <div class="grid gap-4">
            <div
              v-for="platform in platforms"
              :key="platform.id"
              class="p-4 rounded-lg border-2 transition-all"
              :class="[
                selectedPlatform === platform.id 
                  ? 'border-primary bg-primary/5' 
                  : 'border-slate-200 dark:border-slate-700',
                platform.available
                  ? 'cursor-pointer hover:border-primary/50'
                  : 'cursor-not-allowed opacity-60 bg-slate-50 dark:bg-slate-900/40'
              ]"
              @click="platform.available && (selectedPlatform = platform.id)"
            >
              <div class="flex items-center gap-4">
                <div class="w-12 h-12 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-xl font-bold">
                  {{ platform.icon }}
                </div>
                <div class="flex-1">
                  <div class="flex items-center gap-2">
                    <div class="font-semibold text-slate-900 dark:text-white">{{ platform.name }}</div>
                    <span v-if="!platform.available" class="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500">待接入</span>
                  </div>
                  <div class="text-sm text-slate-500 dark:text-slate-400">{{ platform.description }}</div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="selectedPlatform === 'Meta'" class="mt-5 rounded-md border border-slate-200 dark:border-slate-700 p-4">
            <div class="flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-slate-200">
              <span class="material-symbols-outlined text-primary text-base">verified_user</span>
              Meta 计划将直接创建到真实广告账户
            </div>
            <div class="mt-3">
              <select v-model="selectedPlatformAccountId" class="w-full px-3 py-2 rounded-md border text-sm">
                <option value="">选择 Meta 广告账户</option>
                <option v-for="account in availablePlatformAccounts" :key="account.id" :value="account.id">
                  {{ account.account_name }} · {{ account.account_id }}
                </option>
              </select>
              <div v-if="availablePlatformAccounts.length === 0" class="mt-2 text-xs text-amber-600">
                该项目暂无可用 Meta 账户，请先在项目详情绑定广告账户，或到“设置 / 平台连接”完成授权。
              </div>
              <div v-else-if="projectPlatformAccounts.length === 0" class="mt-2 text-xs text-slate-500">
                当前项目尚未绑定账户，已临时显示全部可用 Meta 账户。创建成功后系统会自动绑定该账户。
              </div>
            </div>
          </div>
        </div>

        <!-- 账户环境检查 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">verified</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">账户环境检查</h3>
          </div>
          <div class="space-y-3">
            <div
              v-for="check in accountChecks"
              :key="check.id"
              class="flex items-center gap-3"
            >
              <span
                class="material-symbols-outlined text-emerald-500"
                :class="check.checked ? 'text-emerald-500' : 'text-slate-300'"
              >
                {{ check.checked ? 'check_circle' : 'radio_button_unchecked' }}
              </span>
              <span class="text-sm text-slate-700 dark:text-slate-300">{{ check.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Step 2: 创建 -->
      <div v-if="currentStep === 2" class="space-y-6">
        <!-- 推广目标 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">flag</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">推广目标</h3>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div
              v-for="objective in objectives"
              :key="objective.id"
              class="p-4 rounded-lg border-2 transition-all cursor-pointer"
              :class="campaignObjective === objective.id 
                ? 'border-primary bg-primary/5' 
                : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
              @click="campaignObjective = objective.id"
            >
              <div class="flex flex-col items-center text-center gap-2">
                <span class="material-symbols-outlined text-3xl" :class="campaignObjective === objective.id ? 'text-primary' : 'text-slate-400'">
                  {{ objective.icon }}
                </span>
                <div class="font-semibold text-slate-900 dark:text-white">{{ objective.name }}</div>
                <div class="text-xs text-slate-500 dark:text-slate-400">{{ objective.description }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 预算设置 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">account_balance_wallet</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">预算设置</h3>
          </div>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">预算类型</label>
              <select
                v-model="budgetType"
                class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              >
                <option value="daily">日预算</option>
                <option value="total">总预算</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">
                {{ budgetType === 'daily' ? '日预算金额 ($)' : '总预算金额 ($)' }}
              </label>
              <input
                v-model.number="campaignBudget"
                type="number"
                min="0"
                step="100"
                placeholder="例如: 10000"
                class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              />
            </div>
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
              <div class="rounded-md bg-slate-50 dark:bg-slate-800 px-3 py-2">
                <div class="text-xs text-slate-500 dark:text-slate-400">预计计划总预算</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ formatMoney(projectedTotalBudget) }}</div>
              </div>
              <div class="rounded-md bg-slate-50 dark:bg-slate-800 px-3 py-2">
                <div class="text-xs text-slate-500 dark:text-slate-400">投放天数</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white">{{ flightDays || '-' }} 天</div>
              </div>
              <div class="rounded-md bg-slate-50 dark:bg-slate-800 px-3 py-2">
                <div class="text-xs text-slate-500 dark:text-slate-400">未分配额度</div>
                <div class="text-sm font-semibold text-emerald-600">{{ formatMoney(projectUnallocatedBudget) }}</div>
              </div>
              <div class="rounded-md bg-slate-50 dark:bg-slate-800 px-3 py-2">
                <div class="text-xs text-slate-500 dark:text-slate-400">预算节奏</div>
                <div class="text-sm font-semibold text-slate-900 dark:text-white truncate">{{ budgetPacingHint }}</div>
              </div>
            </div>
            <div
              v-if="budgetErrors.length > 0"
              class="rounded-md border border-red-200 dark:border-red-900/50 bg-red-50 dark:bg-red-900/20 px-3 py-2"
            >
              <div v-for="item in budgetErrors" :key="item" class="flex items-center gap-2 text-sm text-red-600 dark:text-red-300">
                <span class="material-symbols-outlined text-base">error</span>
                <span>{{ item }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 出价策略 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">trending_up</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">出价策略</h3>
          </div>
          <div class="grid grid-cols-2 gap-4 mb-4">
            <div
              v-for="strategy in biddingStrategies"
              :key="strategy.id"
              class="p-4 rounded-lg border-2 transition-all cursor-pointer"
              :class="biddingStrategy === strategy.id 
                ? 'border-primary bg-primary/5' 
                : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
              @click="biddingStrategy = strategy.id"
            >
              <div class="font-semibold text-slate-900 dark:text-white mb-1">{{ strategy.name }}</div>
              <div class="text-xs text-slate-500 dark:text-slate-400">{{ strategy.description }}</div>
            </div>
          </div>
          <div v-if="biddingStrategy === 'target_cpa'">
            <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">目标CPA ($)</label>
            <input
              v-model.number="targetCPA"
              type="number"
              min="0"
              step="0.1"
              placeholder="例如: 8.0"
              class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
            />
          </div>
        </div>

        <!-- 投放时间 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">schedule</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">投放时间</h3>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">开始日期</label>
              <input
                v-model="startDate"
                type="date"
                class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">结束日期</label>
              <input
                v-model="endDate"
                type="date"
                class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Step 3: 执行 -->
      <div v-if="currentStep === 3" class="space-y-6">
        <!-- 选择素材 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">video_library</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">选择素材</h3>
            <span class="text-sm text-slate-500 dark:text-slate-400">选择需要投放的创意素材，可多选</span>
          </div>
          
          <!-- 已选择的素材列表 -->
          <div v-if="selectedMaterials.length > 0" class="grid grid-cols-2 gap-4 mb-4">
            <div
              v-for="material in selectedMaterials"
              :key="material.id"
              class="p-4 rounded-lg border-2 border-primary bg-primary/5 relative"
            >
              <div class="flex items-center gap-3">
                <div class="w-16 h-16 rounded-md bg-slate-100 dark:bg-slate-800 flex items-center justify-center overflow-hidden">
                  <img
                    v-if="materialThumbnails[material.id]"
                    :src="materialThumbnails[material.id]"
                    :alt="material.name"
                    class="w-full h-full object-cover"
                  />
                  <span v-else class="material-symbols-outlined text-2xl text-slate-400">
                    {{ material.type === 'video' ? 'videocam' : 'image' }}
                  </span>
                </div>
                <div class="flex-1">
                  <div class="font-medium text-slate-900 dark:text-white text-sm mb-1">{{ material.name }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">
                    {{ material.type === 'video' ? '视频' : '图片' }} · CTR {{ material.ctr_estimate || 0 }}%
                  </div>
                </div>
              </div>
              <div class="mt-4 space-y-3">
                <div>
                  <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">计划内素材标题</label>
                  <input
                    v-model="materialBindingDrafts[material.id].title"
                    type="text"
                    maxlength="120"
                    class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white"
                  />
                </div>
                <div>
                  <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">计划内素材描述</label>
                  <textarea
                    v-model="materialBindingDrafts[material.id].description"
                    rows="2"
                    maxlength="500"
                    class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white resize-none"
                  ></textarea>
                </div>
                <div>
                  <label class="block text-xs font-medium text-slate-600 dark:text-slate-300 mb-1">投放文案</label>
                  <textarea
                    v-model="materialBindingDrafts[material.id].copy"
                    rows="2"
                    maxlength="1000"
                    class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-sm text-slate-900 dark:text-white resize-none"
                  ></textarea>
                </div>
              </div>
              <!-- 移除按钮 -->
              <button
                @click="removeMaterial(material.id)"
                class="absolute top-2 right-2 w-6 h-6 rounded-full bg-slate-200 dark:bg-slate-700 hover:bg-red-500 hover:text-white transition-colors flex items-center justify-center"
              >
                <span class="material-symbols-outlined text-sm">close</span>
              </button>
            </div>
          </div>
          
          <!-- 添加素材按钮 -->
          <button
            @click="handleOpenMaterialModal"
            class="w-full px-4 py-3 rounded-md border-2 border-dashed border-primary/30 text-primary hover:bg-primary/5 transition-colors flex items-center justify-center gap-2"
          >
            <span class="material-symbols-outlined">add_circle</span>
            <span>添加素材</span>
          </button>
        </div>

        <!-- 定向配置 - 投放地区 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">public</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">定向配置 — 投放地区</h3>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="region in regions"
              :key="region"
              class="px-4 py-2 rounded-full text-sm transition-all"
              :class="targetRegions.includes(region) 
                ? 'bg-primary text-white' 
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'"
              @click="toggleRegion(region)"
            >
              {{ region }}
            </button>
          </div>
        </div>

        <!-- 定向配置 - 受众人群 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">group</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">定向配置 — 受众人群</h3>
          </div>
          <div class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">性别</label>
              <select
                v-model="gender"
                class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              >
                <option value="all">不限</option>
                <option value="male">男性</option>
                <option value="female">女性</option>
              </select>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">最小年龄</label>
                <input
                  v-model.number="ageRange.min"
                  type="number"
                  min="13"
                  max="100"
                  class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">最大年龄</label>
                <input
                  v-model.number="ageRange.max"
                  type="number"
                  min="13"
                  max="100"
                  class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- 定向配置 - 兴趣标签 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">label</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">定向配置 — 兴趣标签</h3>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              v-for="interest in interests"
              :key="interest"
              class="px-4 py-2 rounded-full text-sm transition-all"
              :class="targetInterests.includes(interest) 
                ? 'bg-primary text-white' 
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'"
              @click="toggleInterest(interest)"
            >
              {{ interest }}
            </button>
          </div>
        </div>
      </div>

      <!-- Step 4: 确认 -->
      <div v-if="currentStep === 4" class="space-y-6">
        <!-- 准备阶段 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">settings</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">准备阶段</h3>
          </div>
          <div class="grid grid-cols-3 gap-4 text-sm">
            <div>
              <div class="text-slate-500 dark:text-slate-400 mb-1">所属分组</div>
              <div class="font-medium text-slate-900 dark:text-white">{{ selectedGroup?.name || '-' }}</div>
            </div>
            <div>
              <div class="text-slate-500 dark:text-slate-400 mb-1">投放平台</div>
              <div class="font-medium text-slate-900 dark:text-white">
                {{ platforms.find(p => p.id === selectedPlatform)?.name || '-' }}
              </div>
            </div>
            <div>
              <div class="text-slate-500 dark:text-slate-400 mb-1">账户状态</div>
              <div class="flex items-center gap-1" :class="selectedPlatform === 'Meta' ? 'text-blue-600' : 'text-emerald-600'">
                <span class="material-symbols-outlined text-sm">check_circle</span>
                <span class="font-medium">
                  {{ selectedPlatform === 'Meta' ? '将创建到 Meta' : '本地草稿' }}
                </span>
              </div>
            </div>
            <div v-if="selectedPlatform === 'Meta'">
              <div class="text-slate-500 dark:text-slate-400 mb-1">Meta 账户</div>
              <div class="font-medium text-slate-900 dark:text-white">
                {{ availablePlatformAccounts.find(a => a.id === selectedPlatformAccountId)?.account_name || '-' }}
              </div>
            </div>
          </div>
        </div>

        <!-- 创建阶段 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">edit</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">创建阶段</h3>
          </div>
          <div class="space-y-3 text-sm">
            <div class="flex justify-between">
              <span class="text-slate-500 dark:text-slate-400">推广目标</span>
              <span class="font-medium text-slate-900 dark:text-white">
                {{ objectives.find(o => o.id === campaignObjective)?.name || '-' }}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500 dark:text-slate-400">预算</span>
              <span class="font-medium text-slate-900 dark:text-white">
                {{ budgetType === 'daily' ? '日预算' : '总预算' }} {{ formatMoney(campaignBudget) }}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500 dark:text-slate-400">计划占用预算</span>
              <span class="font-medium text-slate-900 dark:text-white">{{ formatMoney(projectedTotalBudget) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500 dark:text-slate-400">项目未分配额度</span>
              <span class="font-medium text-slate-900 dark:text-white">{{ formatMoney(projectUnallocatedBudget) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500 dark:text-slate-400">出价策略</span>
              <span class="font-medium text-slate-900 dark:text-white">
                {{ biddingStrategies.find(s => s.id === biddingStrategy)?.name || '-' }}
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500 dark:text-slate-400">投放时间</span>
              <span class="font-medium text-slate-900 dark:text-white">
                {{ startDate || '/' }} - {{ endDate || '/' }}
              </span>
            </div>
          </div>
        </div>

        <!-- 执行阶段 -->
        <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary">rocket_launch</span>
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white">执行阶段</h3>
          </div>
          <div class="space-y-3 text-sm">
            <div>
              <div class="text-slate-500 dark:text-slate-400 mb-2">选择素材</div>
              <div class="font-medium text-slate-900 dark:text-white">
                {{ selectedMaterials.length }} 个素材
              </div>
              <div class="mt-2 space-y-2">
                <div
                  v-for="material in selectedMaterials"
                  :key="material.id"
                  class="rounded-md bg-slate-50 dark:bg-slate-800 px-3 py-2"
                >
                  <div class="font-medium text-slate-900 dark:text-white">{{ materialBindingDrafts[material.id]?.title || material.name }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {{ materialBindingDrafts[material.id]?.description || '未填写描述' }}
                  </div>
                </div>
              </div>
            </div>
            <div>
              <div class="text-slate-500 dark:text-slate-400 mb-2">投放地区</div>
              <div class="font-medium text-slate-900 dark:text-white">
                {{ targetRegions.length > 0 ? targetRegions.join('、') : '不限' }}
              </div>
            </div>
            <div>
              <div class="text-slate-500 dark:text-slate-400 mb-2">受众范围</div>
              <div class="font-medium text-slate-900 dark:text-white">
                {{ ageRange.min }} - {{ ageRange.max }} 岁 · {{ gender === 'all' ? '不限' : gender === 'male' ? '男性' : '女性' }}
              </div>
            </div>
            <div>
              <div class="text-slate-500 dark:text-slate-400 mb-2">兴趣标签</div>
              <div class="font-medium text-slate-900 dark:text-white">
                {{ targetInterests.length > 0 ? targetInterests.join('、') : '不限' }}
              </div>
            </div>
          </div>
        </div>
      </div>

        <!-- Navigation Buttons -->
        <div class="flex items-center justify-between pt-6">
        <button
          v-if="currentStep > 1"
          @click="prevStep"
          class="flex items-center gap-2 px-6 py-2 rounded-md border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
        >
          <span class="material-symbols-outlined text-sm">arrow_back</span>
          <span>上一步</span>
        </button>
        <div v-else></div>

        <button
          v-if="currentStep < totalSteps"
          @click="nextStep"
          :disabled="!canProceed"
          class="flex items-center gap-2 px-6 py-2 rounded-md transition-colors ml-auto"
          :class="canProceed 
            ? 'bg-primary text-white hover:bg-primary/90 cursor-pointer' 
            : 'bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed'"
        >
          <span>下一步</span>
          <span class="material-symbols-outlined text-sm">arrow_forward</span>
        </button>
        <button
          v-else
          @click="handleSubmit"
          :disabled="submitting"
          class="flex items-center gap-2 px-6 py-2 rounded-md transition-colors ml-auto"
          :class="submitting 
            ? 'bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 cursor-not-allowed' 
            : 'bg-primary text-white hover:bg-primary/90 cursor-pointer'"
        >
          <span v-if="submitting" class="material-symbols-outlined text-sm animate-spin">progress_activity</span>
          <span v-else class="material-symbols-outlined text-sm">check</span>
          <span>{{ submitting ? '创建中...' : '提交创建' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 选择分组弹窗 -->
    <SelectGroupModal
      :show="showGroupModal"
      @close="handleCloseGroupModal"
      @select="handleSelectGroup"
    />
    
    <!-- 选择素材弹窗 -->
    <SelectMaterialModal
      :show="showMaterialModal"
      :selected-ids="selectedMaterials.map(m => m.id)"
      @close="handleCloseMaterialModal"
      @select="handleSelectMaterials"
    />
    </div>
  </div>
</template>
