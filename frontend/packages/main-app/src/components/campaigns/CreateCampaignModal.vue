<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { http } from '@/api/http'

interface Props {
  show: boolean
  projectId?: string
  initialData?: any
}

interface Emits {
  (e: 'close'): void
  (e: 'submit', data: CampaignFormData): void
}

interface CampaignFormData {
  channel: string
  account: string
  campaignName: string
  objective: string
  buyingType: string
  specialAdCategories: string
  specialAdCategoryCountry: string
  promotedObject: string
  abTest: string
  campaignBudget: string
  campaignStatus: string
  budgetType: string
  budget: string
  pacingType: string
  bidStrategy: string
  spendLimit: string
  start_date: string
  end_date: string
}

interface AccountOption {
  accountId: string
  accountName: string
  channel: string
  connectionId: string
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 是否为编辑模式
const isEditMode = computed(() => !!props.initialData)

const formData = ref<CampaignFormData>({
  channel: 'Meta',
  account: '',
  campaignName: '',
  objective: 'App promotion',
  buyingType: 'Auction',
  specialAdCategories: 'None',
  specialAdCategoryCountry: '',
  promotedObject: '',
  abTest: '关闭',
  campaignBudget: '开启',
  campaignStatus: 'draft',
  budgetType: 'Daily budget',
  budget: '',
  pacingType: 'standard',
  bidStrategy: 'Lowest cost',
  spendLimit: '',
  start_date: new Date().toISOString().slice(0, 16),
  end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16)
})

const accountOptions = ref<AccountOption[]>([])
const loadingAccounts = ref(false)

const errors = ref<Record<string, string>>({})
const submitting = ref(false)

// Meta Campaign 配置选项
const channelOptions = ['Meta', 'Google', 'TikTok']

const objectiveOptions = [
  'App promotion',
  'Sales',
  'Leads',
  'Traffic',
  'Engagement',
  'Awareness'
]

const buyingTypeOptions = [
  'Auction',
  'Reserved'
]

const specialAdCategoriesOptions = [
  'None',
  'Employment',
  'Housing',
  'Credit',
  'Issues, Elections or Politics'
]

const budgetTypeOptions = [
  'Daily budget',
  'Lifetime budget'
]

const bidStrategyOptions = [
  'Lowest cost',
  'Cost cap',
  'Bid cap',
  'Minimum ROAS'
]

