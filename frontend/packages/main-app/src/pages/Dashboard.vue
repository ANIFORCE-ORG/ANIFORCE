<script setup lang="ts">
import { ref, onMounted } from 'vue'
import OnboardingGuide from '@/components/home/OnboardingGuide.vue'
import WorkspaceDashboard from '@/components/home/WorkspaceDashboard.vue'

// 检测是否首次使用
const isFirstTime = ref(true)
const loading = ref(true)

onMounted(async () => {
  try {
    // 检查用户是否完成引导
    const onboardingStatus = localStorage.getItem('onboarding_completed')
    isFirstTime.value = !onboardingStatus

    // 开发调试：打印当前状态
    console.log('引导状态检测:', {
      onboardingStatus,
      isFirstTime: isFirstTime.value
    })
  } catch (err) {
    console.error('检测引导状态失败:', err)
  } finally {
    loading.value = false
  }
})

const handleOnboardingComplete = () => {
  localStorage.setItem('onboarding_completed', 'true')
  isFirstTime.value = false
}

const handleSkipOnboarding = () => {
  localStorage.setItem('onboarding_completed', 'true')
  isFirstTime.value = false
}

// 开发用：重置引导状态
const resetOnboarding = () => {
  localStorage.removeItem('onboarding_completed')
  isFirstTime.value = true
  console.log('引导状态已重置')
}

// 暴露到 window 供开发调试
if (typeof window !== 'undefined') {
  (window as any).resetOnboarding = resetOnboarding
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-950">
    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center min-h-screen">
      <span class="material-symbols-outlined text-4xl text-slate-400 animate-spin">progress_activity</span>
    </div>

    <!-- Onboarding Guide (首次使用) -->
    <OnboardingGuide
      v-else-if="isFirstTime"
      @complete="handleOnboardingComplete"
      @skip="handleSkipOnboarding"
    />

    <!-- Workspace Dashboard (后续使用) -->
    <WorkspaceDashboard v-else />
  </div>
</template>
