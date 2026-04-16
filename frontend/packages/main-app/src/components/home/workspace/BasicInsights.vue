<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// Mock insights based on simple rules
const insights = ref([
  {
    id: 1,
    type: 'warning',
    icon: 'trending_down',
    title: 'ROI下降的投放建议暂停或调整素材',
    description: '投放计划"夏季促销"ROI从2.5x降至1.8x',
    action: '查看详情',
    route: '/campaign'
  },
  {
    id: 2,
    type: 'success',
    icon: 'auto_awesome',
    title: '有3个高ROI素材可以进行二创',
    description: '这些素材ROI超过3.5x，建议生成变体扩大投放',
    action: '立即二创',
    route: '/material/ai-generate/remix'
  },
  {
    id: 3,
    type: 'info',
    icon: 'account_balance_wallet',
    title: '预算不足的项目建议及时补充',
    description: '项目"休闲游戏"预算使用率已达92%',
    action: '查看项目',
    route: '/projects'
  }
])

const handleAction = (insight: any) => {
  if (insight.route) {
    router.push(insight.route)
  }
}
</script>

<template>
  <div>
    <div class="flex items-center gap-2 mb-3">
      <span class="material-symbols-outlined text-primary text-base">lightbulb</span>
      <h4 class="text-sm font-semibold text-slate-900 dark:text-white">优化建议</h4>
      <span class="text-xs text-slate-500 dark:text-slate-400">(基础版)</span>
    </div>

    <div class="p-4 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
      <div class="space-y-2">
        <div
          v-for="insight in insights"
          :key="insight.id"
          class="p-3 rounded-md border transition-all cursor-pointer"
          :class="{
            'border-yellow-200 dark:border-yellow-800 bg-yellow-50/50 dark:bg-yellow-900/10 hover:border-yellow-300': insight.type === 'warning',
            'border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-900/10 hover:border-emerald-300': insight.type === 'success',
            'border-blue-200 dark:border-blue-800 bg-blue-50/50 dark:bg-blue-900/10 hover:border-blue-300': insight.type === 'info'
          }"
          @click="handleAction(insight)"
        >
          <div class="flex items-start gap-2">
            <span
              class="material-symbols-outlined text-base flex-shrink-0 mt-0.5"
              :class="{
                'text-yellow-600': insight.type === 'warning',
                'text-emerald-600': insight.type === 'success',
                'text-blue-600': insight.type === 'info'
              }"
            >
              {{ insight.icon }}
            </span>
            <div class="flex-1 min-w-0">
              <div class="text-xs font-semibold text-slate-900 dark:text-white mb-1">
                {{ insight.title }}
              </div>
              <div class="text-xs text-slate-600 dark:text-slate-400 mb-2">
                {{ insight.description }}
              </div>
              <button class="text-xs font-medium text-primary hover:underline">
                {{ insight.action }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
