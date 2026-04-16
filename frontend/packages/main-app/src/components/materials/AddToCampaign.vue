<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { getCampaigns, type Campaign } from '@/api/campaigns'

interface Material {
  id: string
  name: string
}

interface Props {
  material?: Material
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'add-complete'): void
  (e: 'close'): void
}>()

const loading = ref(false)
const campaigns = ref<Campaign[]>([])
const selectedCampaigns = ref<Set<string>>(new Set())
const searchQuery = ref('')

// 加载广告计划列表
onMounted(async () => {
  try {
    loading.value = true
    const data = await getCampaigns()
    // 只显示运行中的广告
    campaigns.value = data.filter(c => c.status === 'running')
  } catch (err) {
    console.error('加载广告计划失败:', err)
  } finally {
    loading.value = false
  }
})

// 过滤后的广告列表
const filteredCampaigns = computed(() => {
  if (!searchQuery.value.trim()) {
    return campaigns.value
  }

  const query = searchQuery.value.toLowerCase()
  return campaigns.value.filter(c =>
    c.name.toLowerCase().includes(query) ||
    c.project_name.toLowerCase().includes(query)
  )
})

// 切换选择
const toggleSelect = (campaignId: string) => {
  if (selectedCampaigns.value.has(campaignId)) {
    selectedCampaigns.value.delete(campaignId)
  } else {
    selectedCampaigns.value.add(campaignId)
  }
}

// 全选/取消全选
const toggleSelectAll = () => {
  if (selectedCampaigns.value.size === filteredCampaigns.value.length) {
    selectedCampaigns.value.clear()
  } else {
    selectedCampaigns.value = new Set(filteredCampaigns.value.map(c => c.id))
  }
}

const isAllSelected = computed(() => {
  return filteredCampaigns.value.length > 0 &&
         selectedCampaigns.value.size === filteredCampaigns.value.length
})

// 添加到投放计划
const handleAdd = async () => {
  if (selectedCampaigns.value.size === 0) {
    alert('请至少选择一个投放计划')
    return
  }

  try {
    loading.value = true
    // TODO: 调用API将素材添加到选中的投放计划
    // await addMaterialToCampaigns(props.material?.id, Array.from(selectedCampaigns.value))

    console.log('添加素材到投放计划:', {
      materialId: props.material?.id,
      campaignIds: Array.from(selectedCampaigns.value)
    })

    emit('add-complete')
    handleClose()
  } catch (err: any) {
    console.error('添加失败:', err)
    alert(err.message || '添加失败，请重试')
  } finally {
    loading.value = false
  }
}

const handleClose = () => {
  emit('close')
}

// 获取平台标签颜色
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
  <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="handleClose">
    <div class="bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-3xl max-h-[80vh] flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between p-6 border-b border-slate-200 dark:border-slate-700">
        <div>
          <h3 class="text-lg font-bold text-slate-900 dark:text-white">添加到投放计划</h3>
          <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
            素材: {{ material?.name }}
          </p>
        </div>
        <button
          class="w-8 h-8 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center justify-center transition-colors"
          @click="handleClose"
        >
          <span class="material-symbols-outlined text-slate-600 dark:text-slate-400">close</span>
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- Search -->
        <div class="mb-4">
          <div class="relative">
            <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-lg">search</span>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索投放计划..."
              class="w-full pl-10 pr-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>
        </div>

        <!-- Select All -->
        <div class="flex items-center gap-2 mb-3 pb-3 border-b border-slate-200 dark:border-slate-700">
          <input
            type="checkbox"
            :checked="isAllSelected"
            @change="toggleSelectAll"
            class="w-4 h-4 rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary/20"
          />
          <span class="text-sm text-slate-600 dark:text-slate-400">
            全选 ({{ selectedCampaigns.size }}/{{ filteredCampaigns.length }})
          </span>
        </div>

        <!-- Campaign List -->
        <div v-if="loading" class="flex items-center justify-center py-16">
          <span class="material-symbols-outlined text-4xl text-slate-400 animate-spin">progress_activity</span>
        </div>

        <div v-else-if="filteredCampaigns.length > 0" class="space-y-2">
          <div
            v-for="campaign in filteredCampaigns"
            :key="campaign.id"
            class="flex items-center gap-3 p-3 rounded-md border transition-all cursor-pointer"
            :class="selectedCampaigns.has(campaign.id)
              ? 'border-primary bg-primary/5'
              : 'border-slate-200 dark:border-slate-700 hover:border-primary/50'"
            @click="toggleSelect(campaign.id)"
          >
            <input
              type="checkbox"
              :checked="selectedCampaigns.has(campaign.id)"
              class="w-4 h-4 rounded border-slate-300 dark:border-slate-600 text-primary focus:ring-primary/20"
              @click.stop="toggleSelect(campaign.id)"
            />
            <div class="flex-1 min-w-0">
              <div class="text-sm font-semibold text-slate-900 dark:text-white truncate mb-1">
                {{ campaign.name }}
              </div>
              <div class="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
                <span>{{ campaign.project_name }}</span>
                <span>·</span>
                <span class="px-2 py-0.5 rounded text-[10px] font-medium" :class="getPlatformColor(campaign.platform)">
                  {{ campaign.platform }}
                </span>
              </div>
            </div>
            <div class="text-right flex-shrink-0">
              <div class="text-xs text-slate-500 dark:text-slate-400">消耗</div>
              <div class="text-sm font-semibold text-slate-900 dark:text-white">
                ${{ campaign.spent?.toLocaleString() || 0 }}
              </div>
            </div>
          </div>
        </div>

        <div v-else class="flex flex-col items-center justify-center py-16">
          <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">
            campaign
          </span>
          <p class="text-sm text-slate-500 dark:text-slate-400">
            {{ searchQuery ? '未找到匹配的投放计划' : '暂无运行中的投放计划' }}
          </p>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center justify-between p-6 border-t border-slate-200 dark:border-slate-700">
        <div class="text-sm text-slate-600 dark:text-slate-400">
          已选择 {{ selectedCampaigns.size }} 个投放计划
        </div>
        <div class="flex items-center gap-3">
          <button
            class="px-4 py-2 rounded-md border border-slate-200 dark:border-slate-700 text-sm font-medium text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
            @click="handleClose"
          >
            取消
          </button>
          <button
            class="px-4 py-2 rounded-md bg-primary text-white text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="selectedCampaigns.size === 0 || loading"
            @click="handleAdd"
          >
            {{ loading ? '添加中...' : '确认添加' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