// 国家代码映射（基于 Facebook Business SDK SpecialAdCategoryCountry 枚举）
const specialAdCategoryCountryOptions = [
  { code: 'US', name: 'United States' },
  { code: 'CA', name: 'Canada' },
  { code: 'GB', name: 'United Kingdom' },
  { code: 'AU', name: 'Australia' },
  { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' },
  { code: 'IT', name: 'Italy' },
  { code: 'ES', name: 'Spain' },
  { code: 'NL', name: 'Netherlands' },
  { code: 'SE', name: 'Sweden' },
  { code: 'NO', name: 'Norway' },
  { code: 'DK', name: 'Denmark' },
  { code: 'FI', name: 'Finland' },
  { code: 'BE', name: 'Belgium' },
  { code: 'CH', name: 'Switzerland' },
  { code: 'AT', name: 'Austria' },
  { code: 'IE', name: 'Ireland' },
  { code: 'NZ', name: 'New Zealand' },
  { code: 'SG', name: 'Singapore' },
  { code: 'HK', name: 'Hong Kong' },
  { code: 'JP', name: 'Japan' },
  { code: 'KR', name: 'South Korea' },
  { code: 'TW', name: 'Taiwan' },
  { code: 'IN', name: 'India' },
  { code: 'CN', name: 'China' },
  { code: 'BR', name: 'Brazil' },
  { code: 'MX', name: 'Mexico' },
  { code: 'AR', name: 'Argentina' },
  { code: 'CL', name: 'Chile' },
  { code: 'CO', name: 'Colombia' },
  { code: 'PE', name: 'Peru' },
  { code: 'ZA', name: 'South Africa' },
  { code: 'EG', name: 'Egypt' },
  { code: 'NG', name: 'Nigeria' },
  { code: 'KE', name: 'Kenya' },
  { code: 'AE', name: 'United Arab Emirates' },
  { code: 'SA', name: 'Saudi Arabia' },
  { code: 'IL', name: 'Israel' },
  { code: 'TR', name: 'Turkey' },
  { code: 'PL', name: 'Poland' },
  { code: 'CZ', name: 'Czech Republic' },
  { code: 'HU', name: 'Hungary' },
  { code: 'RO', name: 'Romania' },
  { code: 'GR', name: 'Greece' },
  { code: 'PT', name: 'Portugal' },
  { code: 'RU', name: 'Russia' },
  { code: 'UA', name: 'Ukraine' },
  { code: 'TH', name: 'Thailand' },
  { code: 'VN', name: 'Vietnam' },
  { code: 'PH', name: 'Philippines' },
  { code: 'ID', name: 'Indonesia' },
  { code: 'MY', name: 'Malaysia' }
]

const pacingTypeOptions = [
  'standard',
  'day_parting'
]

// 日期格式转换函数：将后端日期格式转换为 datetime-local 格式
const formatDateForInput = (dateStr: string | null | undefined): string => {
  if (!dateStr) {
    return new Date().toISOString().slice(0, 16)
  }

  // 如果已经是 datetime-local 格式 (YYYY-MM-DDTHH:MM)，直接返回
  if (dateStr.includes('T') && dateStr.length >= 16) {
    return dateStr.slice(0, 16)
  }

  // 如果是日期格式 (YYYY-MM-DD)，添加默认时间 00:00
  if (dateStr.length === 10 && dateStr.includes('-')) {
    return `${dateStr}T00:00`
  }

  // 尝试解析为 Date 对象
  try {
    const date = new Date(dateStr)
    if (!isNaN(date.getTime())) {
      return date.toISOString().slice(0, 16)
    }
  } catch (e) {
    console.error('日期格式转换失败:', dateStr, e)
  }

  // 默认返回当前时间
  return new Date().toISOString().slice(0, 16)
}

// 计算属性：根据 Buying Type 过滤 Objective 选项
const filteredObjectiveOptions = computed(() => {
  if (formData.value.buyingType === 'Reserved') {
    // Reserved 仅支持 Awareness 和 Engagement
    return objectiveOptions.filter(opt => opt === 'Awareness' || opt === 'Engagement')
  }
  // Auction 支持所有选项
  return objectiveOptions
})

// 计算属性：是否需要显示 special_ad_category_country
const showSpecialAdCategoryCountry = computed(() => {
  return formData.value.specialAdCategories !== 'None'
})

const isCampaignBudgetEnabled = computed(() => {
  return formData.value.campaignBudget === '开启'
})

const campaignStatusLabel = computed(() => {
  const labels: Record<string, string> = {
    draft: '草稿',
    running: '进行中',
    active: '进行中',
    paused: '暂停'
  }
  return labels[formData.value.campaignStatus] || formData.value.campaignStatus
})

const campaignStatusTone = computed(() => {
  if (formData.value.campaignStatus === 'paused') return 'paused'
  if (formData.value.campaignStatus === 'running' || formData.value.campaignStatus === 'active') return 'active'
  return 'draft'
})

// 监听 Buying Type 改变，自动调整 Objective
watch(() => formData.value.buyingType, (newBuyingType) => {
  const allowedObjectives = filteredObjectiveOptions.value
  // 如果当前 Objective 不在允许的选项中，重置为第一个允许的选项
  if (!allowedObjectives.includes(formData.value.objective)) {
    formData.value.objective = allowedObjectives[0] || 'Awareness'
  }
})

watch(() => formData.value.campaignBudget, (newCampaignBudget) => {
  if (newCampaignBudget === '关闭' && errors.value.budget) {
    const { budget, ...restErrors } = errors.value
    errors.value = restErrors
  }
})

// 获取广告账户列表
const fetchAccountOptions = async () => {
  loadingAccounts.value = true
  console.log('[fetchAccountOptions] 开始获取广告账户列表, channel:', formData.value.channel)

  try {
    const accounts = await http.get<any[]>(`/platform-auth/ad-accounts?channel=${formData.value.channel}`)
    console.log('[fetchAccountOptions] 接收到的数据:', accounts)

    accountOptions.value = accounts.map((account: any) => ({
      accountId: account.account_id,
      accountName: account.account_name,
      channel: account.channel,
      connectionId: account.connection_id
    }))

    console.log('[fetchAccountOptions] 转换后的账户选项:', accountOptions.value)
  } catch (error) {
    console.error('[fetchAccountOptions] 获取广告账户失败:', error)
    accountOptions.value = []
  } finally {
    loadingAccounts.value = false
    console.log('[fetchAccountOptions] 加载完成, 账户数量:', accountOptions.value.length)
  }
}

// 监听渠道变化，重新获取账户列表
const handleChannelChange = () => {
  formData.value.account = ''
  if (formData.value.channel !== 'TikTok') {
    fetchAccountOptions()
  }
}

// 验证表单
const validateForm = (): boolean => {
  errors.value = {}

  if (!formData.value.campaignName.trim()) {
    errors.value.campaignName = '请输入 Campaign 名称'
  }

  if (!formData.value.account) {
    errors.value.account = '请选择广告账户'
  }

  if (isCampaignBudgetEnabled.value && (!formData.value.budget || parseFloat(formData.value.budget) <= 0)) {
    errors.value.budget = '请输入有效的预算金额'
  }

  // 验证 special_ad_category_country：当 special_ad_categories 不为 None 时必填
  if (formData.value.specialAdCategories !== 'None' && !formData.value.specialAdCategoryCountry) {
    errors.value.specialAdCategoryCountry = '请选择特殊广告类别国家'
  }

  // 验证 promoted_object：如果填写了，必须是有效的 JSON
  if (formData.value.promotedObject && formData.value.promotedObject.trim()) {
    try {
      JSON.parse(formData.value.promotedObject)
    } catch (e) {
      errors.value.promotedObject = '请输入有效的 JSON 格式'
    }
  }

  return Object.keys(errors.value).length === 0
}

// 重置表单
const resetForm = () => {
  formData.value = {
    channel: 'Meta',
    account: '',
    campaignName: '',
    objective: 'Awareness',
    buyingType: 'Auction',
    specialAdCategories: 'None',
    specialAdCategoryCountry: '',
    promotedObject: '',
    abTest: '关闭',
    campaignBudget: '关闭',
    campaignStatus: 'draft',
    budgetType: 'Daily budget',
    budget: '',
    pacingType: 'standard',
    bidStrategy: 'Lowest cost',
    spendLimit: '',
    start_date: new Date().toISOString().slice(0, 16),
    end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16)
  }
  errors.value = {}
}

