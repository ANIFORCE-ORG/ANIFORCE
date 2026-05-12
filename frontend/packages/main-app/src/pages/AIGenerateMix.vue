<script setup lang="ts">
// @ts-nocheck
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMaterials, type Material } from '@/api/materials'

const router = useRouter()

const loading = ref(false)
const materials = ref<Material[]>([])
const selectedMaterials = ref<Set<string>>(new Set())
const mixParams = ref({
  duration: 15,
  rhythm: 'medium',
  transition: 'smooth',
  music: true
})
const generating = ref(false)
const progress = ref(0)
const generatedResults = ref<any[]>([])

// 加载素材
onMounted(async () => {
  try {
    loading.value = true
    const data = await getMaterials()
    materials.value = data
  } catch (err) {
    console.error('加载素材失败:', err)
  } finally {
    loading.value = false
  }
})

const rhythmOptions = [
  { value: 'slow', label: '慢节奏', desc: '舒缓平稳' },
  { value: 'medium', label: '中节奏', desc: '适中流畅' },
  { value: 'fast', label: '快节奏', desc: '紧凑刺激' }
]

const transitionOptions = [
  { value: 'smooth', label: '平滑过渡', desc: '淡入淡出' },
  { value: 'cut', label: '直接切换', desc: '快速切换' },
  { value: 'creative', label: '创意转场', desc: 'AI创意效果' }
]

const handleSelectMaterial = (materialId: string) => {
  if (selectedMaterials.value.has(materialId)) {
    selectedMaterials.value.delete(materialId)
  } else {
    selectedMaterials.value.add(materialId)
  }
}

const handleSelectAll = () => {
  if (selectedMaterials.value.size === materials.value.length) {
    selectedMaterials.value.clear()
  } else {
    materials.value.forEach(m => selectedMaterials.value.add(m.id))
  }
}

const isAllSelected = computed(() => {
  return materials.value.length > 0 && selectedMaterials.value.size === materials.value.length
})

