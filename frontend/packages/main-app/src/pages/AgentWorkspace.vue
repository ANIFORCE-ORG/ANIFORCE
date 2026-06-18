<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import SidebarNav from '@/components/layout/SidebarNav.vue'
import { navItems } from '@/config/navigation'

const router = useRouter()

type TaskPhase = 'idle' | 'query' | 'analyze' | 'propose' | 'confirm' | 'execute' | 'done'
type WorkspacePanel = 'context' | 'analysis' | 'budget' | 'audit'

const phase = ref<TaskPhase>('idle')
const panel = ref<WorkspacePanel>('context')
const hitlPending = ref(false)

const sessions = ref([
  { id: 's1', name: 'Summer Sale 优化', active: true },
  { id: 's2', name: '素材效果分析', active: false },
])

const project = {
  name: 'Summer Sale Campaign',
  campaigns: [
    { id: 'a', name: 'Meta 推广', budget: 5000, roi: 1.4 },
    { id: 'b', name: 'Google 搜索', budget: 3000, roi: 2.8 },
  ]
}

const messages = ref<any[]>([
  { role: 'user', text: '分析这两个计划表现，给我预算调整建议' },
])

const timeline = ref([
  { label: '接收上下文', status: 'done' },
  { label: '查询 performance', status: 'idle' },
  { label: '生成分析', status: 'idle' },
  { label: '预算方案', status: 'idle' },
  { label: 'HITL 确认', status: 'idle' },
  { label: '写入 DB', status: 'idle' },
])

function start() {
  phase.value = 'query'
  timeline.value[1].status = 'active'
  messages.value.push({ role: 'assistant', text: '正在查询 DB 确认事实数据...' })
}

function next() {
  if (phase.value === 'query') {
    phase.value = 'analyze'
    timeline.value[1].status = 'done'
    timeline.value[2].status = 'active'
    panel.value = 'analysis'
    messages.value.push({ role: 'assistant', text: '分析完成。计划 A ROI 1.4，计划 B ROI 2.8。右侧已展示报告。' })
  } else if (phase.value === 'analyze') {
    phase.value = 'propose'
    timeline.value[2].status = 'done'
    timeline.value[3].status = 'active'
    panel.value = 'budget'
    messages.value.push({ role: 'assistant', text: '已生成预算方案。右侧可查看详情。' })
  } else if (phase.value === 'propose') {
    phase.value = 'confirm'
    timeline.value[3].status = 'done'
    timeline.value[4].status = 'blocked'
    hitlPending.value = true
  }
}

function approve() {
  phase.value = 'execute'
  timeline.value[4].status = 'done'
  timeline.value[5].status = 'active'
  hitlPending.value = false
  messages.value.push({ role: 'user', text: '确认执行' })
  setTimeout(() => {
    phase.value = 'done'
    timeline.value[5].status = 'done'
    panel.value = 'audit'
    messages.value.push({ role: 'assistant', text: '预算已调整，写入完成。' })
  }, 1000)
}

function reject() {
  phase.value = 'done'
  timeline.value[4].status = 'done'
  hitlPending.value = false
  messages.value.push({ role: 'user', text: '暂不执行' })
}

function switchPanel(item: any) {
  if (item.path) router.push(item.path)
}

function switchSession(session: any) {
  sessions.value.forEach(s => s.active = s.id === session.id)
}
</script>