// 处理关闭
const handleClose = () => {
  if (!submitting.value) {
    resetForm()
    emit('close')
  }
}

// 处理保存
const handleSave = () => {
  if (!validateForm()) {
    return
  }

  submitting.value = true
  const campaignBudgetEnabled = isCampaignBudgetEnabled.value

  // 根据选择的账户找到对应的 connection_id
  const selectedAccount = accountOptions.value.find(
    account => account.accountId === formData.value.account
  )
  const connectionId = selectedAccount?.connectionId

  // 将前端表单字段映射到后端 API 字段
  const submitData: any = {
    id: props.initialData?.id,  // 编辑模式时包含 ID
    name: formData.value.campaignName,  // campaignName -> name
    platform: formData.value.channel,  // channel -> platform
    connection_id: connectionId,  // 添加 connection_id
    account_id: formData.value.account,  // account -> account_id
    objective: formData.value.objective,
    buying_type: formData.value.buyingType,  // buyingType -> buying_type
    special_ad_categories: formData.value.specialAdCategories,  // specialAdCategories -> special_ad_categories
    ab_test: formData.value.abTest,  // abTest -> ab_test
    campaign_budget_optimization: formData.value.campaignBudget,  // campaignBudget -> campaign_budget_optimization
    status: formData.value.campaignStatus,  // campaignStatus -> status
    budget_type: campaignBudgetEnabled ? formData.value.budgetType : undefined,  // budgetType -> budget_type
    budget: campaignBudgetEnabled ? (parseFloat(formData.value.budget) || 0) : 0,  // 转换为数字
    bid_strategy: formData.value.bidStrategy,  // bidStrategy -> bid_strategy
    spend_limit: formData.value.spendLimit ? parseFloat(formData.value.spendLimit) : undefined,  // 转换为数字或undefined
    start_date: formData.value.start_date,
    end_date: formData.value.end_date
  }

  console.log('[handleSave] 提交数据包含 connection_id:', connectionId)
  emit('submit', submitData)
}

