<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Project } from '@/api/projects'

interface Props {
  show: boolean
  editingProject?: Project | null
}

interface Emits {
  (e: 'close'): void
  (e: 'submit', data: ProjectSubmitData): void
}

interface ProjectFormData {
  name: string
  product: string
  countries: string
  status: string
  start: string
  end: string
  total_budget: number
  description: string
}

interface ProjectSubmitData {
  name: string
  product: string
  target_market: string
  status: string
  start_date: string
  end_date: string
  total_budget: number
  description: string
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 判断是否为编辑模式
const isEditMode = ref(false)

// 获取默认日期：开始日期为当前日期，结束日期为7天后
const getDefaultStartDate = () => {
  const now = new Date()
  return now.toISOString().slice(0, 16)
}

const getDefaultEndDate = () => {
  const now = new Date()
  const sevenDaysLater = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
  return sevenDaysLater.toISOString().slice(0, 16)
}

// 格式化日期为 datetime-local input 所需格式
const formatDateForInput = (dateString: string | undefined | null): string => {
  if (!dateString) return getDefaultStartDate()

  try {
    const date = new Date(dateString)
    if (isNaN(date.getTime())) {
      return getDefaultStartDate()
    }
    return date.toISOString().slice(0, 16)
  } catch {
    return getDefaultStartDate()
  }
}

const formData = ref<ProjectFormData>({
  name: '',
  product: '',
  countries: '',
  status: 'active',
  start: getDefaultStartDate(),
  end: getDefaultEndDate(),
  total_budget: 0,
  description: ''
})

const errors = ref<Record<string, string>>({})
const submitting = ref(false)

// 国家代码映射（基于 Facebook Business SDK SpecialAdCategoryCountry 枚举）
const countryOptions = [
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
  { code: 'MY', name: 'Malaysia' },
]

const statusOptions = [
  { value: 'active', label: '进行中' },
  { value: 'paused', label: '已暂停' },
  { value: 'completed', label: '已完成' },
  { value: 'draft', label: '草稿' }
]

// 验证表单
const validateForm = (): boolean => {
  errors.value = {}

  if (!formData.value.name.trim()) {
    errors.value.name = '请输入项目名称'
  }

  if (!formData.value.product.trim()) {
    errors.value.product = '请输入产品名称'
  }

  if (!formData.value.countries) {
    errors.value.countries = '请选择投放国家'
  }

  if (!formData.value.total_budget || formData.value.total_budget <= 0) {
    errors.value.total_budget = '总预算必须大于0'
  }

  return Object.keys(errors.value).length === 0
}

// 重置表单
const resetForm = () => {
  formData.value = {
    name: '',
    product: '',
    countries: '',
    status: 'active',
    start: getDefaultStartDate(),
    end: getDefaultEndDate(),
    total_budget: 0,
    description: ''
  }
  errors.value = {}
  isEditMode.value = false
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

  // 将前端表单字段映射到后端 API 字段
  const submitData = {
    name: formData.value.name,
    product: formData.value.product,
    target_market: formData.value.countries,  // countries -> target_market
    status: isEditMode.value ? formData.value.status : 'active',  // 创建时默认为active
    start_date: formData.value.start,  // start -> start_date
    end_date: formData.value.end,  // end -> end_date
    total_budget: formData.value.total_budget,
    description: formData.value.description
  }

  emit('submit', submitData)
}

// 从项目数据加载到表单（编辑模式）
const loadProjectData = (project: Project) => {
  formData.value = {
    name: project.name,
    product: project.product || '',
    countries: project.target_market || '',
    status: project.status || 'active',
    start: formatDateForInput(project.start_date),
    end: formatDateForInput(project.end_date),
    total_budget: project.total_budget || 0,
    description: project.description || ''
  }
}

// 监听模态框打开
watch(() => props.show, (newVal) => {
  if (newVal) {
    isEditMode.value = !!props.editingProject
    if (props.editingProject) {
      loadProjectData(props.editingProject)
    }
  }
})

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
      class="project-drawer-layer fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
      @click.self="handleClose"
    >
      <!-- 弹窗容器 - 右侧抽屉 -->
      <Transition name="slide">
        <div
          v-if="show"
          class="project-drawer fixed right-0 top-0 h-full bg-white dark:bg-slate-800 shadow-2xl w-full max-w-[600px] overflow-hidden flex flex-col rounded-l-md"
        >
          <!-- 弹窗头部 -->
          <div class="project-drawer-head flex items-center justify-between px-[15px] py-[10px] border-b border-slate-200 dark:border-slate-700">
            <h3 class="text-[13px] font-semibold text-slate-900 dark:text-white">
              {{ isEditMode ? '编辑项目' : '新建投放项目' }}
            </h3>
            <button
              class="project-close p-[4px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              @click="handleClose"
              :disabled="submitting"
            >
              <span class="material-symbols-outlined text-[14px] text-slate-500">close</span>
            </button>
          </div>