<template>
  <div class="flex h-screen w-full overflow-hidden">
    <SidebarNav :nav-items="navItems" :sessions="sessions" active-panel="projects" @switch-panel="switchPanel" @switch-session="switchSession" />

    <!-- 中间 Chat 区 -->
    <main class="flex w-[480px] flex-col border-r border-slate-200 bg-white">
      <header class="flex h-14 items-center border-b border-slate-200 px-5">
        <h2 class="text-sm font-semibold text-slate-900">Chat</h2>
      </header>
      <div class="flex-1 space-y-6 overflow-y-auto p-5">
        <div v-for="(msg, i) in messages" :key="i" :class="msg.role === 'user' ? 'flex justify-end' : ''">
          <div :class="msg.role === 'user' ? 'max-w-[85%] rounded-2xl bg-blue-600 px-4 py-3 text-sm text-white' : 'text-sm leading-6 text-slate-700'">
            {{ msg.text }}
          </div>
        </div>
      </div>
      <div class="border-t border-slate-200 p-4">
        <button v-if="phase === 'idle'" @click="start" class="w-full rounded-xl bg-slate-900 py-3 text-sm font-semibold text-white">启动任务</button>
        <button v-else-if="phase !== 'confirm' && phase !== 'done'" @click="next" class="w-full rounded-xl border border-slate-300 py-3 text-sm font-semibold text-slate-700">推进</button>
      </div>
    </main>

    <!-- 右侧 Workspace -->
    <aside class="flex flex-1 flex-col bg-slate-50">
      <header class="flex h-14 items-center justify-between border-b border-slate-200 bg-white px-6">
        <h2 class="text-sm font-semibold text-slate-900">Workspace</h2>
        <nav class="flex gap-1 text-xs">
          <button v-for="tab in [{ id: 'context', label: '上下文' }, { id: 'analysis', label: '分析' }, { id: 'budget', label: '预算' }, { id: 'audit', label: '审计' }]" :key="tab.id"
            @click="panel = tab.id as WorkspacePanel"
            :class="panel === tab.id ? 'bg-slate-100 font-semibold text-slate-900' : 'text-slate-600 hover:text-slate-900'"
            class="rounded-lg px-3 py-1.5"
          >{{ tab.label }}</button>
        </nav>
      </header>

      <div class="flex flex-1 overflow-hidden">
        <div class="flex-1 overflow-y-auto p-6">
          <div v-if="panel === 'context'">
            <h3 class="text-base font-semibold text-slate-900">{{ project.name }}</h3>
            <div class="mt-4 space-y-3">
              <div v-for="c in project.campaigns" :key="c.id" class="flex items-center justify-between border-b border-slate-200 pb-3">
                <div>
                  <p class="font-medium text-slate-900">{{ c.name }}</p>
                  <p class="text-sm text-slate-500">ROI {{ c.roi }}</p>
                </div>
                <p class="text-lg font-semibold tabular-nums text-slate-900">¥{{ c.budget.toLocaleString() }}</p>
              </div>
            </div>
          </div>

          <div v-else-if="panel === 'analysis'">
            <h3 class="text-base font-semibold text-slate-900">投放分析</h3>
            <table class="mt-4 w-full text-left text-sm">
              <thead class="border-b border-slate-300 text-xs text-slate-600">
                <tr><th class="pb-2">计划</th><th class="pb-2">ROI</th><th class="pb-2">建议</th></tr>
              </thead>
              <tbody class="divide-y divide-slate-200">
                <tr><td class="py-3 font-medium">Meta</td><td class="py-3">1.4</td><td class="py-3 text-amber-600">降预算</td></tr>
                <tr><td class="py-3 font-medium">Google</td><td class="py-3">2.8</td><td class="py-3 text-emerald-600">增预算</td></tr>
              </tbody>
            </table>
          </div>

          <div v-else-if="panel === 'budget'">
            <h3 class="text-base font-semibold text-slate-900">预算方案</h3>
            <div class="mt-4 space-y-3">
              <div class="flex items-center justify-between border-b border-slate-200 pb-3">
                <div><p class="font-medium">Meta</p><p class="text-sm text-slate-500">ROI 1.4</p></div>
                <div class="text-right tabular-nums"><p class="text-sm text-slate-500">¥5,000</p><p class="font-semibold text-amber-600">→ ¥4,500</p></div>
              </div>
              <div class="flex items-center justify-between border-b border-slate-200 pb-3">
                <div><p class="font-medium">Google</p><p class="text-sm text-slate-500">ROI 2.8</p></div>
                <div class="text-right tabular-nums"><p class="text-sm text-slate-500">¥3,000</p><p class="font-semibold text-emerald-600">→ ¥3,500</p></div>
              </div>
            </div>
          </div>

          <div v-else-if="panel === 'audit'">
            <h3 class="text-base font-semibold text-slate-900">执行完成</h3>
            <p class="mt-3 text-sm leading-6 text-slate-600">预算已调整并写入 DB，生成 budget_plan_v1.json 用于幂等保护。</p>
          </div>
        </div>

        <div class="w-64 border-l border-slate-200 bg-white p-4">
          <h4 class="text-xs font-semibold text-slate-600">Timeline</h4>
          <div class="mt-3 space-y-3">
            <div v-for="(t, i) in timeline" :key="i" class="flex gap-2">
              <span class="mt-1 h-2 w-2 flex-none rounded-full" :class="t.status === 'done' ? 'bg-emerald-500' : t.status === 'active' ? 'bg-blue-500' : t.status === 'blocked' ? 'bg-amber-500' : 'bg-slate-300'"></span>
              <p class="text-xs leading-5 text-slate-700">{{ t.label }}</p>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- HITL 弹窗 -->
    <div v-if="hitlPending" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div class="w-96 rounded-2xl bg-white p-6 shadow-2xl">
        <h3 class="text-base font-semibold text-slate-900">确认预算调整</h3>
        <p class="mt-2 text-sm text-slate-600">Meta ¥5,000 → ¥4,500；Google ¥3,000 → ¥3,500</p>
        <div class="mt-5 flex gap-3">
          <button @click="approve" class="flex-1 rounded-xl bg-slate-900 py-2.5 text-sm font-semibold text-white">确认</button>
          <button @click="reject" class="flex-1 rounded-xl border border-slate-300 py-2.5 text-sm font-semibold text-slate-700">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>
