<script setup lang="ts">
// @ts-nocheck
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const prompt = ref('')
const mediaType = ref<'image' | 'video'>('image')
const aspectRatio = ref('16:9')
const style = ref('realistic')
const generating = ref(false)
const progress = ref(0)
const generatedResults = ref<any[]>([])

const mediaTypes = [
  { value: 'image', label: '图片', icon: 'image' },
  { value: 'video', label: '视频', icon: 'videocam' }
]

const aspectRatios = [
  { value: '16:9', label: '16:9 (横屏)', desc: '适合横屏广告' },
  { value: '9:16', label: '9:16 (竖屏)', desc: '适合短视频平台' },
  { value: '1:1', label: '1:1 (方形)', desc: '适合社交媒体' },
  { value: '4:5', label: '4:5 (竖版)', desc: '适合信息流' }
]

const styles = [
  { value: 'realistic', label: '写实风格', icon: '📷' },
  { value: 'cartoon', label: '卡通风格', icon: '🎨' },
  { value: 'anime', label: '动漫风格', icon: '🎭' },
  { value: 'minimalist', label: '极简风格', icon: '✨' }
]

const handleGenerate = async () => {
  if (!prompt.value.trim()) {
    alert('请输入生成提示词')
    return
  }

  generating.value = true
  progress.value = 0
  generatedResults.value = []

  // 模拟生成进度
  const interval = setInterval(() => {
    progress.value += Math.random() * 15
    if (progress.value >= 100) {
      progress.value = 100
      clearInterval(interval)

      // 模拟生成结果
      setTimeout(() => {
        generatedResults.value = [
          {
            id: `gen_${Date.now()}_1`,
            url: '',
            prompt: prompt.value,
            type: mediaType.value,
            aspectRatio: aspectRatio.value,
            style: style.value
          },
          {
            id: `gen_${Date.now()}_2`,
            url: '',
            prompt: prompt.value,
            type: mediaType.value,
            aspectRatio: aspectRatio.value,
            style: style.value
          },
          {
            id: `gen_${Date.now()}_3`,
            url: '',
            prompt: prompt.value,
            type: mediaType.value,
            aspectRatio: aspectRatio.value,
            style: style.value
          },
          {
            id: `gen_${Date.now()}_4`,
            url: '',
            prompt: prompt.value,
            type: mediaType.value,
            aspectRatio: aspectRatio.value,
            style: style.value
          }
        ]
        generating.value = false
      }, 500)
    }
  }, 300)
}

const handleSaveToLibrary = (result: any) => {
  console.log('保存到素材库:', result)
  // TODO: 调用API保存
  alert('已保存到素材库')
}

const handleBack = () => {
  router.push('/material')
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 dark:bg-slate-950">
    <!-- Header -->
    <div class="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
      <div class="max-w-7xl mx-auto px-6 py-4">
        <div class="flex items-center gap-4">
          <button
            class="w-10 h-10 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition-colors"
            @click="handleBack"
          >
            <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">arrow_back</span>
          </button>
          <div>
            <h1 class="text-xl font-bold text-slate-900 dark:text-white">AI全新生成</h1>
            <p class="text-sm text-slate-500 dark:text-slate-400">通过AI生成全新的创意素材</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-6 py-8">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Left: Configuration -->
        <div class="space-y-6">
          <!-- Prompt Input -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">生成提示词</h3>
            <textarea
              v-model="prompt"
              rows="6"
              placeholder="描述你想要生成的素材内容，例如：一个可爱的糖果消除游戏角色，色彩鲜艳，卡通风格..."
              class="w-full px-4 py-3 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
            ></textarea>
          </div>

          <!-- Media Type -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">素材类型</h3>
            <div class="grid grid-cols-2 gap-3">
              <div
                v-for="type in mediaTypes"
                :key="type.value"
                class="p-4 rounded-md border cursor-pointer transition-all"
                :class="mediaType === type.value
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
                @click="mediaType = type.value"
              >
                <div class="flex items-center gap-3">
                  <span class="material-symbols-outlined text-2xl" :class="mediaType === type.value ? 'text-primary' : 'text-slate-400'">
                    {{ type.icon }}
                  </span>
                  <span class="text-sm font-medium" :class="mediaType === type.value ? 'text-slate-900 dark:text-white' : 'text-slate-600 dark:text-slate-400'">
                    {{ type.label }}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- Aspect Ratio -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">尺寸规格</h3>
            <div class="space-y-2">
              <div
                v-for="ratio in aspectRatios"
                :key="ratio.value"
                class="p-3 rounded-md border cursor-pointer transition-all"
                :class="aspectRatio === ratio.value
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
                @click="aspectRatio = ratio.value"
              >
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-sm font-medium text-slate-900 dark:text-white">{{ ratio.label }}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">{{ ratio.desc }}</div>
                  </div>
                  <div v-if="aspectRatio === ratio.value">
                    <span class="material-symbols-outlined text-primary">check_circle</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Style -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">生成风格</h3>
            <div class="grid grid-cols-2 gap-3">
              <div
                v-for="s in styles"
                :key="s.value"
                class="p-4 rounded-md border cursor-pointer transition-all"
                :class="style === s.value
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
                @click="style = s.value"
              >
                <div class="text-center">
                  <div class="text-3xl mb-2">{{ s.icon }}</div>
                  <div class="text-sm font-medium" :class="style === s.value ? 'text-slate-900 dark:text-white' : 'text-slate-600 dark:text-slate-400'">
                    {{ s.label }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Generate Button -->
          <button
            class="w-full px-6 py-3 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="generating || !prompt.trim()"
            @click="handleGenerate"
          >
            {{ generating ? '生成中...' : '开始生成' }}
          </button>
        </div>

        <!-- Right: Results -->
        <div class="space-y-6">
          <!-- Progress -->
          <div v-if="generating" class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">生成进度</h3>
            <div class="space-y-3">
              <div class="flex items-center justify-between text-sm">
                <span class="text-slate-600 dark:text-slate-400">AI正在生成素材...</span>
                <span class="font-semibold text-slate-900 dark:text-white">{{ progress.toFixed(0) }}%</span>
              </div>
              <div class="w-full h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                <div
                  class="h-full bg-primary rounded-full transition-all"
                  :style="{ width: `${progress}%` }"
                ></div>
              </div>
            </div>
          </div>

          <!-- Results -->
          <div v-if="generatedResults.length > 0" class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">生成结果</h3>
            <div class="grid grid-cols-2 gap-4">
              <div
                v-for="result in generatedResults"
                :key="result.id"
                class="group relative aspect-video rounded-md overflow-hidden bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
              >
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-600">
                    {{ result.type === 'image' ? 'image' : 'videocam' }}
                  </span>
                </div>
                <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                  <button
                    class="px-3 py-2 rounded-md bg-white text-slate-900 text-xs font-medium hover:bg-slate-100 transition-colors"
                    @click="handleSaveToLibrary(result)"
                  >
                    保存
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Empty State -->
          <div v-if="!generating && generatedResults.length === 0" class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-12">
            <div class="text-center">
              <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">
                auto_awesome
              </span>
              <p class="text-sm text-slate-500 dark:text-slate-400">
                配置参数后点击"开始生成"，AI将为您创作全新素材
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
