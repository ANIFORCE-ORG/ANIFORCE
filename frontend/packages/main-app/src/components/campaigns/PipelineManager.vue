<script setup lang="ts">
import { ref, computed } from 'vue'

interface Campaign {
  id: string
  name: string
  pipeline_step?: string
  learning_phase?: string
  status: string
}

interface Props {
  campaign?: Campaign
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'update', data: { pipeline_step: string }): void
}>()

// Pipeline 阶段配置
const pipelineSteps = [
  { value: 'testing', label: '测试期', color: 'bg-blue-500', icon: 'science' },
  { value: 'scaling', label: '放量期', color: 'bg-green-500', icon: 'trending_up' },
  { value: 'stable', label: '稳定期', color: 'bg-emerald-500', icon: 'check_circle' },
  { value: 'declining', label: '衰退期', color: 'bg-yellow-500', icon: 'trending_down' },
  { value: 'paused', label: '已暂停', color: 'bg-slate-500', icon: 'pause' }
]

// 学习阶段配置
const learningPhases = [
  { value: 'learning', label: '学习中', color: 'text-blue-600', icon: 'school' },
  { value: 'learned', label: '已学习', color: 'text-green-600', icon: 'check' },
  { value: 'limited', label: '学习受限', color: 'text-yellow-600', icon: 'warning' }
]

const showDialog = ref(false)
const selectedStep = ref(props.campaign?.pipeline_step || 'testing')

const currentStep = computed(() => {
  return pipelineSteps.find(s => s.value === (props.campaign?.pipeline_step || 'testing'))
})

const currentLearningPhase = computed(() => {
  return learningPhases.find(p => p.value === (props.campaign?.learning_phase || 'learning'))
})

const openDialog = () => {
  selectedStep.value = props.campaign?.pipeline_step || 'testing'
  showDialog.value = true
}

const closeDialog = () => {
  showDialog.value = false
}

const handleUpdateStep = () => {
  emit('update', { pipeline_step: selectedStep.value })
  closeDialog()
}

const getStepIndex = (step: string): number => {
  return pipelineSteps.findIndex(s => s.value === step)
}

const isStepActive = (step: string): boolean => {
  const currentIndex = getStepIndex(props.campaign?.pipeline_step || 'testing')
  const stepIndex = getStepIndex(step)
  return stepIndex <= currentIndex
}
</script>

<template>
  <div>
    <!-- Pipeline 状态显示 -->
    <div class="space-y-3">
      <!-- 当前阶段 -->
      <div class="flex items-center gap-3 p-3 rounded-md bg-slate-50 dark:bg-slate-800/50">
        <div
          class="w-10 h-10 rounded-full flex items-center justify-center text-white flex-shrink-0"
          :class="currentStep?.color"
        >
          <span class="material-symbols-outlined text-xl">{{ currentStep?.icon }}</span>
        </div>
        <div class="flex-1">
          <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">当前阶段</div>
          <div class="text-sm font-semibold text-slate-900 dark:text-white">
            {{ currentStep?.label }}
          </div>
        </div>
        <button
          class="px-3 py-1.5 rounded-md bg-primary text-white text-xs font-medium hover:bg-primary/90 transition-colors"
          @click="openDialog"
        >
          切换阶段
        </button>
      </div>

      <!-- 学习阶段 -->
      <div v-if="campaign?.learning_phase" class="flex items-center gap-2 p-3 rounded-md border border-slate-200 dark:border-slate-700">
        <span class="material-symbols-outlined text-lg" :class="currentLearningPhase?.color">
          {{ currentLearningPhase?.icon }}
        </span>
        <div class="flex-1">
          <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">学习阶段</div>
          <div class="text-sm font-semibold" :class="currentLearningPhase?.color">
            {{ currentLearningPhase?.label }}
          </div>
        </div>
      </div>

      <!-- Pipeline 进度条 -->
      <div class="p-3 rounded-md border border-slate-200 dark:border-slate-700">
        <div class="text-xs text-slate-500 dark:text-slate-400 mb-3">投放生命周期</div>
        <div class="flex items-center justify-between">
          <div
            v-for="(step, index) in pipelineSteps.slice(0, 4)"
            :key="step.value"
            class="flex flex-col items-center flex-1"
          >
            <!-- 步骤圆点 -->
            <div
              class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold mb-2 transition-all"
              :class="isStepActive(step.value) ? step.color : 'bg-slate-300 dark:bg-slate-700'"
            >
              {{ index + 1 }}
            </div>
            <!-- 步骤标签 -->
            <div
              class="text-[10px] text-center"
              :class="isStepActive(step.value) ? 'text-slate-900 dark:text-white font-semibold' : 'text-slate-400'"
            >
              {{ step.label }}
            </div>
            <!-- 连接线 -->
            <div
              v-if="index < 3"
              class="absolute h-0.5 w-[calc(25%-2rem)] transition-all"
              :class="isStepActive(pipelineSteps[index + 1].value) ? 'bg-primary' : 'bg-slate-300 dark:bg-slate-700'"
              :style="{ left: `calc(${(index + 1) * 25}% - ${(index + 1) * 0.5}rem)`, top: '1rem' }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 切换阶段对话框 -->
    <div
      v-if="showDialog"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      @click.self="closeDialog"
    >
      <div class="bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-md p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-bold text-slate-900 dark:text-white">切换投放阶段</h3>
          <button
            class="w-8 h-8 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center justify-center transition-colors"
            @click="closeDialog"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">close</span>
          </button>
        </div>

        <div class="space-y-2 mb-6">
          <div
            v-for="step in pipelineSteps"
            :key="step.value"
            class="flex items-center gap-3 p-3 rounded-md border cursor-pointer transition-all"
            :class="selectedStep === step.value
              ? 'border-primary bg-primary/5'
              : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
            @click="selectedStep = step.value"
          >
            <div
              class="w-10 h-10 rounded-full flex items-center justify-center text-white flex-shrink-0"
              :class="step.color"
            >
              <span class="material-symbols-outlined text-xl">{{ step.icon }}</span>
            </div>
            <div class="flex-1">
              <div class="text-sm font-semibold text-slate-900 dark:text-white">
                {{ step.label }}
              </div>
            </div>
            <div v-if="selectedStep === step.value">
              <span class="material-symbols-outlined text-primary">check_circle</span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <button
            class="flex-1 px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            @click="closeDialog"
          >
            取消
          </button>
          <button
            class="flex-1 px-4 py-2 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors"
            @click="handleUpdateStep"
          >
            确认切换
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
