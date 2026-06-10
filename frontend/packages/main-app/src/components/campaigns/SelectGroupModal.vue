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
          class="bg-white dark:bg-slate-800 rounded-md shadow-2xl w-full max-w-[390px] max-h-[70vh] overflow-hidden flex flex-col"
        >
          <!-- 弹窗头部 -->
          <div class="flex items-center justify-between px-[19px] py-[12px] border-b border-slate-200 dark:border-slate-700">
            <h3 class="text-[15px] font-bold text-slate-900 dark:text-white">请选择项目</h3>
            <button
              class="p-[4px] rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              @click="handleClose"
            >
              <span class="material-symbols-outlined text-[17px] text-slate-500">close</span>
            </button>
          </div>

          <!-- 弹窗内容 -->
          <div class="flex-1 overflow-y-auto px-[19px] py-[12px]">
            <!-- 加载状态 -->
            <div v-if="loading" class="flex items-center justify-center py-[37px]">
              <span class="material-symbols-outlined animate-spin text-[31px] text-primary">progress_activity</span>
            </div>

            <!-- 项目列表 -->
            <div v-else-if="projects.length > 0" class="space-y-[9px]">
              <div
                v-for="project in projects"
                :key="project.id"
                class="p-[12px] rounded-md border border-slate-200 dark:border-slate-700 hover:border-primary hover:bg-primary/5 transition-all cursor-pointer"
                @click="handleSelect(project)"
              >
                <div class="font-semibold text-[13px] text-slate-900 dark:text-white mb-[4px]">
                  {{ project.name }}
                </div>
                <div class="text-[11px] text-slate-500 dark:text-slate-400">
                  {{ project.game_type }}
                </div>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-else class="flex flex-col items-center justify-center py-[37px]">
              <span class="material-symbols-outlined text-[47px] text-slate-300 dark:text-slate-700 mb-[12px]">folder_off</span>
              <p class="text-[11px] text-slate-500 dark:text-slate-400">暂无项目</p>
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
