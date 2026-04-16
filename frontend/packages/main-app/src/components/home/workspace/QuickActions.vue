<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const showAIMenu = ref(false)

const actions = [
  {
    id: 'ai',
    icon: 'auto_awesome',
    label: 'AI生成素材',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50 dark:bg-purple-900/30',
    hasSubmenu: true
  },
  {
    id: 'upload',
    icon: 'upload_file',
    label: '上传素材',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50 dark:bg-blue-900/30',
    route: '/material'
  },
  {
    id: 'campaign',
    icon: 'ads_click',
    label: '创建投放',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50 dark:bg-emerald-900/30',
    route: '/campaign'
  },
  {
    id: 'report',
    icon: 'bar_chart',
    label: '查看报表',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50 dark:bg-orange-900/30',
    route: '/monitor'
  }
]

const aiMethods = [
  { id: 'new', label: '全新生成', icon: 'add_circle', route: '/material/ai-generate/new' },
  { id: 'remix', label: '爆款二创', icon: 'shuffle', route: '/material/ai-generate/remix' },
  { id: 'hot', label: '热点复刻', icon: 'trending_up', route: '/material/ai-generate/hot' },
  { id: 'mix', label: '智能混剪', icon: 'auto_awesome_motion', route: '/material/ai-generate/mix' }
]

const handleAction = (action: any) => {
  if (action.hasSubmenu) {
    showAIMenu.value = !showAIMenu.value
  } else if (action.route) {
    router.push(action.route)
  }
}

const handleAIMethod = (method: any) => {
  if (method.route) {
    router.push(method.route)
  }
  showAIMenu.value = false
}
</script>

<template>
  <div>
    <div class="flex items-center gap-2 mb-3">
      <span class="material-symbols-outlined text-primary text-base">bolt</span>
      <h4 class="text-sm font-semibold text-slate-900 dark:text-white">快速操作</h4>
    </div>

    <div class="p-4 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
      <div class="grid grid-cols-2 gap-2">
        <div
          v-for="action in actions"
          :key="action.id"
          class="relative"
        >
          <button
            class="w-full p-3 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-primary/50 transition-all text-left"
            @click="handleAction(action)"
          >
            <div class="flex items-center gap-2">
              <div class="w-8 h-8 rounded-md flex items-center justify-center" :class="action.bgColor">
                <span class="material-symbols-outlined text-base" :class="action.color">
                  {{ action.icon }}
                </span>
              </div>
              <span class="text-xs font-semibold text-slate-900 dark:text-white">
                {{ action.label }}
              </span>
            </div>
          </button>

          <!-- AI Submenu -->
          <div
            v-if="action.hasSubmenu && showAIMenu"
            class="absolute top-full left-0 right-0 mt-1 p-2 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-lg z-10"
          >
            <button
              v-for="method in aiMethods"
              :key="method.id"
              class="w-full p-2 rounded-md hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-left"
              @click="handleAIMethod(method)"
            >
              <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-primary text-sm">
                  {{ method.icon }}
                </span>
                <span class="text-xs font-semibold text-slate-900 dark:text-white">
                  {{ method.label }}
                </span>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
