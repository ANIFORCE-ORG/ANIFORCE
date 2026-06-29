<script setup lang="ts">
import { ref, computed } from 'vue'
import { useLanguage } from '@/store/language'

interface Props {
  show: boolean
  campaignId: string
}

interface Emits {
  (e: 'close'): void
  (e: 'submit', data: any): void
}

interface FormData {
  adsetName: string
  optimizationGoal: string
  billingEvent: string
  destinationType: string
  status: string
  budgetType: 'daily' | 'lifetime'
  dailyBudget: number | null
  lifetimeBudget: number | null
  bidStrategy: string
  bidAmount: number | null
  startTime: string
  endTime: string
  timezoneType: string
  ageMin: number
  ageMax: number
  genders: number[]
  geoCountries: string[]
  pixelId: string
  customEventType: string
  applicationId: string
  pageId: string
  adName: string
  adStatus: string
  adBidAmount: number | null
  adScheduleStartTime: string
  adScheduleEndTime: string
  trackingSpecs: string
  conversionDomain: string
  adLabels: string
  displaySequence: number | null
  creativeName: string
  creativeFormat: 'link' | 'image' | 'video'
  creativePageId: string
  creativeTitle: string
  creativeBody: string
  creativeLink: string
  creativeImageHash: string
  creativeVideoId: string
  creativeCallToAction: string
  creativeInstagramActorId: string
}

