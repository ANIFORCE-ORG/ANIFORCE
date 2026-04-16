<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const loading = ref(false)
const selectedHotMaterial = ref<any>(null)
const localizationParams = ref({
  language: 'zh-CN',
  culturalAdaptation: true,
  brandCustomization: true
})
const generating = ref(false)
const progress = ref(0)
const generatedResults = ref<any[]>([])

// Mock 热门素材数据
const hotMaterials = ref([
  {
    id: 'hot_1',
    name: 'Viral Game Ad - Puzzle Mechanics',
    platform: 'TikTok',
    region: 'US',
    views: '15.2M',
    engagement: '8.5%',
    ctr: 4.2,
    thumbnail: ''
  },
  {
    id: 'hot_2',
    name: 'Trending Drama Hook - Cliffhanger',
    platform: 'Meta',
    region: 'US',
    views: '12.8M',
    engagement: '7.8%',
    ctr: 3.9,
    thumbnail: ''
  },
  {
    id: 'hot_3',
    name: 'Popular Match-3 Gameplay',
    platform: 'Google',
    region: 'UK',
    views: '10.5M',
    engagement: '6.9%',
    ctr: 3.5,
    thumbnail: ''
  },
  {
    id: 'hot_4',
    name: 'Viral Character Reveal',
    platform: 'TikTok',
    region: 'JP',
    views: '9.2M',
    engagement: '7.2%',
    ctr: 3.8,
    thumbnail: ''
  },
  {
    id: 'hot_5',
    name: 'Trending Story Format',
    platform: 'Meta',
    region: 'KR',
    views: '8.7M',
    engagement: '6.5%',
    ctr: 3.3,
    thumbnail: ''
  }
])

const languages = [
  { value: 'zh-CN', label: '简体中文', flag: '🇨🇳' },
  { value: 'zh-TW', label: '繁体中文', flag: '🇹🇼' },
  { value: 'en-US', label: 'English', flag: '🇺🇸' },
  { value: 'ja-JP', label: '日本語', flag: '🇯🇵' },
  { value: 'ko-KR', label: '한국어', flag: '🇰🇷' }
]

const handleSelectMaterial = (material: any) => {
  selectedHotMaterial.value = material
  generatedResults.value = []
}

const handleGenerate = async () => {
  if (!selectedHotMaterial.value) {
    alert('请先选择热门素材')
    return
  }

  generating.value = true
  progress.value = 0
  generatedResults.value = []

  const interval = setInterval(() => {
    progress.value += Math.random() * 15
    if (progress.value >= 100) {
      progress.value = 100
      clearInterval(interval)

      setTimeout(() => {
        generatedResults.value = [
          {
            id: `hot_copy_${Date.now()}_1`,
            url: '',
            originalId: selectedHotMaterial.value.id,
            language: localizationParams.value.language
          },
          {
            id: `hot_copy_${Date.now()}_2`,
            url: '',
            originalId: selectedHotMaterial.value.id,
            language: localizationParams.value.language
          },
          {
            id: `hot_copy_${Date.now()}_3`,
            url: '',
            originalId: selectedHotMaterial.value.id,
            language: localizationParams.value.language
          }
        ]
        generating.value = false
      }, 500)
    }
  }, 300)
}

const handleSaveToLibrary = (result: any) => {
  console.log('保存到素材库:', result)
  alert('已保存到素材库')
}

const handleBack = () => {
  router.push('/material')
}

