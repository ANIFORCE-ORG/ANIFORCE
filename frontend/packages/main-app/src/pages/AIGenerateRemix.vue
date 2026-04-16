<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMaterials, type Material } from '@/api/materials'

const router = useRouter()

const loading = ref(false)
const materials = ref<Material[]>([])
const selectedMaterial = ref<Material | null>(null)
const remixParams = ref({
  style: 'similar',
  variation: 'medium',
  count: 4
})
const generating = ref(false)
const progress = ref(0)
const generatedResults = ref<any[]>([])

// 加载跑量素材
onMounted(async () => {
  try {
    loading.value = true
    const data = await getMaterials()
    // 只显示跑量素材
    materials.value = data.filter(m => m.is_hero)
  } catch (err) {
    console.error('加载素材失败:', err)
  } finally {
    loading.value = false
  }
})

const styleOptions = [
  { value: 'similar', label: '相似风格', desc: '保持原素材风格' },
  { value: 'enhanced', label: '增强版本', desc: '优化视觉效果' },
  { value: 'simplified', label: '简化版本', desc: '简化元素' }
]

const variationOptions = [
  { value: 'low', label: '低变化', desc: '微调细节' },
  { value: 'medium', label: '中变化', desc: '适度调整' },
  { value: 'high', label: '高变化', desc: '大幅改变' }
]

const handleSelectMaterial = (material: Material) => {
  selectedMaterial.value = material
  generatedResults.value = []
}

const handleGenerate = async () => {
  if (!selectedMaterial.value) {
    alert('请先选择参考素材')
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
        generatedResults.value = Array.from({ length: remixParams.value.count }, (_, i) => ({
          id: `remix_${Date.now()}_${i}`,
          url: '',
          originalId: selectedMaterial.value?.id,
          style: remixParams.value.style,
          variation: remixParams.value.variation
        }))
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
            <h1 class="text-xl font-bold text-slate-900 dark:text-white">爆款二创</h1>
            <p class="text-sm text-slate-500 dark:text-slate-400">基于跑量素材生成创意变体</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Content -->
    <div class="max-w-7xl mx-auto px-6 py-8">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <!-- Left: Material Selection -->
        <div class="lg:col-span-1">
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">选择参考素材</h3>

            <div v-if="loading" class="flex items-center justify-center py-8">
              <span class="material-symbols-outlined text-4xl text-slate-400 animate-spin">progress_activity</span>
            </div>

            <div v-else-if="materials.length > 0" class="space-y-3 max-h-[600px] overflow-y-auto">
              <div
                v-for="material in materials"
                :key="material.id"
                class="p-3 rounded-md border cursor-pointer transition-all"
                :class="selectedMaterial?.id === material.id
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
                @click="handleSelectMaterial(material)"
              >
                <div class="flex items-start gap-3">
                  <div class="w-16 h-16 rounded-md overflow-hidden bg-slate-100 dark:bg-slate-800 flex-shrink-0">
                    <div class="w-full h-full flex items-center justify-center">
                      <span class="material-symbols-outlined text-2xl text-slate-400">image</span>
                    </div>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-slate-900 dark:text-white truncate mb-1">
                      {{ material.name }}
                    </div>
                    <div class="flex items-center gap-2 text-xs">
                      <span class="px-2 py-0.5 rounded-full bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600 font-semibold">
                        跑量
                      </span>
                      <span class="text-slate-500 dark:text-slate-400">
                        ROI {{ material.roi?.toFixed(1) }}x
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="text-center py-8">
              <span class="material-symbols-outlined text-4xl text-slate-300 dark:text-slate-700 mb-2">
                star_outline
              </span>
              <p class="text-sm text-slate-500 dark:text-slate-400">暂无跑量素材</p>
            </div>
          </div>
        </div>

        <!-- Middle: Configuration -->
        <div class="lg:col-span-1 space-y-6">
          <!-- Original Material Info -->
          <div v-if="selectedMaterial" class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">原素材数据</h3>
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-sm text-slate-600 dark:text-slate-400">ROI</span>
                <span class="text-sm font-semibold text-emerald-600">{{ selectedMaterial.roi?.toFixed(2) }}x</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-slate-600 dark:text-slate-400">消耗</span>
                <span class="text-sm font-semibold text-slate-900 dark:text-white">${{ selectedMaterial.spend?.toLocaleString() }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm text-slate-600 dark:text-slate-400">CTR</span>
                <span class="text-sm font-semibold text-slate-900 dark:text-white">{{ selectedMaterial.ctr_estimate?.toFixed(2) }}%</span>
              </div>
            </div>
          </div>

          <!-- Style -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">二创风格</h3>
            <div class="space-y-2">
              <div
                v-for="option in styleOptions"
                :key="option.value"
                class="p-3 rounded-md border cursor-pointer transition-all"
                :class="remixParams.style === option.value
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
                @click="remixParams.style = option.value"
              >
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-sm font-medium text-slate-900 dark:text-white">{{ option.label }}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">{{ option.desc }}</div>
                  </div>
                  <div v-if="remixParams.style === option.value">
                    <span class="material-symbols-outlined text-primary">check_circle</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Variation -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">变化程度</h3>
            <div class="space-y-2">
              <div
                v-for="option in variationOptions"
                :key="option.value"
                class="p-3 rounded-md border cursor-pointer transition-all"
                :class="remixParams.variation === option.value
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
                @click="remixParams.variation = option.value"
              >
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-sm font-medium text-slate-900 dark:text-white">{{ option.label }}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">{{ option.desc }}</div>
                  </div>
                  <div v-if="remixParams.variation === option.value">
                    <span class="material-symbols-outlined text-primary">check_circle</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Generate Count -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">生成数量</h3>
            <div class="flex items-center gap-3">
              <input
                v-model.number="remixParams.count"
                type="range"
                min="1"
                max="8"
                class="flex-1"
              />
              <span class="text-sm font-semibold text-slate-900 dark:text-white w-8 text-right">{{ remixParams.count }}</span>
            </div>
          </div>

          <!-- Generate Button -->
          <button
            class="w-full px-6 py-3 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="generating || !selectedMaterial"
            @click="handleGenerate"
          >
            {{ generating ? '生成中...' : '开始生成' }}
          </button>
        </div>

        <!-- Right: Results -->
        <div class="lg:col-span-1 space-y-6">
          <!-- Progress -->
          <div v-if="generating" class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">生成进度</h3>
            <div class="space-y-3">
              <div class="flex items-center justify-between text-sm">
                <span class="text-slate-600 dark:text-slate-400">AI正在生成变体...</span>
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
                  <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-600">image</span>
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
                shuffle
              </span>
              <p class="text-sm text-slate-500 dark:text-slate-400">
                选择参考素材并配置参数后，点击"开始生成"
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
