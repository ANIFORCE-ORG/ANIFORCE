<script setup lang="ts">
export type TaskPanelStatus = 'created' | 'running' | 'waiting_user_input' | 'waiting_approval' | 'applying' | 'completed' | 'failed' | 'canceled'

export interface TaskPanelStep {
  key: string
  label: string
  status: 'done' | 'active' | 'pending' | 'error'
}

export interface TaskPanelAction {
  key: string
  label: string
  icon: string
  tone?: 'primary' | 'neutral' | 'danger'
}

export interface TaskPanelArtifact {
  type?: string
  title?: string
  label?: string
  [key: string]: unknown
}

const props = defineProps<{
  visible: boolean
  title: string
  status: TaskPanelStatus
  summary: string
  tags: string[]
  steps: TaskPanelStep[]
  actions: TaskPanelAction[]
  taskTypeLabel?: string
  phaseLabel?: string
  artifacts?: TaskPanelArtifact[]
  showStandardExamples?: boolean
}>()

const emit = defineEmits<{
  action: [key: string]
}>()

const statusMeta: Record<TaskPanelStatus, { label: string; icon: string; badge: string; tint: string }> = {
  created: {
    label: '已创建',
    icon: 'radio_button_unchecked',
    badge: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    tint: 'bg-slate-50 dark:bg-slate-900/60'
  },
  running: {
    label: '进行中',
    icon: 'progress_activity',
    badge: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300',
    tint: 'bg-blue-50/60 dark:bg-blue-950/20'
  },
  waiting_user_input: {
    label: '等待补充',
    icon: 'edit_note',
    badge: 'bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300',
    tint: 'bg-purple-50/60 dark:bg-purple-950/20'
  },
  waiting_approval: {
    label: '等待确认',
    icon: 'approval_delegation',
    badge: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
    tint: 'bg-amber-50/70 dark:bg-amber-950/20'
  },
  applying: {
    label: '执行中',
    icon: 'bolt',
    badge: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    tint: 'bg-emerald-50/60 dark:bg-emerald-950/20'
  },
  completed: {
    label: '已完成',
    icon: 'check_circle',
    badge: 'bg-green-50 text-green-700 dark:bg-green-950/40 dark:text-green-300',
    tint: 'bg-green-50/60 dark:bg-green-950/20'
  },
  failed: {
    label: '失败',
    icon: 'error',
    badge: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300',
    tint: 'bg-red-50/60 dark:bg-red-950/20'
  },
  canceled: {
    label: '已取消',
    icon: 'do_not_disturb_on',
    badge: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400',
    tint: 'bg-slate-50 dark:bg-slate-900/60'
  }
}

const standardTasks = [
  {
    type: 'campaign_operations',
    icon: 'campaign',
    title: '投放计划创建 / 增删改',
    status: 'waiting_approval' as TaskPanelStatus,
    summary: '已生成 Meta 测试计划草稿，等待确认预算、素材组合和投放地区。',
    accent: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300',
    fields: [
      { label: '平台', value: 'Meta Ads' },
      { label: '操作', value: '创建 / 调整 / 暂停' },
      { label: '预算', value: '$500 / day' },
      { label: '地区', value: 'US · CA · AU' }
    ],
    steps: [
      { key: 'scope', label: '收集投放目标', status: 'done' },
      { key: 'draft', label: '生成计划草稿', status: 'done' },
      { key: 'approval', label: '等待业务确认', status: 'active' },
      { key: 'apply', label: '应用到广告平台', status: 'pending' }
    ] as TaskPanelStep[],
    actions: [
      { key: 'approve_campaign', label: '批准创建计划', icon: 'check', tone: 'primary' },
      { key: 'revise_campaign', label: '调整预算 / 素材', icon: 'tune', tone: 'neutral' },
      { key: 'cancel_campaign', label: '取消任务', icon: 'close', tone: 'danger' }
    ] as TaskPanelAction[],
    artifacts: ['测试计划草稿', '素材组合建议', '预算分配方案']
  },
  {
    type: 'creative_generation',
    icon: 'auto_awesome',
    title: '素材生成与入库',
    status: 'running' as TaskPanelStatus,
    summary: '正在根据游戏卖点生成广告脚本与首批图片素材，完成后进入审核。',
    accent: 'bg-purple-50 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300',
    fields: [
      { label: '品类', value: '策略游戏' },
      { label: '角度', value: '高爆发成长' },
      { label: '规格', value: '1:1 · 9:16' },
      { label: '数量', value: '6 variants' }
    ],
    steps: [
      { key: 'brief', label: '整理创意简报', status: 'done' },
      { key: 'script', label: '生成广告脚本', status: 'active' },
      { key: 'asset', label: '生成图片 / 视频', status: 'pending' },
      { key: 'review', label: '审核并保存入库', status: 'pending' }
    ] as TaskPanelStep[],
    actions: [
      { key: 'edit_brief', label: '补充卖点', icon: 'edit_note', tone: 'neutral' },
      { key: 'open_material', label: '进入素材库', icon: 'image', tone: 'primary' }
    ] as TaskPanelAction[],
    artifacts: ['广告脚本', '图片素材草稿', '素材标签建议']
  }
]
</script>