interface SectionsState {
  basic: boolean
  budget: boolean
  schedule: boolean
  targeting: boolean
  promotedObject: boolean
  ads: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()
const { language } = useLanguage()

const isEnglish = computed(() => language.value === 'en')
const displayText = (cn: string, en: string) => isEnglish.value ? en : cn
const localizedOptions = <T extends string>(options: Array<{ value: T; cn: string; en: string }>) => computed(() => (
  options.map(({ value, cn, en }) => ({
    value,
    label: displayText(cn, en)
  }))
))

const createDefaultFormData = (): FormData => ({
  adsetName: '',
  optimizationGoal: 'OFFSITE_CONVERSIONS',
  billingEvent: 'IMPRESSIONS',
  destinationType: 'WEBSITE',
  status: 'PAUSED',
  budgetType: 'daily',
  dailyBudget: null,
  lifetimeBudget: null,
  bidStrategy: 'LOWEST_COST_WITHOUT_CAP',
  bidAmount: null,
  startTime: '',
  endTime: '',
  timezoneType: 'USER',
  ageMin: 18,
  ageMax: 65,
  genders: [1, 2],
  geoCountries: [],
  pixelId: '',
  customEventType: '',
  applicationId: '',
  pageId: '',
  adName: '',
  adStatus: 'PAUSED',
  adBidAmount: null,
  adScheduleStartTime: '',
  adScheduleEndTime: '',
  trackingSpecs: '',
  conversionDomain: '',
  adLabels: '',
  displaySequence: null,
  creativeName: '',
  creativeFormat: 'link',
  creativePageId: '',
  creativeTitle: '',
  creativeBody: '',
  creativeLink: '',
  creativeImageHash: '',
  creativeVideoId: '',
  creativeCallToAction: 'LEARN_MORE',
  creativeInstagramActorId: ''
})

const createDefaultSections = (): SectionsState => ({
  basic: true,
  budget: true,
  schedule: false,
  targeting: false,
  promotedObject: false,
  ads: true
})

const formData = ref<FormData>(createDefaultFormData())
const sections = ref<SectionsState>(createDefaultSections())
const errors = ref<Record<string, string>>({})
const submitting = ref(false)

const optimizationGoalOptions = localizedOptions([
  { value: 'OFFSITE_CONVERSIONS', cn: '网站转化', en: 'Website conversions' },
  { value: 'LINK_CLICKS', cn: '链接点击', en: 'Link clicks' },
  { value: 'IMPRESSIONS', cn: '展示次数', en: 'Impressions' },
  { value: 'APP_INSTALLS', cn: '应用安装', en: 'App installs' },
  { value: 'LEAD_GENERATION', cn: '潜在客户开发', en: 'Lead generation' }
])

const billingEventOptions = localizedOptions([
  { value: 'IMPRESSIONS', cn: '展示次数', en: 'Impressions' },
  { value: 'LINK_CLICKS', cn: '链接点击', en: 'Link clicks' },
  { value: 'APP_INSTALLS', cn: '应用安装', en: 'App installs' }
])

const destinationTypeOptions = localizedOptions([
  { value: 'WEBSITE', cn: '网站', en: 'Website' },
  { value: 'APP', cn: '应用', en: 'App' },
  { value: 'MESSENGER', cn: 'Messenger', en: 'Messenger' }
])

const statusOptions = localizedOptions([
  { value: 'PAUSED', cn: '暂停', en: 'Paused' },
  { value: 'ACTIVE', cn: '活跃', en: 'Active' }
])

const adStatusOptions = localizedOptions([
  { value: 'PAUSED', cn: '暂停', en: 'Paused' },
  { value: 'ACTIVE', cn: '活跃', en: 'Active' },
  { value: 'ARCHIVED', cn: '归档', en: 'Archived' },
  { value: 'DELETED', cn: '删除', en: 'Deleted' }
])

const bidStrategyOptions = localizedOptions([
  { value: 'LOWEST_COST_WITHOUT_CAP', cn: '最低成本（无上限）', en: 'Lowest cost without cap' },
  { value: 'COST_CAP', cn: '成本上限', en: 'Cost cap' },
  { value: 'LOWEST_COST_WITH_BID_CAP', cn: '最低成本（有出价上限）', en: 'Lowest cost with bid cap' }
])

const timezoneTypeOptions = localizedOptions([
  { value: 'USER', cn: '用户时区', en: 'User timezone' },
  { value: 'ADVERTISER', cn: '广告主时区', en: 'Advertiser timezone' }
])

const creativeFormatOptions = localizedOptions([
  { value: 'link', cn: '链接广告', en: 'Link ad' },
  { value: 'image', cn: '图片广告', en: 'Image ad' },
  { value: 'video', cn: '视频广告', en: 'Video ad' }
])

const callToActionOptions = localizedOptions([
  { value: 'LEARN_MORE', cn: '了解更多', en: 'Learn more' },
  { value: 'SHOP_NOW', cn: '立即购买', en: 'Shop now' },
  { value: 'SIGN_UP', cn: '注册', en: 'Sign up' },
  { value: 'DOWNLOAD', cn: '下载', en: 'Download' },
  { value: 'CONTACT_US', cn: '联系我们', en: 'Contact us' },
  { value: 'NO_BUTTON', cn: '无按钮', en: 'No button' }
])

const countryOptions = localizedOptions([
  { value: 'US', cn: '美国', en: 'United States' },
  { value: 'CA', cn: '加拿大', en: 'Canada' },
  { value: 'GB', cn: '英国', en: 'United Kingdom' },
  { value: 'AU', cn: '澳大利亚', en: 'Australia' },
  { value: 'CN', cn: '中国', en: 'China' },
  { value: 'JP', cn: '日本', en: 'Japan' },
  { value: 'KR', cn: '韩国', en: 'South Korea' },
  { value: 'SG', cn: '新加坡', en: 'Singapore' },
  { value: 'DE', cn: '德国', en: 'Germany' },
  { value: 'FR', cn: '法国', en: 'France' },
  { value: 'IT', cn: '意大利', en: 'Italy' },
  { value: 'ES', cn: '西班牙', en: 'Spain' },
  { value: 'BR', cn: '巴西', en: 'Brazil' },
  { value: 'IN', cn: '印度', en: 'India' },
  { value: 'MX', cn: '墨西哥', en: 'Mexico' }
])

const genderOptions = computed(() => [
  { value: [1, 2], label: displayText('全部', 'All') },
  { value: [1], label: displayText('男性', 'Male') },
  { value: [2], label: displayText('女性', 'Female') }
])

const showBidAmount = computed(() => {
  return ['COST_CAP', 'LOWEST_COST_WITH_BID_CAP'].includes(formData.value.bidStrategy)
})

const showDailyBudget = computed(() => formData.value.budgetType === 'daily')
const showLifetimeBudget = computed(() => formData.value.budgetType === 'lifetime')

const buildCreativeObjectStorySpec = () => {
  const callToAction = formData.value.creativeCallToAction === 'NO_BUTTON'
    ? undefined
    : {
        type: formData.value.creativeCallToAction,
        value: {
          link: formData.value.creativeLink
        }
      }

  if (formData.value.creativeFormat === 'video') {
    return {
      page_id: formData.value.creativePageId,
      video_data: {
        video_id: formData.value.creativeVideoId,
        title: formData.value.creativeTitle || undefined,
        message: formData.value.creativeBody || undefined,
        call_to_action: callToAction
      }
    }
  }

  return {
    page_id: formData.value.creativePageId,
    link_data: {
      link: formData.value.creativeLink,
      name: formData.value.creativeTitle || undefined,
      message: formData.value.creativeBody || undefined,
      image_hash: formData.value.creativeImageHash || undefined,
      call_to_action: callToAction
    }
  }
}

const parseTrackingSpecs = () => {
  const value = formData.value.trackingSpecs.trim()
  return value ? JSON.parse(value) : null
}

const parseAdLabels = () => {
  return formData.value.adLabels
    .split(',')
    .map(label => label.trim())
    .filter(Boolean)
    .map(name => ({ name }))
}

const toNullableNumber = (value: number | string | null) => {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

const toggleSection = (section: keyof SectionsState) => {
  sections.value[section] = !sections.value[section]
}

const handleClose = () => {
  emit('close')
}

const validateForm = (): boolean => {
  errors.value = {}

  if (!formData.value.adsetName.trim()) {
    errors.value.adsetName = displayText('请输入 AdSet 名称', 'Please enter AdSet name')
  }

  if (formData.value.budgetType === 'daily') {
    if (!formData.value.dailyBudget || formData.value.dailyBudget < 1) {
      errors.value.dailyBudget = displayText('每日预算最低 $1.00', 'Daily budget must be at least $1.00')
    }
  } else {
    if (!formData.value.lifetimeBudget || formData.value.lifetimeBudget < 1) {
      errors.value.lifetimeBudget = displayText('总预算最低 $1.00', 'Lifetime budget must be at least $1.00')
    }
  }

  if (showBidAmount.value) {
    if (!formData.value.bidAmount || formData.value.bidAmount <= 0) {
      errors.value.bidAmount = displayText('请输入有效的出价金额', 'Please enter a valid bid amount')
    }
  }

  if (!formData.value.adName.trim()) {
    errors.value.adName = displayText('请输入 Ad 名称', 'Please enter Ad name')
  }

  if (!formData.value.creativeName.trim()) {
    errors.value.creativeName = displayText('请输入 Creative 名称', 'Please enter Creative name')
  }

  if (!formData.value.creativePageId.trim()) {
    errors.value.creativePageId = displayText('请输入 Facebook Page ID', 'Please enter Facebook Page ID')
  }

  if (!formData.value.creativeLink.trim()) {
    errors.value.creativeLink = displayText('请输入目标链接', 'Please enter destination URL')
  }

  if (formData.value.creativeFormat === 'image' && !formData.value.creativeImageHash.trim()) {
    errors.value.creativeImageHash = displayText('图片广告需要 Image Hash', 'Image ads require Image Hash')
  }

  if (formData.value.creativeFormat === 'video' && !formData.value.creativeVideoId.trim()) {
    errors.value.creativeVideoId = displayText('视频广告需要 Video ID', 'Video ads require Video ID')
  }

  const adBidAmount = toNullableNumber(formData.value.adBidAmount)
  const displaySequence = toNullableNumber(formData.value.displaySequence)

  if (adBidAmount !== null && adBidAmount <= 0) {
    errors.value.adBidAmount = displayText('请输入有效的 Ad 出价金额', 'Please enter a valid Ad bid amount')
  }

  if (displaySequence !== null && displaySequence < 0) {
    errors.value.displaySequence = displayText('展示顺序不能小于 0', 'Display sequence cannot be less than 0')
  }

  if (formData.value.adScheduleStartTime && formData.value.adScheduleEndTime) {
    if (formData.value.adScheduleStartTime >= formData.value.adScheduleEndTime) {
      errors.value.adScheduleEndTime = displayText('结束时间必须晚于开始时间', 'End time must be later than start time')
    }
  }

  try {
    parseTrackingSpecs()
  } catch {
    errors.value.trackingSpecs = displayText('Tracking Specs 必须是合法 JSON', 'Tracking Specs must be valid JSON')
  }
  
  return Object.keys(errors.value).length === 0
}

const handleSave = async () => {
  if (!validateForm()) {
    return
  }

  submitting.value = true

  try {
    const adLabels = parseAdLabels()
    const creativeObjectStorySpec = buildCreativeObjectStorySpec()
    const adBidAmount = toNullableNumber(formData.value.adBidAmount)

    const payload = {
      campaign_id: props.campaignId,
      name: formData.value.adsetName,
      optimization_goal: formData.value.optimizationGoal,
      billing_event: formData.value.billingEvent,
      destination_type: formData.value.destinationType,
      status: formData.value.status,
      budget_type: formData.value.budgetType,
      daily_budget: formData.value.budgetType === 'daily' && formData.value.dailyBudget
        ? Math.round(formData.value.dailyBudget * 100)
        : null,
      lifetime_budget: formData.value.budgetType === 'lifetime' && formData.value.lifetimeBudget
        ? Math.round(formData.value.lifetimeBudget * 100)
        : null,
      bid_strategy: formData.value.bidStrategy,
      bid_amount: formData.value.bidAmount ? Math.round(formData.value.bidAmount * 100) : null,
      start_time: formData.value.startTime || null,
      end_time: formData.value.endTime || null,
      timezone_type: formData.value.timezoneType,
      targeting: {
        age_min: formData.value.ageMin,
        age_max: formData.value.ageMax,
        genders: JSON.stringify(formData.value.genders),
        targeting_spec: JSON.stringify({
          age_min: formData.value.ageMin,
          age_max: formData.value.ageMax,
          genders: formData.value.genders,
          geo_locations: { countries: formData.value.geoCountries }
        })
      },
      promoted_object: formData.value.pixelId ? {
        pixel_id: formData.value.pixelId,
        custom_event_type: formData.value.customEventType,
        application_id: formData.value.applicationId,
        page_id: formData.value.pageId
      } : null,
      ad: {
        name: formData.value.adName,
        status: formData.value.adStatus,
        bid_amount: adBidAmount
          ? Math.round(adBidAmount * 100)
          : null,
        tracking_specs: parseTrackingSpecs(),
        conversion_domain: formData.value.conversionDomain || null,
        adlabels: adLabels.length > 0 ? adLabels : null,
        ad_schedule_start_time: formData.value.adScheduleStartTime || null,
        ad_schedule_end_time: formData.value.adScheduleEndTime || null,
        display_sequence: toNullableNumber(formData.value.displaySequence),
        creative: {
          name: formData.value.creativeName,
          format: formData.value.creativeFormat,
          title: formData.value.creativeTitle || null,
          body: formData.value.creativeBody || null,
          image_hash: formData.value.creativeImageHash || null,
          video_id: formData.value.creativeVideoId || null,
          link: formData.value.creativeLink,
          call_to_action: formData.value.creativeCallToAction,
          page_id: formData.value.creativePageId,
          instagram_actor_id: formData.value.creativeInstagramActorId || null,
          object_story_spec: JSON.stringify(creativeObjectStorySpec)
        }
      }
    }

    emit('submit', payload)
    emit('close')
  } catch (err: any) {
    console.error('创建 AdSet 失败:', err)
    errors.value.submit = err.message || displayText('创建失败，请重试', 'Creation failed, please try again')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Transition name="fade">
    <div
      v-if="show"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
      @click.self="handleClose"
    >
      <Transition name="slide">
        <div
          v-if="show"
          class="fixed right-0 top-0 h-full bg-white dark:bg-slate-800 shadow-2xl w-full max-w-[600px] overflow-hidden flex flex-col rounded-l-md"
        >
          <div class="flex items-center justify-between px-[15px] py-[10px] border-b border-slate-200 dark:border-slate-700">
            <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">
              {{ displayText('创建 AdUnit（广告单元）', 'Create AdUnit') }}
            </h3>
            <button
              type="button"
              class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
              @click="handleClose"
            >
              <span class="material-symbols-outlined text-[18px]">close</span>
            </button>
          </div>

          <div class="flex-1 overflow-y-auto px-[15px] py-[12px]">
            <div v-if="errors.submit" class="mb-[10px] p-[8px] rounded-md bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
              <div class="flex items-center gap-[6px]">
                <span class="material-symbols-outlined text-red-600 dark:text-red-400 text-[14px]">error</span>
                <span class="text-[9px] text-red-600 dark:text-red-400">{{ errors.submit }}</span>
              </div>
            </div>

            <!-- 说明文字 -->
            <div class="mb-[13px] p-[10px] bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-200 dark:border-blue-800">
              <p class="text-[10px] text-blue-700 dark:text-blue-300 leading-relaxed">
                <strong class="text-blue-800 dark:text-blue-200">{{ displayText('AdSet 配置说明', 'AdSet setup guide') }}</strong><br>
                {{ displayText('AdSet 对应 Meta 广告组层级，包含定向、预算、出价、排期等配置。请按需展开各个配置模块。', 'AdSet maps to the Meta ad set level and includes targeting, budget, bid, and schedule settings. Expand each section as needed.') }}
              </p>
            </div>

            <div class="flex items-center gap-[10px] py-[10px]">
                <div class="h-px flex-1 bg-slate-200 dark:bg-slate-700"></div>
                <span class="text-[9px] font-medium text-slate-500 dark:text-slate-400">
                   {{ displayText('AdUnit 配置', 'AdUnit settings') }}
                </span>
                <div class="h-px flex-1 bg-slate-200 dark:bg-slate-700"></div>
            </div>

            <form @submit.prevent="handleSave" class="space-y-[10px]">
              <!-- 1️⃣ 基本信息 -->
              <div class="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
                <button
                  type="button"
                  class="w-full flex items-center justify-between px-[12px] py-[8px] bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  @click="toggleSection('basic')"
                >
                  <div class="flex items-center gap-[8px]">
                    <span class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ displayText('基本信息', 'Basic information') }}</span>
                    <span class="text-[9px] text-slate-500 dark:text-slate-400">{{ displayText('（必填）', '(Required)') }}</span>
                  </div>
                  <span class="material-symbols-outlined text-[16px] text-slate-400 transition-transform" :class="{ 'rotate-180': sections.basic }">
                    expand_more
                  </span>
                </button>

                <Transition name="collapse">
                  <div v-show="sections.basic" class="p-[12px] bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
                    <div class="grid grid-cols-2 gap-[10px]">
                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('AdSet 名称', 'AdSet name') }} *
                        </label>
                        <input
                          v-model="formData.adsetName"
                          type="text"
                          placeholder="US_Android_Install_AdSet_001"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                          :class="{ 'border-red-500': errors.adsetName }"
                        />
                        <p v-if="errors.adsetName" class="mt-[3px] text-[8px] text-red-500">{{ errors.adsetName }}</p>
                      </div>

                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('优化目标', 'Optimization goal') }} *
                        </label>
                        <select
                          v-model="formData.optimizationGoal"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option v-for="opt in optimizationGoalOptions" :key="opt.value" :value="opt.value">
                            {{ opt.label }}
                          </option>
                        </select>
                      </div>

                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('计费事件', 'Billing event') }} *
                        </label>
                        <select
                          v-model="formData.billingEvent"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option v-for="opt in billingEventOptions" :key="opt.value" :value="opt.value">
                            {{ opt.label }}
                          </option>
                        </select>
                      </div>

                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('目标类型', 'Destination type') }}
                        </label>
                        <select
                          v-model="formData.destinationType"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option v-for="opt in destinationTypeOptions" :key="opt.value" :value="opt.value">
                            {{ opt.label }}
                          </option>
                        </select>
                      </div>

                      <div class="col-span-2">
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('状态', 'Status') }} *
                        </label>
                        <select
                          v-model="formData.status"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option v-for="opt in statusOptions" :key="opt.value" :value="opt.value">
                            {{ opt.label }}
                          </option>
                        </select>
                      </div>
                    </div>
                  </div>
                </Transition>
              </div>

              <!-- 2️⃣ 预算与出价 -->
              <div class="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
                <button
                  type="button"
                  class="w-full flex items-center justify-between px-[12px] py-[8px] bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  @click="toggleSection('budget')"
                >
                  <div class="flex items-center gap-[8px]">
                    <span class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ displayText('预算与出价', 'Budget and bid') }}</span>
                    <span class="text-[9px] text-slate-500 dark:text-slate-400">{{ displayText('（必填）', '(Required)') }}</span>
                  </div>
                  <span class="material-symbols-outlined text-[16px] text-slate-400 transition-transform" :class="{ 'rotate-180': sections.budget }">
                    expand_more
                  </span>
                </button>

                <Transition name="collapse">
                  <div v-show="sections.budget" class="p-[12px] bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
                    <div class="space-y-[10px]">
                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('预算类型', 'Budget type') }} *
                        </label>
                        <div class="flex gap-[10px]">
                          <label class="flex items-center gap-[5px] cursor-pointer">
                            <input type="radio" v-model="formData.budgetType" value="daily" class="w-[14px] h-[14px]" />
                            <span class="text-[9px] text-slate-700 dark:text-slate-300">{{ displayText('每日预算', 'Daily budget') }}</span>
                          </label>
                          <label class="flex items-center gap-[5px] cursor-pointer">
                            <input type="radio" v-model="formData.budgetType" value="lifetime" class="w-[14px] h-[14px]" />
                            <span class="text-[9px] text-slate-700 dark:text-slate-300">{{ displayText('总预算', 'Lifetime budget') }}</span>
                          </label>
                        </div>
                      </div>

                      <div v-if="showDailyBudget">
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('每日预算', 'Daily budget') }} * <span class="text-slate-500">(USD)</span>
                        </label>
                        <div class="relative">
                          <span class="absolute left-[8px] top-[6px] text-[9px] text-slate-500">$</span>
                          <input
                            v-model.number="formData.dailyBudget"
                            type="number"
                            step="1"
                            min="1"
                            placeholder="100.00"
                            class="w-full pl-[20px] pr-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            :class="{ 'border-red-500': errors.dailyBudget }"
                          />
                        </div>
                        <p v-if="errors.dailyBudget" class="mt-[3px] text-[8px] text-red-500">{{ errors.dailyBudget }}</p>
                        <p class="mt-[3px] text-[8px] text-slate-500">{{ displayText('最低 $1.00', 'Minimum $1.00') }}</p>
                      </div>

                      <div v-if="showLifetimeBudget">
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('总预算', 'Lifetime budget') }} * <span class="text-slate-500">(USD)</span>
                        </label>
                        <div class="relative">
                          <span class="absolute left-[8px] top-[6px] text-[9px] text-slate-500">$</span>
                          <input
                            v-model.number="formData.lifetimeBudget"
                            type="number"
                            step="1"
                            min="1"
                            placeholder="1000.00"
                            class="w-full pl-[20px] pr-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            :class="{ 'border-red-500': errors.lifetimeBudget }"
                          />
                        </div>
                        <p v-if="errors.lifetimeBudget" class="mt-[3px] text-[8px] text-red-500">{{ errors.lifetimeBudget }}</p>
                        <p class="mt-[3px] text-[8px] text-slate-500">{{ displayText('最低 $1.00', 'Minimum $1.00') }}</p>
                      </div>

                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('出价策略', 'Bid strategy') }} *
                        </label>
                        <select
                          v-model="formData.bidStrategy"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option v-for="opt in bidStrategyOptions" :key="opt.value" :value="opt.value">
                            {{ opt.label }}
                          </option>
                        </select>
                      </div>

                      <div v-if="showBidAmount">
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('出价金额', 'Bid amount') }} * <span class="text-slate-500">(USD)</span>
                        </label>
                        <div class="relative">
                          <span class="absolute left-[8px] top-[6px] text-[9px] text-slate-500">$</span>
                          <input
                            v-model.number="formData.bidAmount"
                            type="number"
                            step="0.01"
                            min="0.01"
                            placeholder="5.00"
                            class="w-full pl-[20px] pr-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            :class="{ 'border-red-500': errors.bidAmount }"
                          />
                        </div>
                        <p v-if="errors.bidAmount" class="mt-[3px] text-[8px] text-red-500">{{ errors.bidAmount }}</p>
                      </div>
                    </div>
                  </div>
                </Transition>
              </div>

              <!-- 3️⃣ 投放周期 -->
              <div class="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
                <button
                  type="button"
                  class="w-full flex items-center justify-between px-[12px] py-[8px] bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  @click="toggleSection('schedule')"
                >
                  <div class="flex items-center gap-[8px]">
                    <span class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ displayText('投放周期', 'Schedule') }}</span>
                    <span class="text-[9px] text-slate-500 dark:text-slate-400">{{ displayText('（可选）', '(Optional)') }}</span>
                  </div>
                  <span class="material-symbols-outlined text-[16px] text-slate-400 transition-transform" :class="{ 'rotate-180': sections.schedule }">
                    expand_more
                  </span>
                </button>

                <Transition name="collapse">
                  <div v-show="sections.schedule" class="p-[12px] bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
                    <div class="grid grid-cols-2 gap-[10px]">
                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('开始时间', 'Start time') }}
                        </label>
                        <input
                          v-model="formData.startTime"
                          type="datetime-local"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <p class="mt-[3px] text-[8px] text-slate-500">{{ displayText('留空表示立即开始', 'Leave blank to start immediately') }}</p>
                      </div>

                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('结束时间', 'End time') }}
                        </label>
                        <input
                          v-model="formData.endTime"
                          type="datetime-local"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <p class="mt-[3px] text-[8px] text-slate-500">{{ displayText('留空表示持续投放', 'Leave blank to run continuously') }}</p>
                      </div>

                      <div class="col-span-2">
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('时区设置', 'Timezone setting') }}
                        </label>
                        <select
                          v-model="formData.timezoneType"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option v-for="opt in timezoneTypeOptions" :key="opt.value" :value="opt.value">
                            {{ opt.label }}
                          </option>
                        </select>
                      </div>
                    </div>
                  </div>
                </Transition>
              </div>

              <!-- 4️⃣ 受众定向 -->
              <div class="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
                <button
                  type="button"
                  class="w-full flex items-center justify-between px-[12px] py-[8px] bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  @click="toggleSection('targeting')"
                >
                  <div class="flex items-center gap-[8px]">
                    <span class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ displayText('受众定向', 'Audience targeting') }}</span>
                    <span class="text-[9px] text-slate-500 dark:text-slate-400">{{ displayText('（可选）', '(Optional)') }}</span>
                  </div>
                  <span class="material-symbols-outlined text-[16px] text-slate-400 transition-transform" :class="{ 'rotate-180': sections.targeting }">
                    expand_more
                  </span>
                </button>

                <Transition name="collapse">
                  <div v-show="sections.targeting" class="p-[12px] bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
                    <div class="space-y-[10px]">
                      <!-- 年龄范围 -->
                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('年龄范围', 'Age range') }}
                        </label>
                        <div class="flex items-center gap-[8px]">
                          <input
                            v-model.number="formData.ageMin"
                            type="number"
                            min="18"
                            max="65"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                          <span class="text-[9px] text-slate-500">-</span>
                          <input
                            v-model.number="formData.ageMax"
                            type="number"
                            min="18"
                            max="65"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                        <p class="mt-[3px] text-[8px] text-slate-500">{{ displayText('年龄范围：18-65 岁', 'Age range: 18-65') }}</p>
                      </div>

                      <!-- 性别 -->
                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('性别', 'Gender') }}
                        </label>
                        <select
                          v-model="formData.genders"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option v-for="opt in genderOptions" :key="opt.label" :value="opt.value">
                            {{ opt.label }}
                          </option>
                        </select>
                      </div>

                      <!-- 地理位置 -->
                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('国家/地区', 'Countries/regions') }}
                        </label>
                        <div class="max-h-[120px] overflow-y-auto border border-slate-300 dark:border-slate-600 rounded-md p-[8px] bg-white dark:bg-slate-900">
                          <div class="grid grid-cols-2 gap-[6px]">
                            <label
                              v-for="country in countryOptions"
                              :key="country.value"
                              class="flex items-center gap-[5px] cursor-pointer"
                            >
                              <input
                                v-model="formData.geoCountries"
                                type="checkbox"
                                :value="country.value"
                                class="w-[14px] h-[14px]"
                              />
                              <span class="text-[9px] text-slate-700 dark:text-slate-300">{{ country.label }}</span>
                            </label>
                          </div>
                        </div>
                        <p v-if="formData.geoCountries.length > 0" class="mt-[3px] text-[8px] text-slate-600 dark:text-slate-400">
                          {{ displayText('已选', 'Selected') }} {{ formData.geoCountries.length }} {{ displayText('个', '') }}: {{ formData.geoCountries.join(' / ') }}
                        </p>
                        <p v-else class="mt-[3px] text-[8px] text-slate-500">{{ displayText('请选择国家/地区', 'Select countries/regions') }}</p>
                      </div>
                    </div>
                  </div>
                </Transition>
              </div>

              <!-- 5️⃣ 推广对象配置 -->
              <div class="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
                <button
                  type="button"
                  class="w-full flex items-center justify-between px-[12px] py-[8px] bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  @click="toggleSection('promotedObject')"
                >
                  <div class="flex items-center gap-[8px]">
                    <span class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ displayText('推广对象配置', 'Promoted object') }}</span>
                    <span class="text-[9px] text-slate-500 dark:text-slate-400">{{ displayText('（可选）', '(Optional)') }}</span>
                  </div>
                  <span class="material-symbols-outlined text-[16px] text-slate-400 transition-transform" :class="{ 'rotate-180': sections.promotedObject }">
                    expand_more
                  </span>
                </button>

                <Transition name="collapse">
                  <div v-show="sections.promotedObject" class="p-[12px] bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
                    <div class="space-y-[10px]">
                      <!-- Pixel ID -->
                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          Pixel ID
                        </label>
                        <input
                          v-model="formData.pixelId"
                          type="text"
                          placeholder="123456789012345"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <p class="mt-[3px] text-[8px] text-slate-500">{{ displayText('Meta Pixel ID，用于追踪网站转化', 'Meta Pixel ID for tracking website conversions') }}</p>
                      </div>

                      <!-- 转化事件 -->
                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          {{ displayText('转化事件', 'Conversion event') }}
                        </label>
                        <input
                          v-model="formData.customEventType"
                          type="text"
                          placeholder="Purchase / AddToCart / Lead"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                        <p class="mt-[3px] text-[8px] text-slate-500">{{ displayText('自定义转化事件名称', 'Custom conversion event name') }}</p>
                      </div>

                      <!-- Application ID -->
                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          Application ID
                        </label>
                        <input
                          v-model="formData.applicationId"
                          type="text"
                          :placeholder="displayText('用于应用推广', 'For app promotion')"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>

                      <!-- Page ID -->
                      <div>
                        <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                          Page ID
                        </label>
                        <input
                          v-model="formData.pageId"
                          type="text"
                          :placeholder="displayText('Facebook 主页 ID', 'Facebook Page ID')"
                          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </div>
                  </div>
                </Transition>
              </div>

              <div class="flex items-center gap-[10px] py-[4px]">
                <div class="h-px flex-1 bg-slate-200 dark:bg-slate-700"></div>
                <span class="text-[9px] font-medium text-slate-500 dark:text-slate-400">
                   {{ displayText('Ads 配置', 'Ads settings') }}
                </span>
                <div class="h-px flex-1 bg-slate-200 dark:bg-slate-700"></div>
              </div>

              <!-- 6️⃣ Ads 配置 -->
              <div class="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
                <button
                  type="button"
                  class="w-full flex items-center justify-between px-[12px] py-[8px] bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                  @click="toggleSection('ads')"
                >
                  <div class="flex items-center gap-[8px]">
                    <span class="text-[11px] font-semibold text-slate-900 dark:text-white">{{ displayText('Ads 配置', 'Ads settings') }}</span>
                    <span class="text-[9px] text-slate-500 dark:text-slate-400">{{ displayText('（必填核心 + 重要可选）', '(Required core + important optional)') }}</span>
                  </div>
                  <span class="material-symbols-outlined text-[16px] text-slate-400 transition-transform" :class="{ 'rotate-180': sections.ads }">
                    expand_more
                  </span>
                </button>

                <Transition name="collapse">
                  <div v-show="sections.ads" class="p-[12px] bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700">
                    <div class="space-y-[12px]">
                      <div class="grid grid-cols-2 gap-[10px]">
                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('Ad 名称', 'Ad name') }} *
                          </label>
                          <input
                            v-model="formData.adName"
                            type="text"
                            placeholder="US_Android_Install_Ad_001"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            :class="{ 'border-red-500': errors.adName }"
                          />
                          <p v-if="errors.adName" class="mt-[3px] text-[8px] text-red-500">{{ errors.adName }}</p>
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('Ad 状态', 'Ad status') }} *
                          </label>
                          <select
                            v-model="formData.adStatus"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            <option v-for="opt in adStatusOptions" :key="opt.value" :value="opt.value">
                              {{ opt.label }}
                            </option>
                          </select>
                        </div>
                      </div>

                      <div class="grid grid-cols-2 gap-[10px]">
                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('Creative 名称', 'Creative name') }} *
                          </label>
                          <input
                            v-model="formData.creativeName"
                            type="text"
                            placeholder="Creative_001"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            :class="{ 'border-red-500': errors.creativeName }"
                          />
                          <p v-if="errors.creativeName" class="mt-[3px] text-[8px] text-red-500">{{ errors.creativeName }}</p>
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('Creative 类型', 'Creative type') }} *
                          </label>
                          <select
                            v-model="formData.creativeFormat"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            <option v-for="opt in creativeFormatOptions" :key="opt.value" :value="opt.value">
                              {{ opt.label }}
                            </option>
                          </select>
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            Facebook Page ID *
                          </label>
                          <input
                            v-model="formData.creativePageId"
                            type="text"
                            placeholder="123456789012345"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            :class="{ 'border-red-500': errors.creativePageId }"
                          />
                          <p v-if="errors.creativePageId" class="mt-[3px] text-[8px] text-red-500">{{ errors.creativePageId }}</p>
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('目标链接', 'Destination URL') }} *
                          </label>
                          <input
                            v-model="formData.creativeLink"
                            type="url"
                            placeholder="https://example.com"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            :class="{ 'border-red-500': errors.creativeLink }"
                          />
                          <p v-if="errors.creativeLink" class="mt-[3px] text-[8px] text-red-500">{{ errors.creativeLink }}</p>
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('标题', 'Title') }}
                          </label>
                          <input
                            v-model="formData.creativeTitle"
                            type="text"
                            :placeholder="displayText('广告标题', 'Ad title')"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            CTA
                          </label>
                          <select
                            v-model="formData.creativeCallToAction"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            <option v-for="opt in callToActionOptions" :key="opt.value" :value="opt.value">
                              {{ opt.label }}
                            </option>
                          </select>
                        </div>

                        <div v-if="formData.creativeFormat === 'image'">
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            Image Hash *
                          </label>
                          <input
                            v-model="formData.creativeImageHash"
                            type="text"
                            :placeholder="displayText('Meta 图片哈希', 'Meta image hash')"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            :class="{ 'border-red-500': errors.creativeImageHash }"
                          />
                          <p v-if="errors.creativeImageHash" class="mt-[3px] text-[8px] text-red-500">{{ errors.creativeImageHash }}</p>
                        </div>

                        <div v-if="formData.creativeFormat === 'video'">
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            Video ID *
                          </label>
                          <input
                            v-model="formData.creativeVideoId"
                            type="text"
                            :placeholder="displayText('Meta 视频 ID', 'Meta video ID')"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            :class="{ 'border-red-500': errors.creativeVideoId }"
                          />
                          <p v-if="errors.creativeVideoId" class="mt-[3px] text-[8px] text-red-500">{{ errors.creativeVideoId }}</p>
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            Instagram Actor ID
                          </label>
                          <input
                            v-model="formData.creativeInstagramActorId"
                            type="text"
                            :placeholder="displayText('Instagram 账户 ID', 'Instagram account ID')"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>

                        <div class="col-span-2">
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('正文', 'Body') }}
                          </label>
                          <textarea
                            v-model="formData.creativeBody"
                            rows="3"
                            :placeholder="displayText('广告正文', 'Ad body')"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                          />
                        </div>
                      </div>

                      <div class="grid grid-cols-2 gap-[10px]">
                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('Ad 出价', 'Ad bid') }} <span class="text-slate-500">(USD)</span>
                          </label>
                          <div class="relative">
                            <span class="absolute left-[8px] top-[6px] text-[9px] text-slate-500">$</span>
                            <input
                              v-model.number="formData.adBidAmount"
                              type="number"
                              step="0.01"
                              min="0.01"
                              :placeholder="displayText('留空继承 AdSet', 'Leave blank to inherit AdSet')"
                              class="w-full pl-[20px] pr-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                              :class="{ 'border-red-500': errors.adBidAmount }"
                            />
                          </div>
                          <p v-if="errors.adBidAmount" class="mt-[3px] text-[8px] text-red-500">{{ errors.adBidAmount }}</p>
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('展示顺序', 'Display sequence') }}
                          </label>
                          <input
                            v-model.number="formData.displaySequence"
                            type="number"
                            min="0"
                            placeholder="0"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            :class="{ 'border-red-500': errors.displaySequence }"
                          />
                          <p v-if="errors.displaySequence" class="mt-[3px] text-[8px] text-red-500">{{ errors.displaySequence }}</p>
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('Ad 开始时间', 'Ad start time') }}
                          </label>
                          <input
                            v-model="formData.adScheduleStartTime"
                            type="datetime-local"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('Ad 结束时间', 'Ad end time') }}
                          </label>
                          <input
                            v-model="formData.adScheduleEndTime"
                            type="datetime-local"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                            :class="{ 'border-red-500': errors.adScheduleEndTime }"
                          />
                          <p v-if="errors.adScheduleEndTime" class="mt-[3px] text-[8px] text-red-500">{{ errors.adScheduleEndTime }}</p>
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('转化域名', 'Conversion domain') }}
                          </label>
                          <input
                            v-model="formData.conversionDomain"
                            type="text"
                            placeholder="example.com"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>

                        <div>
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            {{ displayText('广告标签', 'Ad labels') }}
                          </label>
                          <input
                            v-model="formData.adLabels"
                            type="text"
                            placeholder="install, android, us"
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          />
                        </div>

                        <div class="col-span-2">
                          <label class="block text-[9px] font-medium text-slate-700 dark:text-slate-300 mb-[5px]">
                            Tracking Specs JSON
                          </label>
                          <textarea
                            v-model="formData.trackingSpecs"
                            rows="3"
                            placeholder='{"action.type":["offsite_conversion"],"fb_pixel":["123456789012345"]}'
                            class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                            :class="{ 'border-red-500': errors.trackingSpecs }"
                          />
                          <p v-if="errors.trackingSpecs" class="mt-[3px] text-[8px] text-red-500">{{ errors.trackingSpecs }}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </Transition>
              </div>

            </form>
          </div>

          <div class="flex items-center justify-end gap-[8px] px-[15px] py-[10px] border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              class="px-[12px] py-[6px] text-[11px] font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-md hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
              @click="handleClose"
              :disabled="submitting"
            >
              {{ displayText('取消', 'Cancel') }}
            </button>
            <button
              type="button"
              class="px-[12px] py-[6px] text-[11px] font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              @click="handleSave"
              :disabled="submitting"
            >
              {{ submitting ? displayText('创建中...', 'Creating...') : displayText('创建 AdSet', 'Create AdSet') }}
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
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

.collapse-enter-active,
.collapse-leave-active {
  transition: all 0.3s ease;
  max-height: 1000px;
  overflow: hidden;
}

.collapse-enter-from,
.collapse-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
