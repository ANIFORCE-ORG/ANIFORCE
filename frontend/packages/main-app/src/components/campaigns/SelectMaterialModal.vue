<script setup lang="ts">
import { ref, watch } from 'vue'
import { getMaterials, getMaterialImage, type Material } from '@/api/materials'

interface Props {
  show: boolean
  selectedIds?: string[]
}

interface Emits {
  (e: 'close'): void
  (e: 'select', materials: Material[]): void
  (e: 'create-material'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const loading = ref(false)
const materials = ref<Material[]>([])
const materialThumbnails = ref<Record<string, string>>({})
const selectedMaterialIds = ref<string[]>([])
const searchQuery = ref('')
const typeFilter = ref('all')

// 加载素材数据
const loadMaterials = async () => {
  loading.value = true
  try {
    const data = await getMaterials()
    materials.value = data
    filteredMaterials.value = data  // 初始化过滤结果
    
    // 初始化已选择的素材
    if (props.selectedIds) {
      selectedMaterialIds.value = [...props.selectedIds]
    }
    
    // 异步加载缩略图
    loadThumbnails(data)
  } catch (err) {
    console.error('加载素材失败:', err)
  } finally {
    loading.value = false
  }
}

// 加载素材缩略图
const loadThumbnails = async (materialList: Material[]) => {
  for (const material of materialList) {
    try {
      const imageData = await getMaterialImage(material.id, true)
      materialThumbnails.value[material.id] = imageData.data
    } catch (err) {
      console.error(`加载素材${material.id}缩略图失败:`, err)
    }
  }
}

// 监听弹窗显示状态
watch(() => props.show, (newVal) => {
  if (newVal) {
    loadMaterials()
  }
})

// 切换素材选择
const toggleMaterial = (materialId: string) => {
  const index = selectedMaterialIds.value.indexOf(materialId)
  if (index > -1) {
    selectedMaterialIds.value.splice(index, 1)
  } else {
    selectedMaterialIds.value.push(materialId)
  }
}

// 确认选择
const handleConfirm = () => {
  const selectedMaterialObjects = materials.value.filter(m => 
    selectedMaterialIds.value.includes(m.id)
  )
  emit('select', selectedMaterialObjects)
  emit('close')
}

// 关闭弹窗
const handleClose = () => {
  emit('close')
}

const handleCreateMaterial = () => {
  emit('close')
  emit('create-material')
}

// 过滤素材
const filteredMaterials = ref<Material[]>([])
const updateFilteredMaterials = () => {
  let result = materials.value

  // 按类型筛选
  if (typeFilter.value !== 'all') {
    result = result.filter(m => m.type === typeFilter.value)
  }

  // 按搜索关键词筛选
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(m => 
      m.name.toLowerCase().includes(query)
    )
  }

  filteredMaterials.value = result
}

// 监听筛选条件变化
const handleSearch = () => {
  updateFilteredMaterials()
}

const handleTypeFilter = (type: string) => {
  typeFilter.value = type
  updateFilteredMaterials()
}
</script>

<template>
  <div
    v-if="show"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    @click.self="handleClose"
  >
    <div class="bg-white dark:bg-slate-900 rounded-lg shadow-xl w-full max-w-4xl max-h-[80vh] flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-800">
        <h3 class="text-lg font-semibold text-slate-900 dark:text-white">选择素材</h3>
        <button
          @click="handleClose"
          class="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">close</span>
        </button>
      </div>