<template>
  <aside class="hidden xl:flex w-[336px] shrink-0 border-l border-slate-200 bg-slate-50/80 dark:border-slate-800 dark:bg-slate-950/80">
    <div class="flex h-full w-full flex-col overflow-y-auto px-4 py-5">
      <div class="mb-4 flex items-center justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">Task</p>
          <h2 class="mt-1 text-sm font-semibold text-slate-900 dark:text-white">任务工作区</h2>
        </div>
        <span class="material-symbols-outlined text-lg text-slate-400">view_sidebar</span>
      </div>

      <div v-if="visible" class="space-y-4">
        <section class="rounded-xl border border-slate-200 bg-white p-4 shadow-sm shadow-slate-200/50 dark:border-slate-800 dark:bg-slate-900 dark:shadow-none">
          <div class="rounded-lg p-3" :class="statusMeta[status].tint">
            <div class="flex items-start justify-between gap-3">
              <span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold" :class="statusMeta[status].badge">
                <span class="material-symbols-outlined text-sm" :class="{ 'animate-spin': status === 'running' || status === 'applying' }">
                  {{ statusMeta[status].icon }}
                </span>
                {{ statusMeta[status].label }}
              </span>
            </div>
            <h3 class="mt-3 text-base font-semibold leading-snug text-slate-950 dark:text-white">{{ title }}</h3>
            <p class="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{{ summary }}</p>
          </div>

          <div v-if="tags.length" class="mt-3 flex flex-wrap gap-2">
            <span
              v-for="tag in tags"
              :key="tag"
              class="rounded-md bg-slate-100 px-2 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300"
            >
              {{ tag }}
            </span>
          </div>
        </section>

        <section v-if="props.artifacts?.length || props.taskTypeLabel || props.phaseLabel" class="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div class="mb-3">
            <h3 class="text-sm font-semibold text-slate-900 dark:text-white">当前业务任务</h3>
            <p v-if="props.taskTypeLabel || props.phaseLabel" class="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">
              {{ [props.taskTypeLabel, props.phaseLabel].filter(Boolean).join(' · ') }}
            </p>
          </div>

          <div v-if="props.artifacts?.length" class="flex flex-wrap gap-1.5">
            <span
              v-for="artifact in props.artifacts"
              :key="`${artifact.type || 'artifact'}-${artifact.title || artifact.label || JSON.stringify(artifact)}`"
              class="rounded-md bg-slate-50 px-2 py-1 text-[11px] font-medium text-slate-600 dark:bg-slate-950 dark:text-slate-300"
            >
              {{ artifact.title || artifact.label || artifact.type || '任务产物' }}
            </span>
          </div>
        </section>

        <section v-if="props.showStandardExamples !== false" class="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div class="mb-3">
            <h3 class="text-sm font-semibold text-slate-900 dark:text-white">标准任务卡</h3>
            <p class="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">后续由 task_type 驱动，绑定真实业务对象和动作。</p>
          </div>

          <div class="space-y-3">
            <article
              v-for="task in standardTasks"
              :key="task.type"
              class="rounded-xl border border-slate-200 bg-slate-50/60 p-3 dark:border-slate-800 dark:bg-slate-950/35"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="flex min-w-0 gap-2.5">
                  <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg" :class="task.accent">
                    <span class="material-symbols-outlined text-lg">{{ task.icon }}</span>
                  </div>
                  <div class="min-w-0">
                    <h4 class="truncate text-sm font-semibold text-slate-950 dark:text-white">{{ task.title }}</h4>
                    <p class="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{{ task.summary }}</p>
                  </div>
                </div>
                <span class="shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="statusMeta[task.status].badge">
                  {{ statusMeta[task.status].label }}
                </span>
              </div>

              <dl class="mt-3 grid grid-cols-2 gap-2">
                <div
                  v-for="field in task.fields"
                  :key="field.label"
                  class="rounded-lg bg-white px-2.5 py-2 dark:bg-slate-900"
                >
                  <dt class="text-[11px] text-slate-400">{{ field.label }}</dt>
                  <dd class="mt-0.5 truncate text-xs font-medium text-slate-700 dark:text-slate-200">{{ field.value }}</dd>
                </div>
              </dl>

              <div class="mt-3 space-y-2">
                <div v-for="step in task.steps" :key="step.key" class="flex items-center gap-2 text-xs">
                  <span
                    class="h-2 w-2 rounded-full"
                    :class="{
                      'bg-primary': step.status === 'done' || step.status === 'active',
                      'bg-red-400': step.status === 'error',
                      'bg-slate-300 dark:bg-slate-700': step.status === 'pending'
                    }"
                  ></span>
                  <span :class="step.status === 'active' ? 'font-semibold text-slate-900 dark:text-white' : 'text-slate-500 dark:text-slate-400'">{{ step.label }}</span>
                </div>
              </div>

              <div class="mt-3 flex flex-wrap gap-1.5">
                <span
                  v-for="artifact in task.artifacts"
                  :key="artifact"
                  class="rounded-md bg-white px-2 py-1 text-[11px] font-medium text-slate-500 dark:bg-slate-900 dark:text-slate-400"
                >
                  {{ artifact }}
                </span>
              </div>

              <div class="mt-3 grid gap-2">
                <button
                  v-for="action in task.actions"
                  :key="action.key"
                  class="flex h-8 items-center justify-center gap-1.5 rounded-md border px-2 text-xs font-medium transition-colors"
                  :class="{
                    'border-primary bg-primary text-white hover:bg-primary/90': action.tone === 'primary',
                    'border-red-200 bg-red-50 text-red-600 hover:bg-red-100 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300': action.tone === 'danger',
                    'border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800': !action.tone || action.tone === 'neutral'
                  }"
                  @click="emit('action', action.key)"
                >
                  <span class="material-symbols-outlined text-sm">{{ action.icon }}</span>
                  {{ action.label }}
                </button>
              </div>
            </article>
          </div>
        </section>

        <section class="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <div class="mb-3 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-slate-900 dark:text-white">推进阶段</h3>
            <span class="text-xs text-slate-400">自动更新</span>
          </div>
          <ol class="space-y-3">
            <li v-for="step in steps" :key="step.key" class="flex gap-3">
              <span
                class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[11px]"
                :class="{
                  'border-primary bg-primary text-white': step.status === 'done',
                  'border-primary bg-white text-primary dark:bg-slate-900': step.status === 'active',
                  'border-red-300 bg-red-50 text-red-600 dark:border-red-900 dark:bg-red-950/30 dark:text-red-300': step.status === 'error',
                  'border-slate-200 bg-slate-50 text-slate-300 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-500': step.status === 'pending'
                }"
              >
                <span v-if="step.status === 'done'" class="material-symbols-outlined text-sm">check</span>
                <span v-else-if="step.status === 'error'" class="material-symbols-outlined text-sm">close</span>
                <span v-else class="h-1.5 w-1.5 rounded-full bg-current"></span>
              </span>
              <div class="min-w-0 flex-1 border-b border-slate-100 pb-3 last:border-b-0 dark:border-slate-800">
                <p
                  class="text-sm"
                  :class="step.status === 'active' ? 'font-semibold text-slate-950 dark:text-white' : 'text-slate-500 dark:text-slate-400'"
                >
                  {{ step.label }}
                </p>
              </div>
            </li>
          </ol>
        </section>

        <section class="rounded-xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
          <h3 class="mb-3 text-sm font-semibold text-slate-900 dark:text-white">下一步</h3>
          <div class="space-y-2">
            <button
              v-for="action in actions"
              :key="action.key"
              class="flex h-9 w-full items-center justify-center gap-2 rounded-md border px-3 text-sm font-medium transition-colors"
              :class="{
                'border-primary bg-primary text-white hover:bg-primary/90': action.tone === 'primary',
                'border-red-200 bg-red-50 text-red-600 hover:bg-red-100 dark:border-red-900/50 dark:bg-red-950/30 dark:text-red-300': action.tone === 'danger',
                'border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800': !action.tone || action.tone === 'neutral'
              }"
              @click="emit('action', action.key)"
            >
              <span class="material-symbols-outlined text-base">{{ action.icon }}</span>
              {{ action.label }}
            </button>
          </div>
        </section>
      </div>

      <div v-else class="rounded-xl border border-dashed border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-100 text-yellow-700 dark:bg-yellow-950/40 dark:text-yellow-300">
          <span class="material-symbols-outlined">sticky_note_2</span>
        </div>
        <h3 class="mt-4 text-sm font-semibold text-slate-900 dark:text-white">任务会出现在这里</h3>
        <p class="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
          发送一个投放目标后，右侧会展示任务状态、推进阶段和需要你确认的动作。
        </p>
      </div>
    </div>
  </aside>
</template>