// 初始化时获取账户列表
const init = () => {
  if (formData.value.channel !== 'TikTok') {
    fetchAccountOptions()
  }
}

// 监听模态框打开，自动获取账户列表
watch(() => props.show, (newVal) => {
  if (newVal) {
    if (formData.value.channel !== 'TikTok') {
      fetchAccountOptions()
    }
  }
})

// 监听 initialData 变化，填充表单数据
watch(() => props.initialData, (newData) => {
  if (newData) {
    console.log('编辑模式：填充表单数据', newData)
    formData.value = {
      channel: newData.platform || 'Meta',
      account: newData.account_id || '',
      campaignName: newData.name || '',
      objective: newData.objective || 'Awareness',
      buyingType: newData.buying_type || 'Auction',
      specialAdCategories: newData.special_ad_categories || 'None',
      specialAdCategoryCountry: newData.special_ad_category_country || '',
      promotedObject: newData.promoted_object || '',
      abTest: newData.ab_test || '关闭',
      campaignBudget: newData.campaign_budget_optimization || '关闭',
      campaignStatus: newData.status || 'draft',
      budgetType: newData.budget_type || 'Daily budget',
      budget: newData.budget?.toString() || '',
      pacingType: newData.pacing_type || 'standard',
      bidStrategy: newData.bid_strategy || 'Lowest cost',
      spendLimit: newData.spend_limit?.toString() || '',
      start_date: formatDateForInput(newData.start_date),
      end_date: formatDateForInput(newData.end_date)
    }
  } else {
    resetForm()
  }
}, { immediate: true })

// 监听提交完成
defineExpose({
  resetForm,
  setSubmitting: (value: boolean) => {
    submitting.value = value
  },
  init
})
</script>