          <!-- 弹窗内容 -->
          <div class="project-drawer-body flex-1 overflow-y-auto px-[15px] py-[10px]">
            <!-- 说明文字 -->
            <div class="project-framework-note mb-[12px] p-[8px] bg-blue-50 dark:bg-blue-900/20 rounded-md">
              <p class="text-[10px] text-blue-600 dark:text-blue-400">
                填写项目基本信息，创建后可继续添加 Campaign
              </p>
            </div>

            <!-- 表单 -->
            <form @submit.prevent="handleSave" class="project-form space-y-[10px]">
              <!-- 第一行：项目名称 -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  项目名称 *
                </label>
                <input
                  v-model="formData.name"
                  type="text"
                  placeholder="例如：Candy Blast 全球推广"
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  :class="{ 'border-red-500': errors.name }"
                />
                <p v-if="errors.name" class="mt-[3px] text-[9px] text-red-500">{{ errors.name }}</p>
              </div>

              <!-- 第二行：产品 + 投放国家 -->
              <div class="grid grid-cols-2 gap-[10px]">
                <!-- 产品 -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    产品 *
                  </label>
                  <input
                    v-model="formData.product"
                    type="text"
                    placeholder="例如：休闲消除手游"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    :class="{ 'border-red-500': errors.product }"
                  />
                  <p v-if="errors.product" class="mt-[3px] text-[9px] text-red-500">{{ errors.product }}</p>
                </div>

                <!-- 投放国家 -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    投放国家/地区 *
                  </label>
                  <select
                    v-model="formData.countries"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    :class="{ 'border-red-500': errors.countries }"
                  >
                    <option value="">请选择国家</option>
                    <option v-for="country in countryOptions" :key="country.code" :value="country.code">
                      {{ country.code }} ({{ country.name }})
                    </option>
                  </select>
                  <p v-if="errors.countries" class="mt-[3px] text-[9px] text-red-500">{{ errors.countries }}</p>
                </div>
              </div>

              <!-- 第三行：开始日期 + 结束日期 -->
              <div class="grid grid-cols-2 gap-[10px]">
                <!-- 开始日期 -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Start Date
                  </label>
                  <input
                    v-model="formData.start"
                    type="datetime-local"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <!-- 结束日期 -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    End Date
                  </label>
                  <input
                    v-model="formData.end"
                    type="datetime-local"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              <!-- 第四行：总预算 + 状态（仅编辑模式） -->
              <div class="grid grid-cols-2 gap-[10px]">
                <!-- 总预算 -->
                <div>
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    Total Budget(USD) *
                  </label>
                  <input
                    v-model.number="formData.total_budget"
                    type="number"
                    min="1.0"
                    step="1.0"
                    placeholder="10.00"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                    :class="{ 'border-red-500': errors.total_budget }"
                  />
                  <p v-if="errors.total_budget" class="mt-[3px] text-[9px] text-red-500">{{ errors.total_budget }}</p>
                </div>

                <!-- 状态（仅编辑模式显示） -->
                <div v-if="isEditMode">
                  <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                    状态
                  </label>
                  <select
                    v-model="formData.status"
                    class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option v-for="status in statusOptions" :key="status.value" :value="status.value">
                      {{ status.label }}
                    </option>
                  </select>
                </div>
              </div>

              <!-- 第五行：项目描述 -->
              <div>
                <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
                  项目描述
                </label>
                <textarea
                  v-model="formData.description"
                  rows="3"
                  placeholder="简要描述项目目标和内容..."
                  class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 resize-none"
                ></textarea>
              </div>
            </form>
          </div>

