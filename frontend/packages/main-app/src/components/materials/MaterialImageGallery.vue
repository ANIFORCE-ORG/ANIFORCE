<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getMaterials, getMaterialImage, type Material, type MaterialImage } from '@/api/materials'

interface Props {
  projectId?: string
  campaignId?: string
  type?: string
  limit?: number
}

const props = withDefaults(defineProps<Props>(), {
  limit: 20
})

const emit = defineEmits<{
  selectMaterial: [material: Material]
  selectImage: [image: MaterialImage]
}>()

const materials = ref<Material[]>([])
const loadedImages = ref<Map<string, MaterialImage>>(new Map())
const loading = ref(false)
const error = ref<string | null>(null)
const selectedMaterialId = ref<string | null>(null)

onMounted(async () => {
  await loadMaterials()
})

const loadMaterials = async () => {
  loading.value = true
  error.value = null
  
  try {
    const data = await getMaterials({
      project_id: props.projectId,
      campaign_id: props.campaignId,
      type: props.type,
      limit: props.limit
    })
    materials.value = data
  } catch (err: any) {
    error.value = err.message || '加载素材失败'
    console.error('加载素材失败:', err)
  } finally {
    loading.value = false
  }
}

const loadImage = async (materialId: string, thumbnail: boolean = true) => {
  if (loadedImages.value.has(materialId)) {
    return loadedImages.value.get(materialId)
  }
  
  try {
    const image = await getMaterialImage(materialId, thumbnail)
    loadedImages.value.set(materialId, image)
    return image
  } catch (err) {
    console.error('加载图像失败:', err)
    return null
  }
}

const handleMaterialClick = async (material: Material) => {
  selectedMaterialId.value = material.id
  emit('selectMaterial', material)
  
  const image = await loadImage(material.id, false)
  if (image) {
    emit('selectImage', image)
  }
}

const getImageSrc = (material: Material): string => {
  const loaded = loadedImages.value.get(material.id)
  if (loaded) {
    return loaded.data
  }
  
  loadImage(material.id, true)
  return material.thumbnail_url || material.url || ''
}
</script>

<template>
  <div class="material-gallery">
    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-16">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="flex flex-col items-center justify-center py-16">
      <span class="material-symbols-outlined text-6xl text-red-400 mb-4">error</span>
      <p class="text-sm text-red-600 dark:text-red-400">{{ error }}</p>
      <button
        class="mt-4 px-4 py-2 rounded-md bg-primary text-white hover:bg-primary/90 transition-colors"
        @click="loadMaterials"
      >
        重试
      </button>
    </div>

    <!-- Gallery Grid -->
    <div v-else-if="materials.length > 0" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      <div
        v-for="material in materials"
        :key="material.id"
        class="relative group cursor-pointer rounded-lg overflow-hidden border-2 transition-all"
        :class="[
          selectedMaterialId === material.id
            ? 'border-primary shadow-lg'
            : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'
        ]"
        @click="handleMaterialClick(material)"
      >
        <!-- Image -->
        <div class="aspect-video bg-slate-100 dark:bg-slate-800 relative overflow-hidden">
          <img
            :src="getImageSrc(material)"
            :alt="material.name"
            class="w-full h-full object-cover transition-transform group-hover:scale-105"
            loading="lazy"
          />
          
          <!-- Overlay on hover -->
          <div class="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <span class="material-symbols-outlined text-white text-4xl">visibility</span>
          </div>
        </div>

        <!-- Info -->
        <div class="p-3 bg-white dark:bg-slate-900">
          <h4 class="text-sm font-semibold text-slate-900 dark:text-white truncate mb-1">
            {{ material.name }}
          </h4>
          <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
            <span class="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800">
              {{ material.type }}
            </span>
            <span v-if="material.ctr_estimate" class="font-medium text-emerald-600">
              CTR: {{ (material.ctr_estimate * 100).toFixed(1) }}%
            </span>
          </div>
          
          <!-- Tags -->
          <div v-if="material.tags.length > 0" class="flex gap-1 mt-2 flex-wrap">
            <span
              v-for="tag in material.tags.slice(0, 3)"
              :key="tag"
              class="text-xs px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
            >
              {{ tag }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="flex flex-col items-center justify-center py-16">
      <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">image</span>
      <p class="text-sm text-slate-500 dark:text-slate-400">暂无素材</p>
    </div>
  </div>
</template>

<style scoped>
.material-gallery {
  width: 100%;
}
</style>