<template>
  <!-- 遮罩层 -->
  <Transition name="fade">
    <div
      v-if="show"
      class="campaign-drawer-layer fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
      @click.self="handleClose"
    >
      <!-- 弹窗容器 - 右侧抽屉 -->
      <Transition name="slide">
        <div
          v-if="show"
          class="campaign-drawer fixed right-0 top-0 h-full bg-white dark:bg-slate-800 shadow-2xl w-full max-w-[600px] overflow-hidden flex flex-col rounded-l-md"
        >
          <!-- 弹窗头部 -->
          <div class="campaign-drawer-head flex items-center justify-between px-[15px] py-[10px] border-b border-slate-200 dark:border-slate-700">
            <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">
              {{ isEditMode ? '编辑 Campaign' : '创建 Campaign' }}
            </h3>
            <button
              class="campaign-close p-[4px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              @click="handleClose"
              :disabled="submitting"
            >
              <span class="material-symbols-outlined text-[14px] text-slate-500">close</span>
            </button>
          </div>

          <!-- 弹窗内容 -->
          <div class="campaign-drawer-body flex-1 overflow-y-auto px-[15px] py-[10px]">
            <!-- 说明文字 -->
            <div class="campaign-framework-note mb-[13px] p-[10px] bg-slate-50 dark:bg-slate-700/30 rounded-md">
              <p class="text-[10px] text-slate-600 dark:text-slate-400 leading-relaxed">
                <strong class="text-slate-700 dark:text-slate-300">Meta Campaign 框架</strong><br>
                项目对应 Meta Campaign 层级；下层计划对应 Meta Ad Set，素材对应 Meta Ad 素材配置。这里配置项目归属与 Campaign 字段。
              </p>
            </div>

            <!-- 表单 -->
            <form @submit.prevent="handleSave" class="campaign-form space-y-[10px]">
              <!-- 第一行：投放渠道 + 广告账户 -->
              <div class="grid grid-cols-2 gap-[10px]">
                <!-- 投放渠道 -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    投放渠道
                  </label>
                  <select
                    v-model="formData.channel"
                    @change="handleChannelChange"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option v-for="channel in channelOptions" :key="channel" :value="channel" :disabled="channel === 'TikTok'" :class="{ 'text-slate-400': channel === 'TikTok' }">
                      {{ channel }}{{ channel === 'TikTok' ? ' (暂未支持)' : '' }}
                    </option>
                  </select>
                </div>

                <!-- 广告账户 -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    广告账户 *
                  </label>
                  <select
                    v-model="formData.account"
                    :disabled="loadingAccounts || formData.channel === 'TikTok'"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    :class="{ 'border-red-500': errors.account }"
                  >
                    <option value="" disabled>{{ loadingAccounts ? '加载中...' : '请选择广告账户' }}</option>
                    <option v-for="acc in accountOptions" :key="acc.accountId" :value="acc.accountId">
                      {{ acc.accountName }} ({{ acc.accountId }})
                    </option>
                  </select>
                  <p v-if="errors.account" class="mt-[3px] text-[9px] text-red-500">{{ errors.account }}</p>
                </div>
              </div>

              <!-- 第二行：Campaign 名称 -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  Campaign 名称 *
                </label>
                <input
                  v-model="formData.campaignName"
                  type="text"
                  placeholder="Meta Campaign Name"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  :class="{ 'border-red-500': errors.campaignName }"
                />
                <p v-if="errors.campaignName" class="mt-[3px] text-[9px] text-red-500">{{ errors.campaignName }}</p>
              </div>

              <!-- 第三行：Objective + Buying Type -->
              <div class="grid grid-cols-2 gap-[10px]">
                <!-- Buying Type -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Buying Type *
                  </label>
                  <select
                    v-model="formData.buyingType"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option v-for="opt in buyingTypeOptions" :key="opt" :value="opt">
                      {{ opt }}
                    </option>
                  </select>
                </div>

                <!-- Objective -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Objective *
                  </label>
                  <select
                    v-model="formData.objective"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option v-for="opt in filteredObjectiveOptions" :key="opt" :value="opt">
                      {{ opt }}
                    </option>
                  </select>
                </div>
              </div>

              <!-- Spend Limit -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  Campaign Spend Limit (Optional)
                </label>
                <input
                  v-model="formData.spendLimit"
                  type="text"
                  placeholder="例如 18,000 USD"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <!-- 第四行：Special Ad Categories -->
              <div class="grid grid-cols-2 gap-[10px]">
                <!-- Special Ad Categories -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Special Ad Categories
                  </label>
                  <select
                    v-model="formData.specialAdCategories"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option v-for="opt in specialAdCategoriesOptions" :key="opt" :value="opt">
                      {{ opt }}
                    </option>
                  </select>
                </div>

                <!-- Special Ad Category Country (始终显示，根据条件 enable/disable) -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Special Ad Category Country
                    <span v-if="showSpecialAdCategoryCountry" class="text-red-500">*</span>
                  </label>
                  <select
                    v-model="formData.specialAdCategoryCountry"
                    :disabled="!showSpecialAdCategoryCountry"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    :class="{ 'border-red-500': errors.specialAdCategoryCountry }"
                  >
                    <option value="">Select Country</option>
                    <option v-for="country in specialAdCategoryCountryOptions" :key="country.code" :value="country.code">
                      {{ country.code }} ({{ country.name }})
                    </option>
                  </select>
                  <p v-if="errors.specialAdCategoryCountry" class="mt-[3px] text-[9px] text-red-500">{{ errors.specialAdCategoryCountry }}</p>
                </div>
              </div>

              <!-- 第五行：Campaign Budget 开关 + Campaign Status -->
              <div class="grid grid-cols-2 gap-[10px]">
                <!-- Campaign Budget 开关 -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Campaign Budget 开关
                  </label>
                  <select
                    v-model="formData.campaignBudget"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="开启">开启</option>
                    <option value="关闭">关闭</option>
                  </select>
                </div>

                <!-- Campaign Status -->
                <div>
                  <label class="campaign-status-label block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    <span>Campaign Status</span><span class="campaign-status-indicator" :class="campaignStatusTone">{{ campaignStatusLabel }}</span>
                  </label>
                  <select
                    v-model="formData.campaignStatus"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="draft">Draft</option>
                    <option value="running">Running</option>
                    <option value="paused">Paused</option>
                  </select>
                </div>
              </div>

              <!-- 第六行：Budget Type + Daily/Lifetime Budget -->
              <div class="grid grid-cols-2 gap-[10px]">
                <!-- Budget Type -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Budget Type
                  </label>
                  <select
                    v-model="formData.budgetType"
                    :disabled="!isCampaignBudgetEnabled"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <option v-for="type in budgetTypeOptions" :key="type" :value="type">
                      {{ type }}
                    </option>
                  </select>
                </div>

                <!-- Daily/Lifetime Budget -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Daily/Lifetime budget(USD)<span v-if="isCampaignBudgetEnabled"> *</span>
                  </label>
                  <input
                    v-model="formData.budget"
                    type="text"
                    placeholder="例如 800 USD"
                    :disabled="!isCampaignBudgetEnabled"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    :class="{ 'border-red-500': errors.budget }"
                  />
                  <p v-if="errors.budget" class="mt-[3px] text-[9px] text-red-500">{{ errors.budget }}</p>
                </div>
              </div>

              <!-- 第七行：Bid Strategy + A/B Test  -->
              <div class="grid grid-cols-2 gap-[10px]">
                <!-- Bid Strategy -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Bid Strategy
                  </label>
                  <select
                    v-model="formData.bidStrategy"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option v-for="strategy in bidStrategyOptions" :key="strategy" :value="strategy">
                      {{ strategy }}
                    </option>
                  </select>
                </div>

                <!-- A/B Test -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    A/B Test
                  </label>
                  <select
                    v-model="formData.abTest"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="关闭">关闭</option>
                    <option value="开启">开启</option>
                  </select>
                </div>
              </div>

              <!-- 新增行：Pacing Type + Promoted Object -->
              <div class="grid grid-cols-2 gap-[10px]">
                <!-- Pacing Type -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Pacing Type
                  </label>
                  <select
                    v-model="formData.pacingType"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option v-for="type in pacingTypeOptions" :key="type" :value="type">
                      {{ type }}
                    </option>
                  </select>
                </div>

                <!-- Promoted Object (JSON) -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Promoted Object (JSON)
                  </label>
                  <input
                    v-model="formData.promotedObject"
                    type="text"
                    placeholder='{"application_id": "123"}'
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <!-- 第八行：Start Date + End Date -->
              <div class="grid grid-cols-2 gap-[10px]">
                <!-- Start Date -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Start Date
                  </label>
                  <input
                    v-model="formData.start_date"
                    type="datetime-local"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <!-- End Date -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    End Date
                  </label>
                  <input
                    v-model="formData.end_date"
                    type="datetime-local"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
            </form>
          </div>

          <!-- 弹窗底部 -->
          <div class="campaign-drawer-actions flex items-center justify-end gap-[8px] px-[15px] py-[10px] border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              class="campaign-secondary px-[12px] py-[6px] text-[11px] font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-md hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
              @click="handleClose"
              :disabled="submitting"
            >
              取消
            </button>
            <button
              type="button"
              class="campaign-confirm px-[12px] py-[6px] text-[11px] font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              @click="handleSave"
              :disabled="submitting"
            >
              {{ submitting ? (isEditMode ? '保存中...' : '创建中...') : (isEditMode ? '保存' : '创建') }}
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
.campaign-drawer-layer {
  --cm-surface: #f6f5f4;
  --cm-surface-soft: #fafaf9;
  --cm-line: #e5e3df;
  --cm-line-soft: #ede9e4;
  --cm-line-strong: #c8c4be;
  --cm-ink: #1a1a1a;
  --cm-charcoal: #37352f;
  --cm-slate: #5d5b54;
  --cm-steel: #787671;
  --cm-stone: #a4a097;
  background: rgba(26,26,26,.48) !important;
  font-family: "Notion Sans", "Avenir Next", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}
