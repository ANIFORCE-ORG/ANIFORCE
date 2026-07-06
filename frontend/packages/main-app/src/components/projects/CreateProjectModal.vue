<script setup lang="ts">
/**
 * 项目创建/编辑 Modal 壳 - 复用 CreateProjectForm，不重复表单字段
 */
import { ref, watch } from 'vue'
import type { Project } from '@/api/projects'
import CreateProjectForm from './CreateProjectForm.vue'
import {
  type ProjectFormModel,
  type CreateProjectPayload,
  emptyProjectForm,
  getDefaultStartDate,
  getDefaultEndDate,
  toCreateProjectPayload,
} from './projectFormModel'

interface Props {
  show: boolean
  editingProject?: Project | null
}

interface Emits {
  (e: 'close'): void
  (e: 'submit', data: CreateProjectPayload): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isEditMode = ref(false)
const formData = ref<ProjectFormModel>(emptyProjectForm())
const errors = ref<Record<string, string>>({})
const submitting = ref(false)

const formatDateForInput = (dateString: string | undefined | null): string => {
  if (!dateString) return getDefaultStartDate()
  try {
    const date = new Date(dateString)
    if (isNaN(date.getTime())) return getDefaultStartDate()
    return date.toISOString().slice(0, 16)
  } catch {
    return getDefaultStartDate()
  }
}

const validateForm = (): boolean => {
  errors.value = {}
  if (!formData.value.name.trim()) errors.value.name = '请输入项目名称'
  if (!formData.value.product.trim()) errors.value.product = '请输入产品名称'
  if (!formData.value.countries) errors.value.countries = '请选择投放国家'
  if (!formData.value.total_budget || formData.value.total_budget <= 0) errors.value.total_budget = '总预算必须大于0'
  return Object.keys(errors.value).length === 0
}

const resetForm = () => {
  formData.value = emptyProjectForm()
  errors.value = {}
  isEditMode.value = false
}

const handleClose = () => {
  if (!submitting.value) {
    resetForm()
    emit('close')
  }
}

const handleSave = () => {
  if (!validateForm()) return
  submitting.value = true
  const payload = toCreateProjectPayload(formData.value)
  if (!isEditMode.value) payload.status = 'active'
  emit('submit', payload)
}

const loadProjectData = (project: Project) => {
  formData.value = {
    name: project.name,
    product: project.product || '',
    countries: project.target_market || '',
    status: project.status || 'active',
    start: formatDateForInput(project.start_date),
    end: formatDateForInput(project.end_date),
    total_budget: project.total_budget || 0,
    description: project.description || '',
  }
}

watch(() => props.show, (newVal) => {
  if (newVal) {
    isEditMode.value = !!props.editingProject
    if (props.editingProject) loadProjectData(props.editingProject)
  }
})

defineExpose({
  resetForm,
  setSubmitting: (value: boolean) => { submitting.value = value },
})
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
              {{ isEditMode ? '编辑项目' : '新建投放项目' }}
            </h3>
            <button
              class="p-[4px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              @click="handleClose"
              :disabled="submitting"
            >
              <span class="material-symbols-outlined text-[14px] text-slate-500">close</span>
            </button>
          </div>

          <div class="flex-1 overflow-y-auto px-[15px] py-[10px]">
            <div class="mb-[12px] p-[8px] bg-blue-50 dark:bg-blue-900/20 rounded-md">
              <p class="text-[10px] text-blue-600 dark:text-blue-400">
                填写项目基本信息，创建后可继续添加 Campaign
              </p>
            </div>
            <CreateProjectForm
              v-model="formData"
              :edit-mode="isEditMode"
              :errors="errors"
            />
          </div>

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
              {{ submitting ? '保存中...' : '保存' }}
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from,
.fade-leave-to { opacity: 0; }
.slide-enter-active,
.slide-leave-active { transition: transform 0.3s ease; }
.slide-enter-from,
.slide-leave-to { transform: translateX(100%); }
</style>
