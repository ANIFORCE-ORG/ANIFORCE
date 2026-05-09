<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { GeoDiagnosisClient } from './client'
import type { GeoAuditReport } from './types'

const props = defineProps<{
  projectId: string
}>()

const client = new GeoDiagnosisClient()
const audits = ref<GeoAuditReport[]>([])
const loading = ref(false)
const error = ref('')
const latestAudit = computed(() => audits.value[0] || null)

const scoreState = (score?: number) => {
  if (!score) return '未诊断'
  if (score >= 72) return '良好'
  if (score >= 50) return '待优化'
  return '高风险'
}

const loadAudits = async () => {
  loading.value = true
  error.value = ''
  try {
    audits.value = await client.listAudits(props.projectId)
  } catch (err: any) {
    error.value = err?.message || '加载 GEO 诊断失败'
  } finally {
    loading.value = false
  }
}

onMounted(loadAudits)
</script>

<template>
  <section class="rounded-md border border-emerald-200 bg-emerald-50 p-5">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h3 class="text-sm font-semibold text-slate-900">GEO / Agent Readiness</h3>
        <p class="mt-1 text-sm text-slate-500">项目级 GEO 诊断摘要和历史。</p>
      </div>
      <button class="rounded-md bg-emerald-500 px-4 py-2 text-sm font-semibold text-white">
        开始诊断
      </button>
    </div>

    <p v-if="error" class="mt-4 text-sm text-red-600">{{ error }}</p>
    <p v-else-if="loading" class="mt-4 text-sm text-slate-500">加载中...</p>

    <div v-else-if="latestAudit" class="mt-4 grid grid-cols-4 gap-3">
      <div class="rounded-md border border-emerald-100 bg-white p-3">
        <div class="text-xs text-slate-500">GEO Readiness</div>
        <div class="text-xl font-bold text-slate-900">{{ latestAudit.scores.geo_readiness }}</div>
      </div>
      <div class="rounded-md border border-emerald-100 bg-white p-3">
        <div class="text-xs text-slate-500">状态</div>
        <div class="text-xl font-bold text-slate-900">{{ scoreState(latestAudit.scores.geo_readiness) }}</div>
      </div>
      <div class="rounded-md border border-emerald-100 bg-white p-3">
        <div class="text-xs text-slate-500">AI Mention</div>
        <div class="text-xl font-bold text-slate-900">{{ latestAudit.scores.mention_rate }}%</div>
      </div>
      <div class="rounded-md border border-emerald-100 bg-white p-3">
        <div class="text-xs text-slate-500">主要竞品</div>
        <div class="truncate text-sm font-semibold text-slate-900">{{ latestAudit.competitor_leader }}</div>
      </div>
    </div>

    <div v-else class="mt-4 rounded-md border border-dashed border-emerald-200 bg-white p-3 text-sm text-slate-500">
      当前项目还没有 GEO 诊断报告。
    </div>
  </section>
</template>
