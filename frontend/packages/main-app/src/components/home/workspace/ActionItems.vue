<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// Mock data - 实际应该从API获取
const items = ref([
  {
    id: 1,
    type: 'warning',
    icon: 'trending_down',
    title: '投放计划"夏季促销"ROI下降至1.8x',
    description: '建议暂停或更换素材',
    route: '/campaign'
  },
  {
    id: 2,
    type: 'info',
    icon: 'speed',
    title: '素材"角色展示A"CTR低于平均值',
    description: '建议优化素材或进行二创',
    route: '/material'
  },
  {
    id: 3,
    type: 'warning',
    icon: 'account_balance_wallet',
    title: '项目"休闲游戏"预算即将用完',
    description: '建议及时补充预算',
    route: '/projects'
  }
])

const handleViewDetail = (item: any) => {
  if (item.route) {
    router.push(item.route)
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-2">
        <span class="material-symbols-outlined text-primary text-base">notifications_active</span>
        <h4 class="text-sm font-semibold text-slate-900 dark:text-white">需要关注</h4>
        <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-red-50 dark:bg-red-900/30 text-red-600">
          {{ items.length }}
        </span>
      </div>
      <button class="text-xs text-primary hover:underline">
        查看全部
      </button>
    </div>

    <div class="p-4 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
      <div class="space-y-2">
        <div
          v-for="item in items"
          :key="item.id"
          class="p-3 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-primary/50 transition-all cursor-pointer"
          @click="handleViewDetail(item)"
        >
          <div class="flex items-start gap-2">
            <span
              class="material-symbols-outlined text-base flex-shrink-0 mt-0.5"
              :class="item.type === 'warning' ? 'text-yellow-600' : 'text-blue-600'"
            >
              {{ item.icon }}
            </span>
            <div class="flex-1 min-w-0">
              <div class="text-xs font-semibold text-slate-900 dark:text-white mb-1">
                {{ item.title }}
              </div>
              <div class="text-xs text-slate-600 dark:text-slate-400">
                {{ item.description }}
              </div>
            </div>
            <button class="text-xs text-primary hover:underline flex-shrink-0">
              查看详情
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
