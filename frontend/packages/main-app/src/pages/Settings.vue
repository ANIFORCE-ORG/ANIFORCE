<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { getAIUsageLogs, getAIUsageSummary, setAIUsageBudget, type AIUsageLog } from '@/api/ai'

const router = useRouter()
const showAIUsage = ref(false)
const aiUsageLoading = ref(false)
const aiUsageError = ref('')
const aiUsageSummary = ref<{
  total_tokens: number
  estimated_cost_usd: number
  by_scenario: Record<string, { total_tokens: number; estimated_cost_usd: number }>
} | null>(null)
const aiUsageLogs = ref<AIUsageLog[]>([])
const dailyTokenLimit = ref(60000)

const settingCards = [
  {
    id: 'agent-account',
    icon: 'admin_panel_settings',
    title: 'Agent 系统账号',
    description: '管理团队成员、登录身份和基础账号信息',
    action: '进入账号设置',
    path: '',
  },
  {
    id: 'system',
    icon: 'tune',
    title: '系统设置',
    description: '配置默认偏好、通知、权限和系统级策略',
    action: '进入系统设置',
    path: '',
  },
  {
    id: 'platform-connections',
    icon: 'hub',
    title: '平台连接',
    description: '连接 Meta、Google、TikTok 广告平台和同步广告账户',
    action: '管理平台连接',
    path: '/platform-connections',
  },
  {
    id: 'ai-usage',
    icon: 'monitoring',
    title: 'AI 使用量',
    description: '查看模型调用、Token 消耗、场景日志和预算限制',
    action: '查看使用量',
    path: '',
  },
]

const switchPanel = (item: { path: string }) => {
  if (item.path) router.push(item.path)
}

const formatCost = (value?: number) => `$${(value || 0).toFixed(4)}`

const loadAIUsage = async () => {
  aiUsageLoading.value = true
  aiUsageError.value = ''
  try {
    const [summary, logs] = await Promise.all([
      getAIUsageSummary(),
      getAIUsageLogs({ limit: 20 }),
    ])
    aiUsageSummary.value = summary
    aiUsageLogs.value = logs
  } catch (err: any) {
    aiUsageError.value = err.message || '加载 AI 使用量失败'
  } finally {
    aiUsageLoading.value = false
  }
}

const openAIUsage = async () => {
  showAIUsage.value = true
  await loadAIUsage()
}

const saveAIBudget = async () => {
  aiUsageLoading.value = true
  aiUsageError.value = ''
  try {
    await setAIUsageBudget({
      scope_type: 'user',
      daily_token_limit: dailyTokenLimit.value,
      monthly_token_limit: 1000000,
      daily_cost_limit_usd: 20,
      monthly_cost_limit_usd: 500,
      enabled: true,
    })
    await loadAIUsage()
  } catch (err: any) {
    aiUsageError.value = err.message || '保存 AI 预算失败'
  } finally {
    aiUsageLoading.value = false
  }
}

onMounted(() => {
  if (window.location.search.includes('panel=ai-usage')) {
    openAIUsage()
  }
})
</script>

