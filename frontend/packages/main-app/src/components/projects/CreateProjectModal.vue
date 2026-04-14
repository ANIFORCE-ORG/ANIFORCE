<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  show: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'submit', data: ProjectFormData): void
}

interface ProjectFormData {
  name: string
  description: string
  game_type: string
  target_market: string
  total_budget: number
  manager: string
  start_date: string
  end_date: string
  tags: string[]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const formData = ref<ProjectFormData>({
  name: '',
  description: '',
  game_type: '',
  target_market: '',
  total_budget: 0,
  manager: '',
  start_date: '',
  end_date: '',
  tags: []
})

const errors = ref<Record<string, string>>({})
const submitting = ref(false)
const tagInput = ref('')

// 产品类型选项
const gameTypes = [
  { value: 'puzzle', label: '消除游戏' },
  { value: 'rpg', label: 'RPG游戏' },
  { value: 'strategy', label: '策略游戏' },
  { value: 'casual', label: '休闲游戏' },
  { value: 'drama', label: '短剧' },
  { value: 'other', label: '其他' }
]

// 目标地区选项
const targetMarkets = [
  { value: 'US', label: '美国' },
  { value: 'UK', label: '英国' },
  { value: 'JP', label: '日本' },
  { value: 'KR', label: '韩国' },
  { value: 'SEA', label: '东南亚' },
  { value: 'EU', label: '欧洲' },
  { value: 'Global', label: '全球' }
]

// 表单验证
const validateForm = (): boolean => {
  errors.value = {}
  
  if (!formData.value.name.trim()) {
    errors.value.name = '请输入项目名称'
  }
  
  if (!formData.value.game_type) {
    errors.value.game_type = '请选择产品类型'
  }
  
  if (!formData.value.target_market) {
    errors.value.target_market = '请选择目标地区'
  }
  
  if (!formData.value.total_budget || formData.value.total_budget <= 0) {
    errors.value.total_budget = '请输入有效的预算金额'
  }
  
  if (formData.value.start_date && formData.value.end_date) {
    if (new Date(formData.value.start_date) > new Date(formData.value.end_date)) {
      errors.value.end_date = '结束日期不能早于开始日期'
    }
  }
  
  return Object.keys(errors.value).length === 0
}

// 添加标签
const addTag = () => {
  const tag = tagInput.value.trim()
  if (tag && !formData.value.tags.includes(tag)) {
    formData.value.tags.push(tag)
    tagInput.value = ''
  }
}

// 删除标签
const removeTag = (index: number) => {
  formData.value.tags.splice(index, 1)
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
    name: '',
    description: '',
    game_type: '',
    target_market: '',
    total_budget: 0,
    manager: '',
    start_date: '',
    end_date: '',
    tags: []
  }
  errors.value = {}
  submitting.value = false
  tagInput.value = ''
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
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      @click.self="handleClose"
    >
      <!-- 弹窗容器 -->
      <Transition name="scale">
        <div
          v-if="show"
          class="bg-white dark:bg-slate-800 rounded-lg shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col"
        >
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
            <h3 class="text-lg font-bold text-slate-900 dark:text-white">创建新项目</h3>
            <button
              class="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              @click="handleClose"
              :disabled="submitting"
            >
              <span class="material-symbols-outlined text-slate-500">close</span>
            </button>
          </div>

          <!-- 弹窗内容 -->
          <div class="flex-1 overflow-y-auto px-6 py-4">
            <form @submit.prevent="handleSubmit" class="space-y-4">
              <!-- 项目名称 -->
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  项目名称 <span class="text-red-500">*</span>
                </label>
                <input
                  v-model="formData.name"
                  type="text"
                  placeholder="例如：Candy Blast 美国市场推广"
                  class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                  :class="{ 'border-red-500': errors.name }"
                />
                <p v-if="errors.name" class="mt-1 text-xs text-red-500">{{ errors.name }}</p>
              </div>

              <!-- 项目描述 -->
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  项目描述
                </label>
                <textarea
                  v-model="formData.description"
                  rows="3"
                  placeholder="简要描述项目目标和策略..."
                  class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
                ></textarea>
              </div>