          <!-- 弹窗底部 -->
          <div class="project-drawer-actions flex items-center justify-end gap-[8px] px-[15px] py-[10px] border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              class="project-secondary px-[12px] py-[6px] text-[11px] font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-md hover:bg-slate-50 dark:hover:bg-slate-600 transition-colors"
              @click="handleClose"
              :disabled="submitting"
            >
              取消
            </button>
            <button
              type="button"
              class="project-confirm px-[12px] py-[6px] text-[11px] font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              @click="handleSave"
              :disabled="submitting"
            >
              {{ submitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
.project-drawer-layer {
  --project-surface: #f6f5f4;
  --project-surface-soft: #fafaf9;
  --project-line: #e5e3df;
  --project-line-strong: #c8c4be;
  --project-ink: #1a1a1a;
  --project-charcoal: #37352f;
  --project-slate: #5d5b54;
  --project-steel: #787671;
  --project-stone: #a4a097;
  background: rgba(26, 26, 26, 0.48) !important;
  font-family: "Notion Sans", "Avenir Next", Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
}

.project-drawer {
  width: min(680px, 100vw) !important;
  max-width: none !important;
  border-left: 1px solid var(--project-line);
  border-radius: 0 !important;
  background: #fff !important;
  box-shadow: rgba(15, 15, 15, 0.20) -18px 0 52px -18px !important;
}

.project-drawer-head {
  min-height: 57px;
  padding: 0 18px !important;
  border-color: var(--project-line) !important;
}

.project-drawer-head h3 {
  margin: 0;
  color: var(--project-ink) !important;
  font-size: 15px !important;
  font-weight: 600;
  letter-spacing: -0.2px;
}

.project-close {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  padding: 0 !important;
  border: 0;
  border-radius: 6px !important;
  background: transparent;
  color: var(--project-steel) !important;
}

.project-close:hover {
  background: var(--project-surface) !important;
  color: var(--project-ink) !important;
}

.project-close .material-symbols-outlined {
  font-size: 18px !important;
  color: inherit !important;
}

.project-drawer-body {
  padding: 14px 18px 24px !important;
  scrollbar-color: var(--project-line-strong) transparent;
}

.project-framework-note {
  margin-bottom: 14px !important;
  padding: 12px !important;
  border: 0 !important;
  border-radius: 8px !important;
  background: var(--project-surface) !important;
}

.project-framework-note p {
  margin: 0;
  color: var(--project-slate) !important;
  font-size: 10px !important;
  line-height: 1.55;
}

.project-form {
  display: grid;
  gap: 12px;
}

.project-form > div {
  margin: 0 !important;
}

.project-form label {
  margin-bottom: 5px !important;
  color: var(--project-slate) !important;
  font-size: 10px !important;
  font-weight: 500 !important;
}

.project-form input,
.project-form select,
.project-form textarea {
  width: 100%;
  border: 1px solid var(--project-line-strong) !important;
  border-radius: 8px !important;
  outline: none;
  background: #fff !important;
  color: var(--project-charcoal) !important;
  font-size: 11px !important;
  box-shadow: none !important;
}

.project-form input,
.project-form select {
  height: 38px;
  padding: 0 10px !important;
}

.project-form textarea {
  min-height: 84px;
  padding: 9px 10px !important;
  line-height: 1.5;
}

.project-form input::placeholder,
.project-form textarea::placeholder {
  color: var(--project-stone);
}

.project-form input:focus,
.project-form select:focus,
.project-form textarea:focus {
  border: 2px solid var(--project-charcoal) !important;
  box-shadow: none !important;
}

.project-form .border-red-500 {
  border-color: #e03131 !important;
}

.project-drawer-actions {
  min-height: 58px;
  padding: 0 18px !important;
  border-color: var(--project-line) !important;
  background: rgba(255, 255, 255, 0.96);
}

.project-secondary,
.project-confirm {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 14px !important;
  border-radius: 8px !important;
  font-size: 11px !important;
  font-weight: 500;
}

.project-secondary {
  border: 1px solid var(--project-line-strong) !important;
  background: #fff !important;
  color: var(--project-charcoal) !important;
}

.project-secondary:hover {
  border-color: var(--project-charcoal) !important;
  color: var(--project-ink) !important;
}

.project-confirm {
  border: 1px solid #2383e2 !important;
  background: #2383e2 !important;
  color: #fff !important;
}

.project-confirm:hover {
  border-color: #1b6fc1 !important;
  background: #1b6fc1 !important;
}

@media (max-width: 720px) {
  .project-drawer {
    width: 100vw !important;
    border-left: 0;
  }

  .project-drawer-body {
    padding: 14px 14px 24px !important;
  }

  .project-drawer-head,
  .project-drawer-actions {
    padding-right: 14px !important;
    padding-left: 14px !important;
  }
}

@media (max-width: 520px) {
  .project-form .grid-cols-2 {
    grid-template-columns: 1fr;
  }

  .project-drawer-head {
    min-height: 52px;
  }

  .project-drawer-actions {
    min-height: 56px;
  }
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
