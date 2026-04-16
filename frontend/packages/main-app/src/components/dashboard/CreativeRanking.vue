<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

interface Material {
  id: string
  name: string
  thumbnail_url?: string
  ctr: number
  spend: number
  roi: number
  status: string
}

interface Props {
  materials?: Material[]
}

const props = defineProps<Props>()
const router = useRouter()

// 计算排行榜数据（只显示运行中的素材，按ROI排序，取前5）
const topMaterials = computed(() => {
  if (!props.materials || props.materials.length === 0) {
    return []
  }

  return props.materials
    .filter(m => m.status === 'running')
    .sort((a, b) => b.roi - a.roi)
    .slice(0, 5)
})

// 跳转到素材详情
const handleMaterialClick = (materialId: string) => {
  router.push(`/materials/${materialId}`)
}

// 获取排名样式
const getRankClass = (index: number): string => {
  if (index === 0) return 'bg-yellow-500 text-white'
  if (index === 1) return 'bg-slate-400 text-white'
  if (index === 2) return 'bg-orange-600 text-white'
  return 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
}
</script>

<template>
  <div class="space-y-2">
    <div
      v-for="(material, index) in topMaterials"
      :key="material.id"
      class="flex items-center gap-3 p-3 rounded-md bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
      @click="handleMaterialClick(material.id)"
    >
      <!-- 排名 -->
      <div
        class="w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm flex-shrink-0"
        :class="getRankClass(index)"
      >
        {{ index + 1 }}
      </div>

      <!-- 缩略图 -->
      <div class="w-12 h-12 rounded-md overflow-hidden bg-slate-200 dark:bg-slate-700 flex-shrink-0">
        <img
          v-if="material.thumbnail_url"
          :src="material.thumbnail_url"
          :alt="material.name"
          class="w-full h-full object-cover"
        />
        <div v-else class="w-full h-full flex items-center justify-center">
          <span class="material-symbols-outlined text-slate-400 text-2xl">
            image
          </span>
        </div>
      </div>

      <!-- 素材信息 -->
      <div class="flex-1 min-w-0">
        <div class="text-sm font-semibold text-slate-900 dark:text-white truncate mb-1">
          {{ material.name }}
        </div>
        <div class="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
          <span>CTR {{ (material.ctr * 100).toFixed(2) }}%</span>
          <span>·</span>
          <span>${{ material.spend.toLocaleString() }}</span>
        </div>
      </div>

      <!-- ROI -->
      <div class="text-right flex-shrink-0">
        <div
          class="text-lg font-bold"
          :class="material.roi >= 2.0 ? 'text-green-600 dark:text-green-400' : 'text-slate-900 dark:text-white'"
        >
          {{ material.roi.toFixed(1) }}x
        </div>
        <div class="text-xs text-slate-400">ROI</div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="topMaterials.length === 0" class="text-center py-8">
      <span class="material-symbols-outlined text-4xl text-slate-300 dark:text-slate-700 mb-2">
        emoji_events
      </span>
      <p class="text-sm text-slate-500 dark:text-slate-400">暂无素材数据</p>
    </div>
  </div>
</template>
