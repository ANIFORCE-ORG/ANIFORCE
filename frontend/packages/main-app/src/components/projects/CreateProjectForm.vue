<script setup lang="ts">
/**
 * 项目创建/编辑表单 - 纯表单组件
 * 页面 Modal 和 Workspace 审核都复用此组件，不新造字段
 */
import { ref, watch } from 'vue'
import type { Project } from '@/api/projects'
import {
  type ProjectFormModel,
  emptyProjectForm,
  getDefaultStartDate,
  getDefaultEndDate,
  projectCountryOptions,
  projectStatusOptions,
} from './projectFormModel'

interface Props {
  modelValue: ProjectFormModel
  editMode?: boolean
  errors?: Record<string, string>
}

interface Emits {
  (e: 'update:modelValue', value: ProjectFormModel): void
}

const props = withDefaults(defineProps<Props>(), {
  editMode: false,
  errors: () => ({}),
})
const emit = defineEmits<Emits>()

const formData = ref<ProjectFormModel>({ ...props.modelValue })

watch(() => props.modelValue, (val) => {
  formData.value = { ...val }
}, { deep: true })

function emitUpdate(): void {
  emit('update:modelValue', { ...formData.value })
}

watch(formData, emitUpdate, { deep: true })
</script>

<template>
  <form class="space-y-[10px]">
    <!-- 项目名称 -->
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

    <!-- 产品 + 投放国家 -->
    <div class="grid grid-cols-2 gap-[10px]">
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
          <option v-for="country in projectCountryOptions" :key="country.code" :value="country.code">
            {{ country.code }} ({{ country.name }})
          </option>
        </select>
        <p v-if="errors.countries" class="mt-[3px] text-[9px] text-red-500">{{ errors.countries }}</p>
      </div>
    </div>

    <!-- 开始日期 + 结束日期 -->
    <div class="grid grid-cols-2 gap-[10px]">
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

    <!-- 总预算 + 状态 -->
    <div class="grid grid-cols-2 gap-[10px]">
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
      <div v-if="editMode">
        <label class="block text-[10px] font-normal text-slate-700 dark:text-slate-300 mb-[5px]">
          状态
        </label>
        <select
          v-model="formData.status"
          class="w-full px-[8px] py-[6px] rounded-md border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-[10px] text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
        >
          <option v-for="status in projectStatusOptions" :key="status.value" :value="status.value">
            {{ status.label }}
          </option>
        </select>
      </div>
    </div>

    <!-- 项目描述 -->
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
</template>
