<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  show: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'submit', data: ProjectFormData): void
}

interface ProjectFormData {
  channel: string
  name: string
  product: string
  countries: string
  account: string
  campaignName: string
  objective: string
  buyingType: string
  specialAdCategories: string
  abTest: string
  campaignBudget: string
  campaignStatus: string
  budgetType: string
  budget: string
  bidStrategy: string
  spendLimit: string
  start: string
  end: string
}

interface AccountOption {
  accountId: string
  accountName: string
  channel: string
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const formData = ref<ProjectFormData>({
  channel: 'Meta',
  name: '',
  product: '',
  countries: '',
  account: '',
  campaignName: '',
  objective: 'App promotion',
  buyingType: 'Auction',
  specialAdCategories: 'None',
  abTest: '关闭',
  campaignBudget: '开启',
  campaignStatus: 'Draft',
  budgetType: 'Daily budget',
  budget: '',
  bidStrategy: 'Lowest cost',
  spendLimit: '',
  start: '',
  end: ''
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

const buyingTypeOptions = ['Auction', 'Reservation']

const specialAdCategoriesOptions = [
  'None',
  'Credit',
  'Employment',
  'Housing',
  'Social issues, elections or politics'
]

const campaignStatusOptions = ['Active', 'Paused', 'Draft']

const budgetTypeOptions = ['Daily budget', 'Lifetime budget']

const bidStrategyOptions = [
  'Lowest cost',
  'Cost cap',
  'Bid cap',
  'ROAS goal'
]

// 获取广告账户列表
const fetchAccountOptions = async () => {
  loadingAccounts.value = true
  console.log('[fetchAccountOptions] 开始获取广告账户列表, channel:', formData.value.channel)
  
  try {
    const token = localStorage.getItem('animagus_token')
    console.log('[fetchAccountOptions] Token存在:', !!token)
    
    const url = `/api/v1/platform-auth/ad-accounts?channel=${formData.value.channel}`
    console.log('[fetchAccountOptions] 请求URL:', url)
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    })
    
    console.log('[fetchAccountOptions] 响应状态:', response.status, response.statusText)
    
    if (!response.ok) {
      const errorText = await response.text()
      console.error('[fetchAccountOptions] 请求失败:', errorText)
      throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`)
    }
    
    const data = await response.json()
    console.log('[fetchAccountOptions] 接收到的数据:', data)
    
    accountOptions.value = data.map((account: any) => ({
      accountId: account.account_id,
      accountName: account.account_name,
      channel: account.channel
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

// 表单验证
const validateForm = (): boolean => {
  errors.value = {}
  
  if (!formData.value.name.trim()) {
    errors.value.name = '请输入项目名称'
  }
  
  if (!formData.value.product.trim()) {
    errors.value.product = '请输入产品名称'
  }
  
  if (!formData.value.countries.trim()) {
    errors.value.countries = '请输入投放国家'
  }
  
  if (!formData.value.account.trim()) {
    errors.value.account = '请输入广告账户 ID'
  }
  
  if (!formData.value.campaignName.trim()) {
    errors.value.campaignName = '请输入 Campaign 名称'
  }
  
  if (formData.value.start && formData.value.end) {
    if (new Date(formData.value.start) > new Date(formData.value.end)) {
      errors.value.end = '结束时间不能早于开始时间'
    }
  }
  
  return Object.keys(errors.value).length === 0
}

// 提交表单
const handleSubmit = () => {
  if (!validateForm()) {
    return
  }
  
  submitting.value = true
  emit('submit', { ...formData.value })
}

// 关闭弹窗
const handleClose = () => {
  if (!submitting.value) {
    emit('close')
    resetForm()
  }
}

// 重置表单
const resetForm = () => {
  formData.value = {
    channel: 'Meta',
    name: '',
    product: '',
    countries: '',
    account: '',
    campaignName: '',
    objective: 'App promotion',
    buyingType: 'Auction',
    specialAdCategories: 'None',
    abTest: '关闭',
    campaignBudget: '开启',
    campaignStatus: 'Draft',
    budgetType: 'Daily budget',
    budget: '',
    bidStrategy: 'Lowest cost',
    spendLimit: '',
    start: '',
    end: ''
  }
  errors.value = {}
  submitting.value = false
  accountOptions.value = []
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
    // 模态框打开时，如果渠道不是TikTok，则获取账户列表
    if (formData.value.channel !== 'TikTok') {
      fetchAccountOptions()
    }
  }
})

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
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
      @click.self="handleClose"
    >
      <!-- 弹窗容器 - 右侧抽屉 -->
      <Transition name="slide">
        <div
          v-if="show"
          class="fixed right-0 top-0 h-full bg-white dark:bg-slate-800 shadow-2xl w-full max-w-[600px] overflow-hidden flex flex-col rounded-l-md
          "
        >
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between px-[15px] py-[10px] border-b border-slate-200 dark:border-slate-700">
            <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">新建投放项目</h3>
            <button
              class="p-[4px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              @click="handleClose"
              :disabled="submitting"
            >
              <span class="material-symbols-outlined text-[14px] text-slate-500">close</span>
            </button>
          </div>

          <!-- 弹窗内容 -->
          <div class="flex-1 overflow-y-auto px-[15px] py-[10px]">
            <!-- 说明文字 -->
            <div class="mb-[13px] p-[10px] bg-slate-50 dark:bg-slate-700/30 rounded-md">
              <p class="text-[10px] text-slate-600 dark:text-slate-400 leading-relaxed">
                <strong class="text-slate-700 dark:text-slate-300">Meta Campaign 框架</strong><br>
                项目对应 Meta Campaign 层级；下层计划对应 Meta Ad Set，素材对应 Meta Ad 素材配置。这里配置项目归属与 Campaign 字段。
              </p>
            </div>

            <form @submit.prevent="handleSubmit" class="grid grid-cols-2 gap-x-[13px] gap-y-[13px]">
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

              <!-- 项目名称 -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  项目名称
                </label>
                <input
                  v-model="formData.name"
                  type="text"
                  placeholder="例如 CB_US_Meta_AppPromotion"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  :class="{ 'border-red-500': errors.name }"
                />
                <p v-if="errors.name" class="mt-[3px] text-[9px] text-red-500">{{ errors.name }}</p>
              </div>

              <!-- 产品 -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  产品
                </label>
                <input
                  v-model="formData.product"
                  type="text"
                  placeholder="例如 休闲消除手游"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  :class="{ 'border-red-500': errors.product }"
                />
                <p v-if="errors.product" class="mt-[3px] text-[9px] text-red-500">{{ errors.product }}</p>
              </div>

              <!-- 投放国家 -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  投放国家
                </label>
                <input
                  v-model="formData.countries"
                  type="text"
                  placeholder="例如 美国 / 加拿大"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  :class="{ 'border-red-500': errors.countries }"
                />
                <p v-if="errors.countries" class="mt-[3px] text-[9px] text-red-500">{{ errors.countries }}</p>
              </div>

              <!-- 广告账户 -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  广告账户
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

              <!-- Campaign 名称 -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  Campaign 名称
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

              <!-- Objective -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  Objective
                </label>
                <select
                  v-model="formData.objective"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option v-for="opt in objectiveOptions" :key="opt" :value="opt">
                    {{ opt }}
                  </option>
                </select>
              </div>

              <!-- Buying type -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  Buying type
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

              <!-- Special ad categories -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  Special ad categories
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

              <!-- A/B test -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  A/B test
                </label>
                <select
                  v-model="formData.abTest"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="关闭">关闭</option>
                  <option value="开启">开启</option>
                </select>
              </div>

              <!-- Campaign budget 开关 -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  Campaign budget 开关
                </label>
                <select
                  v-model="formData.campaignBudget"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="开启">开启</option>
                  <option value="关闭">关闭</option>
                </select>
              </div>

              <!-- 状态 -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  状态
                </label>
                <select
                  v-model="formData.campaignStatus"
                  disabled
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 opacity-60 cursor-not-allowed"
                >
                  <option v-for="status in campaignStatusOptions" :key="status" :value="status">
                    {{ status }}
                  </option>
                </select>
              </div>

              <!-- Budget type -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  Budget type
                </label>
                <select
                  v-model="formData.budgetType"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option v-for="type in budgetTypeOptions" :key="type" :value="type">
                    {{ type }}
                  </option>
                </select>
              </div>

              <!-- daily/lifetime budget -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  daily/lifetime budget
                </label>
                <input
                  v-model="formData.budget"
                  type="text"
                  placeholder="例如 800 USD"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <!-- bid strategy -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  bid strategy
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

              <!-- spend limit -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  spend limit
                </label>
                <input
                  v-model="formData.spendLimit"
                  type="text"
                  placeholder="例如 18,000 USD"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <!-- start -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  start
                </label>
                <input
                  v-model="formData.start"
                  type="datetime-local"
                  placeholder="例如 2026-06-01 10:00"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <!-- end -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  end
                </label>
                <input
                  v-model="formData.end"
                  type="datetime-local"
                  placeholder="例如 2026-06-30 23:00"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  :class="{ 'border-red-500': errors.end }"
                />
                <p v-if="errors.end" class="mt-[3px] text-[9px] text-red-500">{{ errors.end }}</p>
              </div>
            </form>
          </div>

          <!-- 弹窗底部 -->
          <div class="flex items-center justify-between px-[15px] py-[11px] border-t border-slate-200 dark:border-slate-700">
            <span class="text-[10px] text-slate-500 dark:text-slate-400">
              项目对应该渠道 Campaign 层级
            </span>
            <div class="flex items-center gap-[8px]">
              <button
                type="button"
                class="px-[13px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 text-[10px] text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                @click="handleClose"
                :disabled="submitting"
              >
                取消
              </button>
              <button
                type="button"
                class="px-[13px] py-[6px] rounded-md bg-blue-600 text-white text-[10px] hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-[5px]"
                @click="handleSubmit"
                :disabled="submitting"
              >
                <span v-if="submitting" class="material-symbols-outlined animate-spin text-[10px]">progress_activity</span>
                <span>{{ submitting ? '保存中...' : '保存项目' }}</span>
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
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
