<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import SelectGroupModal from '@/components/campaigns/SelectGroupModal.vue'
import { getProjectDetail, type Project } from '@/api/projects'
import { createCampaign } from '@/api/campaigns'

const router = useRouter()
const route = useRoute()

const projectId = ref(route.query.projectId as string || '')

const currentStep = ref(1)
const totalSteps = 4

// 导航配置
const navItems = [
  { id: 'dashboard', icon: 'pie_chart', label: '数据概览', path: '/dashboard' },
  { id: 'projects', icon: 'folder_open', label: '项目管理', path: '/projects' },
  { id: 'campaigns', icon: 'ads_click', label: '广告投放', path: '/campaign' },
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
const selectedPlatform = ref('')
const showGroupModal = ref(false)
const platforms = [
  { id: 'Google', name: 'Google Ads', icon: 'G', description: '搜索广告、展示广告、应用广告' },
  { id: 'TikTok', name: 'TikTok Ads', icon: '♪', description: '信息流广告、开屏广告、挑战赛' },
  { id: 'Meta', name: 'Meta Ads', icon: 'f', description: 'Facebook/Instagram 广告' }
]

const accountChecks = [
  { id: 'account', label: '广告账户已开户', checked: true },
  { id: 'conversion', label: '转化像素已配置', checked: true },
  { id: 'app', label: '应用已绑定', checked: true },
  { id: 'payment', label: '支付方式已设置', checked: true }
]

// 创建阶段数据
const campaignObjective = ref('install')
const objectives = [
  { id: 'install', name: '应用安装', description: '增加应用下载量', icon: 'download' },
  { id: 'conversion', name: '转化率', description: '优化应用内转化', icon: 'shopping_cart' },
  { id: 'engagement', name: '品牌曝光', description: '提升品牌知名度', icon: 'visibility' },
  { id: 'retention', name: '用户留存', description: '提升用户活跃度', icon: 'group' }
]

const budgetType = ref('daily')
const dailyBudget = ref(10000)

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

// 执行阶段数据
const selectedMaterials = ref<string[]>([])
const materials = ref([
  { id: 'mat_001', name: 'CB_Victory_Dance', type: 'image', ctr: 5.8, roi: 2.8 },
  { id: 'mat_002', name: 'CB_AI_ComboPlay', type: 'image', ctr: 4.2, roi: 3.0 },
  { id: 'mat_003', name: 'DB_AI_NewScene', type: 'image', ctr: 6.2, roi: 3.0 },
  { id: 'mat_004', name: 'DB_AI_EmotionHook', type: 'image', ctr: 6.1, roi: 3.0 }
])

const targetRegions = ref<string[]>([])
const regions = ['美国', '英国', '加拿大', '澳洲', '日本', '韩国', '新加坡', '泰国', '印度', '巴西']

const ageRange = ref({ min: 18, max: 65 })
const gender = ref('all')

const targetInterests = ref<string[]>([])
const interests = ['游戏', '短视频', '电商购物', '社交媒体', '音乐', '电影', '旅行', '科技数码', '时尚美妆', '烹饪美食', '教育']

// 验证逻辑
const canProceedStep1 = computed(() => {
  return selectedGroup.value !== null && selectedPlatform.value !== ''
})

const canProceedStep2 = computed(() => {
  return campaignObjective.value !== '' && dailyBudget.value > 0
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

const nextStep = () => {
  if (currentStep.value < totalSteps && canProceed.value) {
    currentStep.value++
  }
}

const prevStep = () => {
  if (currentStep.value > 1) {
    currentStep.value--
  }
}

const toggleMaterial = (materialId: string) => {
  const index = selectedMaterials.value.indexOf(materialId)
  if (index > -1) {
    selectedMaterials.value.splice(index, 1)
  } else {
    selectedMaterials.value.push(materialId)
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
  
  submitting.value = true
  
  try {
    // 构建广告计划名称
    const campaignName = `${selectedGroup.value.name} - ${platforms.find(p => p.id === selectedPlatform.value)?.name}`
    
    // 调用API创建广告计划
    const campaign = await createCampaign({
      project_id: selectedGroup.value.id,
      name: campaignName,
      platform: selectedPlatform.value,
      budget: dailyBudget.value,
      status: 'draft',
      material_ids: selectedMaterials.value
    })
    
    console.log('广告计划创建成功:', campaign)
    
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
  console.log('选择分组:', project)
}

// 页面加载时，如果有projectId参数，自动加载该项目作为默认分组
onMounted(async () => {
  if (projectId.value) {
    try {
      const project = await getProjectDetail(projectId.value)
      selectedGroup.value = project
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
      <div class="flex-1 overflow-y-auto">
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
              <div class="text-sm text-slate-500 dark:text-slate-400 mt-1">{{ selectedGroup.game_type }}</div>
            </div>
            <div v-else class="text-center text-primary">
              请选择分组
            </div>
          </button>
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
              class="p-4 rounded-lg border-2 transition-all cursor-pointer"
              :class="selectedPlatform === platform.id 
                ? 'border-primary bg-primary/5' 
                : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
              @click="selectedPlatform = platform.id"
            >
              <div class="flex items-center gap-4">
                <div class="w-12 h-12 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-xl font-bold">
                  {{ platform.icon }}
                </div>
                <div class="flex-1">
                  <div class="font-semibold text-slate-900 dark:text-white">{{ platform.name }}</div>
                  <div class="text-sm text-slate-500 dark:text-slate-400">{{ platform.description }}</div>
                </div>
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
                v-model.number="dailyBudget"
                type="number"
                min="0"
                step="100"
                placeholder="例如: 10000"
                class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
              />
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
          <div class="grid grid-cols-2 gap-4">
            <div
              v-for="material in materials"
              :key="material.id"
              class="p-4 rounded-lg border-2 transition-all cursor-pointer"
              :class="selectedMaterials.includes(material.id) 
                ? 'border-primary bg-primary/5' 
                : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
              @click="toggleMaterial(material.id)"
            >
              <div class="flex items-center gap-3">
                <div class="w-16 h-16 rounded-md bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                  <span class="material-symbols-outlined text-2xl text-slate-400">image</span>
                </div>
                <div class="flex-1">
                  <div class="font-medium text-slate-900 dark:text-white text-sm mb-1">{{ material.name }}</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400">
                    {{ material.type }} · CTR {{ material.ctr }}% · ROI {{ material.roi }}x
                  </div>
                </div>
              </div>
            </div>
          </div>
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
              <div class="flex items-center gap-1 text-emerald-600">
                <span class="material-symbols-outlined text-sm">check_circle</span>
                <span class="font-medium">全部就绪</span>
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
                {{ budgetType === 'daily' ? '日预算' : '总预算' }} ${{ dailyBudget.toLocaleString() }}
              </span>
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
    </div>
  </div>
</template>