              <!-- 产品类型和目标地区 -->
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    产品类型 <span class="text-red-500">*</span>
                  </label>
                  <select
                    v-model="formData.game_type"
                    class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/20"
                    :class="{ 'border-red-500': errors.game_type }"
                  >
                    <option value="">请选择</option>
                    <option v-for="type in gameTypes" :key="type.value" :value="type.value">
                      {{ type.label }}
                    </option>
                  </select>
                  <p v-if="errors.game_type" class="mt-1 text-xs text-red-500">{{ errors.game_type }}</p>
                </div>

                <div>
                  <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    目标地区 <span class="text-red-500">*</span>
                  </label>
                  <select
                    v-model="formData.target_market"
                    class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/20"
                    :class="{ 'border-red-500': errors.target_market }"
                  >
                    <option value="">请选择</option>
                    <option v-for="market in targetMarkets" :key="market.value" :value="market.value">
                      {{ market.label }}
                    </option>
                  </select>
                  <p v-if="errors.target_market" class="mt-1 text-xs text-red-500">{{ errors.target_market }}</p>
                </div>
              </div>

              <!-- 总预算 -->
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  总预算金额 (USD) <span class="text-red-500">*</span>
                </label>
                <div class="relative">
                  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">$</span>
                  <input
                    v-model.number="formData.total_budget"
                    type="number"
                    min="0"
                    step="100"
                    placeholder="0"
                    class="w-full pl-8 pr-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                    :class="{ 'border-red-500': errors.total_budget }"
                  />
                </div>
                <p v-if="errors.total_budget" class="mt-1 text-xs text-red-500">{{ errors.total_budget }}</p>
              </div>

              <!-- 项目负责人 -->
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  项目负责人
                </label>
                <input
                  v-model="formData.manager"
                  type="text"
                  placeholder="例如：张三"
                  class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                />
              </div>

              <!-- 项目周期 -->
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    开始日期
                  </label>
                  <input
                    v-model="formData.start_date"
                    type="date"
                    class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/20"
                  />
                </div>

                <div>
                  <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    结束日期
                  </label>
                  <input
                    v-model="formData.end_date"
                    type="date"
                    class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/20"
                    :class="{ 'border-red-500': errors.end_date }"
                  />
                  <p v-if="errors.end_date" class="mt-1 text-xs text-red-500">{{ errors.end_date }}</p>
                </div>
              </div>

              <!-- 标签 -->
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  项目标签
                </label>
                <div class="flex gap-2 mb-2">
                  <input
                    v-model="tagInput"
                    type="text"
                    placeholder="输入标签后按回车添加"
                    class="flex-1 px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                    @keydown.enter.prevent="addTag"
                  />
                  <button
                    type="button"
                    class="px-4 py-2 rounded-md bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                    @click="addTag"
                  >
                    添加
                  </button>
                </div>
                <div v-if="formData.tags.length > 0" class="flex flex-wrap gap-2">
                  <span
                    v-for="(tag, index) in formData.tags"
                    :key="index"
                    class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-primary/10 text-primary text-xs"
                  >
                    {{ tag }}
                    <button
                      type="button"
                      class="hover:text-primary/70"
                      @click="removeTag(index)"
                    >
                      <span class="material-symbols-outlined text-xs">close</span>
                    </button>
                  </span>
                </div>
              </div>
            </form>
          </div>

          <!-- 弹窗底部 -->
          <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700">
            <button
              type="button"
              class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              @click="handleClose"
              :disabled="submitting"
            >
              取消
            </button>
            <button
              type="button"
              class="px-4 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              @click="handleSubmit"
              :disabled="submitting"
            >
              <span v-if="submitting" class="material-symbols-outlined animate-spin text-sm">progress_activity</span>
              <span>{{ submitting ? '创建中...' : '创建项目' }}</span>
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

.scale-enter-active,
.scale-leave-active {
  transition: all 0.2s ease;
}

.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