const getPlatformColor = (platform: string): string => {
  const colors: Record<string, string> = {
    Meta: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600',
    Google: 'bg-red-100 dark:bg-red-900/30 text-red-600',
    TikTok: 'bg-slate-900 dark:bg-white text-white dark:text-slate-900'
  }
  return colors[platform] || 'bg-slate-100 dark:bg-slate-700 text-slate-600'
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
            <h1 class="text-xl font-bold text-slate-900 dark:text-white">热点复刻</h1>
            <p class="text-sm text-slate-500 dark:text-slate-400">复刻行业热门素材并本地化</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-6 py-8">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Left: Hot Materials -->
        <div class="lg:col-span-1">
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">热门素材</h3>

            <div class="space-y-3 max-h-[700px] overflow-y-auto">
              <div
                v-for="material in hotMaterials"
                :key="material.id"
                class="p-4 rounded-md border cursor-pointer transition-all"
                :class="selectedHotMaterial?.id === material.id
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
                @click="handleSelectMaterial(material)"
              >
                <div class="space-y-3">
                  <!-- Thumbnail -->
                  <div class="aspect-video rounded-md overflow-hidden bg-slate-100 dark:bg-slate-800">
                    <div class="w-full h-full flex items-center justify-center">
                      <span class="material-symbols-outlined text-4xl text-slate-400">play_circle</span>
                    </div>
                  </div>

                  <!-- Info -->
                  <div>
                    <div class="text-sm font-medium text-slate-900 dark:text-white mb-2">
                      {{ material.name }}
                    </div>
                    <div class="flex items-center gap-2 mb-2">
                      <span class="text-xs px-2 py-0.5 rounded font-medium" :class="getPlatformColor(material.platform)">
                        {{ material.platform }}
                      </span>
                      <span class="text-xs text-slate-500 dark:text-slate-400">{{ material.region }}</span>
                    </div>
                    <div class="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <div class="text-slate-400">观看</div>
                        <div class="font-semibold text-slate-900 dark:text-white">{{ material.views }}</div>
                      </div>
                      <div>
                        <div class="text-slate-400">互动率</div>
                        <div class="font-semibold text-slate-900 dark:text-white">{{ material.engagement }}</div>
                      </div>
                      <div>
                        <div class="text-slate-400">CTR</div>
                        <div class="font-semibold text-emerald-600">{{ material.ctr }}%</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Middle: Configuration -->
        <div class="lg:col-span-1 space-y-6">
          <!-- Language -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">目标语言</h3>
            <div class="space-y-2">
              <div
                v-for="lang in languages"
                :key="lang.value"
                class="p-3 rounded-md border cursor-pointer transition-all"
                :class="localizationParams.language === lang.value
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
                @click="localizationParams.language = lang.value"
              >
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <span class="text-2xl">{{ lang.flag }}</span>
                    <span class="text-sm font-medium text-slate-900 dark:text-white">{{ lang.label }}</span>
                  </div>
                  <div v-if="localizationParams.language === lang.value">
                    <span class="material-symbols-outlined text-primary">check_circle</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Cultural Adaptation -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">本地化选项</h3>
            <div class="space-y-4">
              <label class="flex items-start gap-3 cursor-pointer">
                <input
                  v-model="localizationParams.culturalAdaptation"
                  type="checkbox"
                  class="w-5 h-5 rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary/20 mt-0.5"
                />
                <div>
                  <div class="text-sm font-medium text-slate-900 dark:text-white">文化适配</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    调整文化元素、色彩、符号等以适应目标市场
                  </div>
                </div>
              </label>

              <label class="flex items-start gap-3 cursor-pointer">
                <input
                  v-model="localizationParams.brandCustomization"
                  type="checkbox"
                  class="w-5 h-5 rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary/20 mt-0.5"
                />
                <div>
                  <div class="text-sm font-medium text-slate-900 dark:text-white">品牌定制</div>
                  <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    替换为您的品牌元素和产品信息
                  </div>
                </div>
              </label>
            </div>
          </div>

          <!-- Original Material Info -->
          <div v-if="selectedHotMaterial" class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">原素材信息</h3>
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-sm text-slate-600 dark:text-slate-400">平台</span>
                <span class="text-sm font-semibold text-slate-900 dark:text-white">{{ selectedHotMaterial.platform }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-slate-600 dark:text-slate-400">地区</span>
                <span class="text-sm font-semibold text-slate-900 dark:text-white">{{ selectedHotMaterial.region }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-slate-600 dark:text-slate-400">观看量</span>
                <span class="text-sm font-semibold text-slate-900 dark:text-white">{{ selectedHotMaterial.views }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-slate-600 dark:text-slate-400">互动率</span>
                <span class="text-sm font-semibold text-emerald-600">{{ selectedHotMaterial.engagement }}</span>
              </div>
            </div>
          </div>

          <!-- Generate Button -->
          <button
            class="w-full px-6 py-3 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="generating || !selectedHotMaterial"
            @click="handleGenerate"
          >
            {{ generating ? '生成中...' : '开始复刻' }}
          </button>
        </div>

        <!-- Right: Results -->
        <div class="lg:col-span-1 space-y-6">
          <!-- Progress -->
          <div v-if="generating" class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">复刻进度</h3>
            <div class="space-y-3">
              <div class="flex items-center justify-between text-sm">
                <span class="text-slate-600 dark:text-slate-400">AI正在复刻素材...</span>
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
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">复刻结果</h3>
            <div class="space-y-4">
              <div
                v-for="result in generatedResults"
                :key="result.id"
                class="group relative aspect-video rounded-md overflow-hidden bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
              >
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-600">play_circle</span>
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
                trending_up
              </span>
              <p class="text-sm text-slate-500 dark:text-slate-400">
                选择热门素材并配置本地化参数后，点击"开始复刻"
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
