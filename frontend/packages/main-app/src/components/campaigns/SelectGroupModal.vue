<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getProjects, type Project } from '@/api/projects'

interface Props {
  show: boolean
}

interface Emits {
  (e: 'close'): void
  (e: 'select', project: Project): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const loading = ref(false)
const projects = ref<Project[]>([])

const createDemoProject = () => ({
  id: `demo-project-${Date.now()}`,
  name: 'Demo 广告项目',
  game_type: 'game',
  target_market: 'US',
  tags: ['demo'],
  total_budget: 0,
  spent: 0,
  status: 'draft',
  manager: 'Demo',
  start_date: '',
  end_date: '',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
})

onMounted(async () => {
  if (props.show) {
    await loadProjects()
  }
})

const loadProjects = async () => {
  loading.value = true
  try {
    const data = await getProjects({ limit: 50 })
    projects.value = data
  } catch (err) {
    console.error('加载项目列表失败:', err)
  } finally {
    loading.value = false
  }
}

const handleSelect = (project: Project) => {
  emit('select', project)
  emit('close')
}

const handleUseDemoProject = () => {
  handleSelect(createDemoProject())
}

const handleClose = () => {
  emit('close')
}

// 监听show变化，重新加载数据
const handleShowChange = async (newShow: boolean) => {
  if (newShow) {
    await loadProjects()
  }
}

// 使用watch监听show变化
import { watch } from 'vue'
watch(() => props.show, handleShowChange)
</script>

<template>
  <!-- 遮罩层 -->
  <Transition name="fade">
    <div
      v-if="show"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      @click.self="handleClose"
    >
      <!-- 弹窗容器 -->
      <Transition name="scale">
        <div
          v-if="show"
          class="bg-white dark:bg-slate-800 rounded-lg shadow-2xl w-full max-w-lg max-h-[70vh] overflow-hidden flex flex-col"
        >
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
            <h3 class="text-lg font-bold text-slate-900 dark:text-white">请选择项目</h3>
            <button
              class="p-1 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              @click="handleClose"
            >
              <span class="material-symbols-outlined text-slate-500">close</span>
            </button>
          </div>

          <!-- 弹窗内容 -->
          <div class="flex-1 overflow-y-auto px-6 py-4">
            <!-- 加载状态 -->
            <div v-if="loading" class="flex items-center justify-center py-12">
              <span class="material-symbols-outlined animate-spin text-4xl text-primary">progress_activity</span>
            </div>

            <!-- 项目列表 -->
            <div v-else-if="projects.length > 0" class="space-y-3">
              <div
                v-for="project in projects"
                :key="project.id"
                class="p-4 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-primary hover:bg-primary/5 transition-all cursor-pointer"
                @click="handleSelect(project)"
              >
                <div class="font-semibold text-slate-900 dark:text-white mb-1">
                  {{ project.name }}
                </div>
                <div class="text-sm text-slate-500 dark:text-slate-400">
                  {{ project.game_type }}
                </div>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-else class="flex flex-col items-center justify-center py-12 text-center">
              <span class="material-symbols-outlined text-6xl text-slate-300 dark:text-slate-700 mb-4">folder_off</span>
              <p class="text-sm font-semibold text-slate-700 dark:text-slate-300">暂无项目</p>
              <p class="mt-1 max-w-xs text-xs leading-5 text-slate-500 dark:text-slate-400">
                项目接口为空时，可以先使用 Demo 项目完成前端创建流程测试。
              </p>
              <button
                class="mt-5 inline-flex items-center gap-2 whitespace-nowrap rounded-md bg-primary px-4 py-2 text-sm font-semibold text-white hover:bg-primary/90"
                @click="handleUseDemoProject"
              >
                <span class="material-symbols-outlined text-base">add</span>
                使用 Demo 项目继续
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.scale-enter-active,
.scale-leave-active {
  transition: all 0.2s ease;
}

.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