const handleGenerate = async () => {
  if (selectedMaterials.value.size < 2) {
    alert('请至少选择2个素材进行混剪')
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
            id: `mix_${Date.now()}_1`,
            url: '',
            materialCount: selectedMaterials.value.size,
            duration: mixParams.value.duration,
            rhythm: mixParams.value.rhythm,
            transition: mixParams.value.transition
          },
          {
            id: `mix_${Date.now()}_2`,
            url: '',
            materialCount: selectedMaterials.value.size,
            duration: mixParams.value.duration,
            rhythm: mixParams.value.rhythm,
            transition: mixParams.value.transition
          },
          {
            id: `mix_${Date.now()}_3`,
            url: '',
            materialCount: selectedMaterials.value.size,
            duration: mixParams.value.duration,
            rhythm: mixParams.value.rhythm,
            transition: mixParams.value.transition
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
            <h1 class="text-xl font-bold text-slate-900 dark:text-white">智能混剪</h1>
            <p class="text-sm text-slate-500 dark:text-slate-400">AI智能分析并混剪多个素材片段</p>
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
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold text-slate-900 dark:text-white">选择素材片段</h3>
              <button
                class="text-xs text-primary hover:text-primary/80 transition-colors"
                @click="handleSelectAll"
              >
                {{ isAllSelected ? '取消全选' : '全选' }}
              </button>
            </div>

            <div v-if="loading" class="flex items-center justify-center py-8">
              <span class="material-symbols-outlined text-4xl text-slate-400 animate-spin">progress_activity</span>
            </div>

            <div v-else-if="materials.length > 0" class="space-y-3 max-h-[600px] overflow-y-auto">
              <div
                v-for="material in materials"
                :key="material.id"
                class="p-3 rounded-md border cursor-pointer transition-all"
                :class="selectedMaterials.has(material.id)
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
                @click="handleSelectMaterial(material.id)"
              >
                <div class="flex items-start gap-3">
                  <input
                    type="checkbox"
                    :checked="selectedMaterials.has(material.id)"
                    class="w-5 h-5 rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary/20 mt-0.5"
                    @click.stop="handleSelectMaterial(material.id)"
                  />
                  <div class="w-16 h-16 rounded-md overflow-hidden bg-slate-100 dark:bg-slate-800 flex-shrink-0">
                    <div class="w-full h-full flex items-center justify-center">
                      <span class="material-symbols-outlined text-2xl text-slate-400">videocam</span>
                    </div>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-sm font-medium text-slate-900 dark:text-white truncate mb-1">
                      {{ material.name }}
                    </div>
                    <div class="text-xs text-slate-500 dark:text-slate-400">
                      {{ material.format }} · {{ material.duration }}s
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="text-center py-8">
              <span class="material-symbols-outlined text-4xl text-slate-300 dark:text-slate-700 mb-2">
                video_library
              </span>
              <p class="text-sm text-slate-500 dark:text-slate-400">暂无素材</p>
            </div>

            <div v-if="selectedMaterials.size > 0" class="mt-4 pt-4 border-t border-slate-200 dark:border-slate-700">
              <div class="text-sm text-slate-600 dark:text-slate-400">
                已选择 <span class="font-semibold text-primary">{{ selectedMaterials.size }}</span> 个素材
              </div>
            </div>
          </div>
        </div>

        <!-- Middle: Configuration -->
        <div class="lg:col-span-1 space-y-6">
          <!-- Duration -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">视频时长</h3>
            <div class="space-y-3">
              <div class="flex items-center justify-between text-sm">
                <span class="text-slate-600 dark:text-slate-400">目标时长</span>
                <span class="font-semibold text-slate-900 dark:text-white">{{ mixParams.duration }}秒</span>
              </div>
              <input
                v-model.number="mixParams.duration"
                type="range"
                min="10"
                max="60"
                step="5"
                class="w-full"
              />
              <div class="flex items-center justify-between text-xs text-slate-400">
                <span>10s</span>
                <span>60s</span>
              </div>
            </div>
          </div>

          <!-- Rhythm -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">混剪节奏</h3>
            <div class="space-y-2">
              <div
                v-for="option in rhythmOptions"
                :key="option.value"
                class="p-3 rounded-md border cursor-pointer transition-all"
                :class="mixParams.rhythm === option.value
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
                @click="mixParams.rhythm = option.value"
              >
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-sm font-medium text-slate-900 dark:text-white">{{ option.label }}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">{{ option.desc }}</div>
                  </div>
                  <div v-if="mixParams.rhythm === option.value">
                    <span class="material-symbols-outlined text-primary">check_circle</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Transition -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">转场效果</h3>
            <div class="space-y-2">
              <div
                v-for="option in transitionOptions"
                :key="option.value"
                class="p-3 rounded-md border cursor-pointer transition-all"
                :class="mixParams.transition === option.value
                  ? 'border-primary bg-primary/5'
                  : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
                @click="mixParams.transition = option.value"
              >
                <div class="flex items-center justify-between">
                  <div>
                    <div class="text-sm font-medium text-slate-900 dark:text-white">{{ option.label }}</div>
                    <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">{{ option.desc }}</div>
                  </div>
                  <div v-if="mixParams.transition === option.value">
                    <span class="material-symbols-outlined text-primary">check_circle</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Music -->
          <div class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">配乐选项</h3>
            <label class="flex items-start gap-3 cursor-pointer">
              <input
                v-model="mixParams.music"
                type="checkbox"
                class="w-5 h-5 rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary/20 mt-0.5"
              />
              <div>
                <div class="text-sm font-medium text-slate-900 dark:text-white">自动配乐</div>
                <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  AI根据视频节奏自动匹配背景音乐
                </div>
              </div>
            </label>
          </div>

          <!-- Generate Button -->
          <button
            class="w-full px-6 py-3 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="generating || selectedMaterials.size < 2"
            @click="handleGenerate"
          >
            {{ generating ? '混剪中...' : '开始混剪' }}
          </button>
        </div>

        <!-- Right: Results -->
        <div class="lg:col-span-1 space-y-6">
          <!-- Progress -->
          <div v-if="generating" class="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 p-6">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">混剪进度</h3>
            <div class="space-y-3">
              <div class="flex items-center justify-between text-sm">
                <span class="text-slate-600 dark:text-slate-400">AI正在智能混剪...</span>
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
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-4">混剪结果</h3>
            <div class="space-y-4">
              <div
                v-for="result in generatedResults"
                :key="result.id"
                class="group relative aspect-video rounded-md overflow-hidden bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
              >
                <div class="absolute inset-0 flex items-center justify-center">
                  <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-600">play_circle</span>
                </div>
                <div class="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/60 to-transparent">
                  <div class="text-xs text-white">
                    {{ result.materialCount }}个素材 · {{ result.duration }}s
                  </div>
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
                auto_awesome_motion
              </span>
              <p class="text-sm text-slate-500 dark:text-slate-400">
                选择至少2个素材并配置参数后，点击"开始混剪"
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
