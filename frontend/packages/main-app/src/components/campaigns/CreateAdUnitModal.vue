<script setup lang="ts">
import { ref, watch } from 'vue'

interface Props {
  show: boolean
  campaignId: string
}

interface Emits {
  (e: 'close'): void
  (e: 'submit', data: any): void
}

interface FormData {
  taskName: string
  adsetName: string
  conversionLocation: string
  pixelAppPage: string
  conversionEvent: string
  performanceGoal: string
  attribution: string
  budget: string
  schedule: string
  targeting: string
  placements: string
  status: string
  adName: string
  adFormat: string
  material: string
  copy: string
  adStatus: string
  owner: string
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const formData = ref<FormData>({
  taskName: '',
  adsetName: '',
  conversionLocation: 'Website',
  pixelAppPage: '',
  conversionEvent: 'Purchase',
  performanceGoal: 'Maximize conversions',
  attribution: '7-day click, 1-day view',
  budget: '',
  schedule: '',
  targeting: '',
  placements: 'Automatic',
  status: 'Draft',
  adName: '',
  adFormat: 'Single image',
  material: '',
  copy: '',
  adStatus: 'Draft',
  owner: ''
})

const errors = ref<Record<string, string>>({})
const submitting = ref(false)

// 配置选项
const conversionLocationOptions = ['Website', 'App', 'Messenger', 'WhatsApp']
const conversionEventOptions = ['Purchase', 'Add to cart', 'Lead', 'Complete registration', 'View content']
const performanceGoalOptions = ['Maximize conversions', 'Maximize conversion value', 'Cost per result goal']
const attributionOptions = ['7-day click, 1-day view', '1-day click', '7-day click']
const placementOptions = ['Automatic', 'Manual', 'Facebook Feed', 'Instagram Feed', 'Stories', 'Reels']
const statusOptions = ['Draft', 'Learning', 'Active', 'Paused']
const adFormatOptions = ['Single image', 'Single video', 'Carousel', 'Collection']
const adStatusOptions = ['Draft', 'Review', 'Active', 'Paused']

// 验证表单
const validateForm = (): boolean => {
  errors.value = {}

  if (!formData.value.taskName.trim()) {
    errors.value.taskName = '请输入任务名称'
  }

  if (!formData.value.adsetName.trim()) {
    errors.value.adsetName = '请输入 Ad Set 名称'
  }

  if (!formData.value.budget || parseFloat(formData.value.budget) <= 0) {
    errors.value.budget = '请输入有效的预算金额'
  }

  if (!formData.value.adName.trim()) {
    errors.value.adName = '请输入广告名称'
  }

  return Object.keys(errors.value).length === 0
}

// 重置表单
const resetForm = () => {
  formData.value = {
    taskName: '',
    adsetName: '',
    conversionLocation: 'Website',
    pixelAppPage: '',
    conversionEvent: 'Purchase',
    performanceGoal: 'Maximize conversions',
    attribution: '7-day click, 1-day view',
    budget: '',
    schedule: '',
    targeting: '',
    placements: 'Automatic',
    status: 'Draft',
    adName: '',
    adFormat: 'Single image',
    material: '',
    copy: '',
    adStatus: 'Draft',
    owner: ''
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
  emit('submit', formData.value)
}

// 监听提交完成
defineExpose({
  resetForm,
  setSubmitting: (value: boolean) => {
    submitting.value = value
  }
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
          class="fixed right-0 top-0 h-full bg-white dark:bg-slate-800 shadow-2xl w-full max-w-[600px] overflow-hidden flex flex-col rounded-l-md"
        >
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between px-[15px] py-[10px] border-b border-slate-200 dark:border-slate-700">
            <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">
              创建广告单元 (Ad Unit)
            </h3>
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
                <strong class="text-slate-700 dark:text-slate-300">Ad Unit 配置</strong><br>
                对应 Meta 广告组Ad Set层级，包含定向、预算、排期等配置。下层 Ad 对应具体的广告素材。
              </p>
            </div>

            <!-- 表单 -->
            <form @submit.prevent="handleSave" class="space-y-[10px]">
              <!-- 任务与 Ad Set 配置 -->
              <div class="space-y-[10px]">
                <h4 class="text-[11px] font-semibold text-slate-900 dark:text-white">任务与 Ad Unit 配置</h4>

                <div class="grid grid-cols-2 gap-[10px]">
                  <!-- 任务名称 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      任务名称 * <span class="text-slate-500">(Task Name)</span>
                    </label>
                    <input
                      v-model="formData.taskName"
                      type="text"
                      placeholder="输入任务名称"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                      :class="{ 'border-red-500': errors.taskName }"
                    />
                    <p v-if="errors.taskName" class="mt-[3px] text-[8px] text-red-500">{{ errors.taskName }}</p>
                  </div>

                  <!-- Ad Set 名称 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      Ad Set 名称 * <span class="text-slate-500">(Ad Set Name)</span>
                    </label>
                    <input
                      v-model="formData.adsetName"
                      type="text"
                      placeholder="输入 Ad Set 名称"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                      :class="{ 'border-red-500': errors.adsetName }"
                    />
                    <p v-if="errors.adsetName" class="mt-[3px] text-[8px] text-red-500">{{ errors.adsetName }}</p>
                  </div>

                  <!-- 转化位置 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      转化位置 <span class="text-slate-500">(Conversion Location)</span>
                    </label>
                    <select
                      v-model="formData.conversionLocation"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option v-for="opt in conversionLocationOptions" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                  </div>

                  <!-- Pixel/App/Page -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      Pixel/App/Page <span class="text-slate-500">(Tracking ID)</span>
                    </label>
                    <input
                      v-model="formData.pixelAppPage"
                      type="text"
                      placeholder="输入 Pixel/App/Page"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <!-- 转化事件 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      转化事件 <span class="text-slate-500">(Conversion Event)</span>
                    </label>
                    <select
                      v-model="formData.conversionEvent"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option v-for="opt in conversionEventOptions" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                  </div>

                  <!-- 效果目标 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      效果目标 <span class="text-slate-500">(Performance Goal)</span>
                    </label>
                    <select
                      v-model="formData.performanceGoal"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option v-for="opt in performanceGoalOptions" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                  </div>

                  <!-- 归因设置 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      归因设置 <span class="text-slate-500">(Attribution Setting)</span>
                    </label>
                    <select
                      v-model="formData.attribution"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option v-for="opt in attributionOptions" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                  </div>

                  <!-- 预算 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      预算 * <span class="text-slate-500">(Budget USD)</span>
                    </label>
                    <input
                      v-model="formData.budget"
                      type="text"
                      placeholder="例如 500"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                      :class="{ 'border-red-500': errors.budget }"
                    />
                    <p v-if="errors.budget" class="mt-[3px] text-[8px] text-red-500">{{ errors.budget }}</p>
                  </div>

                  <!-- 排期 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      排期 <span class="text-slate-500">(Schedule)</span>
                    </label>
                    <input
                      v-model="formData.schedule"
                      type="text"
                      placeholder="例如 2024-01-01 至 2024-01-31"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <!-- 定向 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      定向 <span class="text-slate-500">(Targeting)</span>
                    </label>
                    <input
                      v-model="formData.targeting"
                      type="text"
                      placeholder="国家；年龄；语言；受众"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <!-- 版位 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      版位 <span class="text-slate-500">(Placements/Network)</span>
                    </label>
                    <select
                      v-model="formData.placements"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option v-for="opt in placementOptions" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                  </div>

                  <!-- 状态 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      状态 <span class="text-slate-500">(Status)</span>
                    </label>
                    <select
                      v-model="formData.status"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option v-for="opt in statusOptions" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                  </div>
                </div>
              </div>

              <!-- 广告素材配置 -->
              <div class="space-y-[10px]">
                <h4 class="text-[11px] font-semibold text-slate-900 dark:text-white">广告素材配置</h4>

                <div class="grid grid-cols-2 gap-[10px]">
                  <!-- 广告名称 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      素材/广告名称 * <span class="text-slate-500">(Ad Name)</span>
                    </label>
                    <input
                      v-model="formData.adName"
                      type="text"
                      placeholder="输入广告名称"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                      :class="{ 'border-red-500': errors.adName }"
                    />
                    <p v-if="errors.adName" class="mt-[3px] text-[8px] text-red-500">{{ errors.adName }}</p>
                  </div>

                  <!-- 素材格式 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      素材格式 <span class="text-slate-500">(Ad Format)</span>
                    </label>
                    <select
                      v-model="formData.adFormat"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option v-for="opt in adFormatOptions" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                  </div>

                  <!-- 素材名称 -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      素材名称 <span class="text-slate-500">(Material Name)</span>
                    </label>
                    <input
                      v-model="formData.material"
                      type="text"
                      placeholder="输入素材名称"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  <!-- 文案/CTA -->
                  <div>
                    <label class="block text-[9px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                      文案/CTA <span class="text-slate-500">(Copy/CTA)</span>
                    </label>
                    <input
                      v-model="formData.copy"
                      type="text"
                      placeholder="输入文案或 CTA"
                      class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[9px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                </div>
              </div>
            </form>
          </div>

          <!-- 弹窗底部 -->
          <div class="flex items-center justify-end gap-[8px] px-[15px] py-[10px] border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              class="px-[12px] py-[6px] text-[11px] font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-md hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
              @click="handleClose"
              :disabled="submitting"
            >
              取消
            </button>
            <button
              type="button"
              class="px-[12px] py-[6px] text-[11px] font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              @click="handleSave"
              :disabled="submitting"
            >
              {{ submitting ? '创建中...' : '创建' }}
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
</style>