.campaign-drawer { width: min(680px,100vw) !important; max-width: none !important; border-left: 1px solid var(--cm-line); border-radius: 0 !important; background: #fff !important; box-shadow: rgba(15,15,15,.20) -18px 0 52px -18px !important; }
.campaign-drawer-head { min-height: 57px; padding: 0 18px !important; border-color: var(--cm-line) !important; }
.campaign-drawer-head h3 { margin: 0; color: var(--cm-ink) !important; font-size: 15px !important; font-weight: 600; letter-spacing: -.2px; }
.campaign-close { width: 30px; height: 30px; display: grid; place-items: center; padding: 0 !important; border: 0; border-radius: 6px; background: transparent; color: var(--cm-steel); }
.campaign-close:hover { background: var(--cm-surface) !important; color: var(--cm-ink); }
.campaign-close .material-symbols-outlined { font-size: 18px !important; }
.campaign-drawer-body { padding: 14px 18px 24px !important; scrollbar-color: var(--cm-line-strong) transparent; }
.campaign-framework-note { margin-bottom: 15px !important; padding: 12px !important; border: 0 !important; border-radius: 8px; background: var(--cm-surface) !important; }
.campaign-framework-note p { margin: 0; color: var(--cm-slate) !important; font-size: 10px !important; line-height: 1.55; }
.campaign-framework-note strong { display: inline-block; margin-bottom: 4px; color: var(--cm-charcoal) !important; font-size: 10px; font-weight: 600; }
.campaign-form { display: grid; gap: 11px; }
.campaign-form > div { margin: 0 !important; }
.campaign-form label { color: var(--cm-slate) !important; font-size: 10px !important; font-weight: 500 !important; }
.campaign-form input,.campaign-form select { width: 100%; height: 38px; padding: 0 10px !important; border: 1px solid var(--cm-line-strong) !important; border-radius: 8px !important; outline: none; background: #fff !important; color: var(--cm-charcoal) !important; font-size: 11px !important; box-shadow: none !important; }
.campaign-form input::placeholder { color: var(--cm-stone); }
.campaign-form input:focus,.campaign-form select:focus { border: 2px solid var(--cm-charcoal) !important; box-shadow: none !important; }
.campaign-form input:disabled,.campaign-form select:disabled { border-color: var(--cm-line) !important; background: var(--cm-surface-soft) !important; color: var(--cm-stone) !important; opacity: 1 !important; }
.campaign-status-label { display: flex !important; align-items: center; justify-content: space-between; gap: 8px; }
.campaign-status-indicator { min-height: 20px; display: inline-flex; align-items: center; gap: 5px; padding: 2px 6px; border-radius: 6px; font-size: 8px; font-weight: 600; }
.campaign-status-indicator::before { content: ""; width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.campaign-status-indicator.draft { background: #fff3d6; color: #805700; }
.campaign-status-indicator.active { background: #ecfdf5; color: #047857; }
.campaign-status-indicator.paused { border: 1px solid #fdba74; background: #fff7ed; color: #ea580c; }
.campaign-drawer-actions { min-height: 58px; padding: 0 18px !important; border-color: var(--cm-line) !important; background: rgba(255,255,255,.96); }
.campaign-secondary,.campaign-confirm { min-height: 34px; display: inline-flex; align-items: center; justify-content: center; padding: 0 14px !important; border-radius: 8px !important; font-size: 11px !important; font-weight: 500; }
.campaign-secondary { border: 1px solid var(--cm-line-strong) !important; background: #fff !important; color: var(--cm-charcoal) !important; }
.campaign-secondary:hover { border-color: var(--cm-charcoal) !important; color: var(--cm-ink) !important; }
.campaign-confirm { border: 1px solid #2383e2 !important; background: #2383e2 !important; color: #fff !important; }
.campaign-confirm:hover { border-color: #1b6fc1 !important; background: #1b6fc1 !important; }
@media (max-width: 720px) {
  .campaign-drawer { width: 100vw !important; border-left: 0; }
  .campaign-drawer-body { padding: 14px 14px 24px !important; }
  .campaign-drawer-head,.campaign-drawer-actions { padding-right: 14px !important; padding-left: 14px !important; }
}
@media (max-width: 520px) {
  .campaign-form .grid-cols-2 { grid-template-columns: 1fr; }
  .campaign-drawer-head { min-height: 52px; }
  .campaign-drawer-actions { min-height: 56px; }
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: transform 0.3s ease;
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}
</style>