<template>
  <div class="flex h-[calc(100vh-120px)] w-full overflow-hidden bg-slate-50 dark:bg-slate-950">
    <SidebarNav active-panel="settings" @switch-panel="switchPanel" />

    <main class="flex-1 overflow-y-auto bg-white dark:bg-slate-900">
      <div class="border-b border-slate-200 dark:border-slate-800 px-6 py-4">
        <h1 class="text-xl font-bold text-slate-900 dark:text-white">设置</h1>
        <p class="text-sm text-slate-500 mt-1">管理 Agent 系统账号、系统配置和广告平台连接</p>
      </div>

      <div class="p-6 grid gap-4 md:grid-cols-3">
        <section
          v-for="card in settingCards"
          :key="card.id"
          class="rounded-md border border-slate-200 p-5 bg-white"
        >
          <div class="flex items-center gap-3">
            <span class="material-symbols-outlined text-primary text-2xl">{{ card.icon }}</span>
            <h2 class="font-semibold text-slate-900">{{ card.title }}</h2>
          </div>
          <p class="mt-3 text-sm text-slate-500 min-h-10">{{ card.description }}</p>
          <button
            class="mt-5 px-4 py-2 rounded-md text-sm font-medium"
            :class="card.path || card.id === 'ai-usage' ? 'bg-primary text-white' : 'border border-slate-200 text-slate-500 cursor-not-allowed'"
            :disabled="!card.path && card.id !== 'ai-usage'"
            @click="card.id === 'ai-usage' ? openAIUsage() : card.path && router.push(card.path)"
          >
            {{ card.action }}
          </button>
        </section>
      </div>

      <section v-if="showAIUsage" class="mx-6 mb-6 rounded-md border border-slate-200 bg-white p-5">
        <div class="mb-5 flex items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold text-slate-900">AI 使用量</h2>
            <p class="text-sm text-slate-500">模型调用、Token 消耗、场景日志和预算配置</p>
          </div>
          <button
            class="rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
            @click="loadAIUsage"
          >
            刷新
          </button>
        </div>

        <div v-if="aiUsageError" class="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
          {{ aiUsageError }}
        </div>

        <div class="grid gap-3 md:grid-cols-3">
          <div class="rounded-md bg-slate-50 px-4 py-3">
            <div class="text-xs text-slate-500">总 Token</div>
            <div class="mt-1 text-xl font-semibold text-slate-900">{{ aiUsageSummary?.total_tokens || 0 }}</div>
          </div>
          <div class="rounded-md bg-slate-50 px-4 py-3">
            <div class="text-xs text-slate-500">预估成本</div>
            <div class="mt-1 text-xl font-semibold text-slate-900">{{ formatCost(aiUsageSummary?.estimated_cost_usd) }}</div>
          </div>
          <div class="rounded-md bg-slate-50 px-4 py-3">
            <div class="text-xs text-slate-500">日 Token 限额</div>
            <div class="mt-2 flex items-center gap-2">
              <input
                v-model.number="dailyTokenLimit"
                type="number"
                min="1"
                class="w-full rounded-md border border-slate-200 px-3 py-2 text-sm"
              />
              <button
                class="rounded-md bg-primary px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
                :disabled="aiUsageLoading"
                @click="saveAIBudget"
              >
                保存
              </button>
            </div>
          </div>
        </div>

        <div class="mt-5 grid gap-3 md:grid-cols-2">
          <div class="rounded-md border border-slate-200 p-4">
            <h3 class="mb-3 text-sm font-semibold text-slate-900">场景汇总</h3>
            <div class="space-y-2">
              <div
                v-for="(item, scenario) in aiUsageSummary?.by_scenario || {}"
                :key="scenario"
                class="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2 text-sm"
              >
                <span class="font-medium text-slate-700">{{ scenario }}</span>
                <span class="text-slate-500">{{ item.total_tokens }} Token · {{ formatCost(item.estimated_cost_usd) }}</span>
              </div>
              <div v-if="!aiUsageSummary || Object.keys(aiUsageSummary.by_scenario).length === 0" class="text-sm text-slate-500">
                暂无调用记录
              </div>
            </div>
          </div>

          <div class="rounded-md border border-slate-200 p-4">
            <h3 class="mb-3 text-sm font-semibold text-slate-900">最近调用</h3>
            <div class="max-h-80 overflow-y-auto">
              <table class="w-full text-left text-xs">
                <thead class="text-slate-500">
                  <tr>
                    <th class="py-2">场景</th>
                    <th class="py-2">模型</th>
                    <th class="py-2 text-right">Token</th>
                    <th class="py-2 text-right">状态</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="log in aiUsageLogs" :key="log.id" class="border-t border-slate-100">
                    <td class="py-2 text-slate-700">{{ log.scenario }}</td>
                    <td class="py-2 text-slate-500">{{ log.model || '-' }}</td>
                    <td class="py-2 text-right text-slate-700">{{ log.total_tokens }}</td>
                    <td class="py-2 text-right text-slate-500">{{ log.status }}</td>
                  </tr>
                  <tr v-if="aiUsageLogs.length === 0">
                    <td colspan="4" class="py-6 text-center text-slate-500">暂无调用日志</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>