      <!-- Search and Filter -->
      <div class="p-6 border-b border-slate-200 dark:border-slate-800">
        <div class="flex gap-4">
          <!-- 搜索框 -->
          <div class="flex-1">
            <input
              v-model="searchQuery"
              @input="handleSearch"
              type="text"
              placeholder="搜索素材名称或描述..."
              class="w-full px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <!-- 类型筛选 -->
          <div class="flex gap-2">
            <button
              @click="handleTypeFilter('all')"
              class="px-4 py-2 rounded-md transition-colors"
              :class="typeFilter === 'all' 
                ? 'bg-primary text-white' 
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'"
            >
              全部
            </button>
            <button
              @click="handleTypeFilter('image')"
              class="px-4 py-2 rounded-md transition-colors"
              :class="typeFilter === 'image' 
                ? 'bg-primary text-white' 
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'"
            >
              图片
            </button>
            <button
              @click="handleTypeFilter('video')"
              class="px-4 py-2 rounded-md transition-colors"
              :class="typeFilter === 'video' 
                ? 'bg-primary text-white' 
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'"
            >
              视频
            </button>
          </div>
        </div>

        <!-- 已选择数量 -->
        <div class="mt-4 text-sm text-slate-600 dark:text-slate-400">
          已选择 {{ selectedMaterialIds.length }} 个素材
        </div>
      </div>

      <!-- Material List -->
      <div class="flex-1 overflow-y-auto p-6">
        <div v-if="loading" class="flex items-center justify-center py-12">
          <div class="text-slate-500 dark:text-slate-400">加载中...</div>
        </div>

        <div v-else-if="filteredMaterials.length === 0" class="flex flex-col items-center justify-center py-12 text-center">
          <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">image_not_supported</span>
          <div class="text-sm font-semibold text-slate-700 dark:text-slate-300">
            {{ materials.length === 0 ? '素材库暂无素材' : '没有匹配的素材' }}
          </div>
          <p class="mt-2 max-w-sm text-xs leading-5 text-slate-500 dark:text-slate-400">
            创建广告计划可以先保存草稿。需要投放素材时，请到创意素材模块上传或生成素材后再回来选择。
          </p>
          <button
            class="mt-5 inline-flex items-center gap-2 whitespace-nowrap rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90"
            @click="handleCreateMaterial"
          >
            <span class="material-symbols-outlined text-base">video_library</span>
            去素材模块创建素材
          </button>
        </div>

        <div v-else class="grid grid-cols-3 gap-4">
          <div
            v-for="material in filteredMaterials"
            :key="material.id"
            class="relative group cursor-pointer rounded-lg border-2 transition-all overflow-hidden"
            :class="selectedMaterialIds.includes(material.id)
              ? 'border-primary bg-primary/5'
              : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
            @click="toggleMaterial(material.id)"
          >
            <!-- 素材预览 -->
            <div class="aspect-video bg-slate-100 dark:bg-slate-800 flex items-center justify-center overflow-hidden">
              <img
                v-if="materialThumbnails[material.id]"
                :src="materialThumbnails[material.id]"
                :alt="material.name"
                class="w-full h-full object-cover"
              />
              <span v-else class="material-symbols-outlined text-4xl text-slate-400">
                {{ material.type === 'video' ? 'videocam' : 'image' }}
              </span>
            </div>

            <!-- 素材信息 -->
            <div class="p-3">
              <div class="font-medium text-sm text-slate-900 dark:text-white truncate">
                {{ material.name }}
              </div>
              <div class="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {{ material.type === 'video' ? '视频' : '图片' }} · CTR {{ material.ctr_estimate || 0 }}%
              </div>
            </div>

            <!-- 选中标记 -->
            <div
              v-if="selectedMaterialIds.includes(material.id)"
              class="absolute top-2 right-2 w-6 h-6 rounded-full bg-primary flex items-center justify-center"
            >
              <span class="material-symbols-outlined text-white text-sm">check</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-end gap-3 p-6 border-t border-slate-200 dark:border-slate-800">
        <button
          @click="handleClose"
          class="px-6 py-2 rounded-md border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
        >
          取消
        </button>
        <button
          @click="handleConfirm"
          class="px-6 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
        >
          确认选择 ({{ selectedMaterialIds.length }})
        </button>
      </div>
    </div>
  </div>
</template>
