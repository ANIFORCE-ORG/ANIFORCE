<script setup lang="ts">
import { ref, watch } from 'vue'
import { PRODUCT_TYPES } from '@/config/productTypes'
import { REGIONS } from '@/config/regions'
import type { Project } from '@/api/projects'

interface Props {
  show: boolean
  project: Project | null
}

interface Emits {
  (e: 'close'): void
  (e: 'submit', data: ProjectEditFormData): void
}

interface ProjectEditFormData {
  name: string
  product_type?: string
  region?: string[]
  total_budget: number
  target_roi?: number
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const formData = ref<ProjectEditFormData>({
  name: '',
  product_type: '',
  region: [],
  total_budget: 0,
  target_roi: 0
})

const errors = ref<Record<string, string>>({})
const submitting = ref(false)

// 监听项目变化，填充表单
watch(() => props.project, (project) => {
  if (project) {
    formData.value = {
      name: project.name,
      product_type: project.product_type || '',
      region: Array.isArray(project.region) ? project.region : (project.region ? [project.region] : []),
      total_budget: project.total_budget,
      target_roi: project.target_roi || 0
    }
  }
}, { immediate: true })

// 表单验证
const validateForm = (): boolean => {
  errors.value = {}

  if (!formData.value.name.trim()) {
    errors.value.name = '请输入项目名称'
  }

  if (!formData.value.total_budget || formData.value.total_budget <= 0) {
    errors.value.total_budget = '请输入有效的预算金额'
  }

  if (formData.value.target_roi && formData.value.target_roi <= 0) {
    errors.value.target_roi = '目标ROI必须大于0'
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
    name: '',
    product_type: '',
    region: [],
    total_budget: 0,
    target_roi: 0
  }
  errors.value = {}
  submitting.value = false
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
            <h3 class="text-lg font-bold text-slate-900 dark:text-white">编辑项目</h3>
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

              <!-- 产品类型 -->
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  产品类型
                </label>
                <select
                  v-model="formData.product_type"
                  class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/20"
                >
                  <option value="">请选择</option>
                  <option v-for="type in PRODUCT_TYPES" :key="type.value" :value="type.value">
                    {{ type.icon }} {{ type.label }}
                  </option>
                </select>
              </div>

              <!-- 目标地区 -->
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  目标地区
                </label>
                <select
                  v-model="formData.region"
                  multiple
                  class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary/20"
                  size="5"
                >
                  <option v-for="region in REGIONS" :key="region.value" :value="region.value">
                    {{ region.label }}
                  </option>
                </select>
                <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">按住 Ctrl/Cmd 可多选</p>
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

              <!-- 目标ROI -->
              <div>
                <label class="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  目标ROI
                </label>
                <input
                  v-model.number="formData.target_roi"
                  type="number"
                  min="0"
                  step="0.1"
                  placeholder="例如：2.0"
                  class="w-full px-3 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
                  :class="{ 'border-red-500': errors.target_roi }"
                />
                <p v-if="errors.target_roi" class="mt-1 text-xs text-red-500">{{ errors.target_roi }}</p>
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
              <span>{{ submitting ? '保存中...' : '保存修改' }}</span>
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
