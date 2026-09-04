<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { formatTrendMetricValue, type TrendMetric } from '@/data/trendMetrics'

export type AnalysisTableRow = {
  id: string
  name: string
  detail: string
  metrics: Partial<Record<TrendMetric, number | null>>
  delta: number | null
  status: string
  statusTone: 'normal' | 'warning' | 'danger'
}

const props = withDefaults(defineProps<{
  title: string
  subtitle: string
  entityLabel: string
  searchPlaceholder: string
  rows: AnalysisTableRow[]
  columns?: TrendMetric[]
  pageSize?: number
  currency?: string | null
  mixedCurrency?: boolean
  totals?: Partial<Record<TrendMetric, number | null>>
}>(), {
  columns: () => ['spend', 'conversion_value', 'conversions', 'roas', 'clicks', 'ctr'],
  pageSize: 10,
  currency: 'USD',
  mixedCurrency: false,
})

const query = ref('')
const attentionOnly = ref(false)
const currentPage = ref(1)
const filteredRows = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return props.rows.filter(row => {
    const matchesKeyword = !keyword || `${row.name} ${row.id} ${row.detail}`.toLowerCase().includes(keyword)
    return matchesKeyword && (!attentionOnly.value || row.statusTone !== 'normal')
  })
})
const pageCount = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / props.pageSize)))
const pagedRows = computed(() => filteredRows.value.slice((currentPage.value - 1) * props.pageSize, currentPage.value * props.pageSize))
const totals = computed(() => props.totals ?? props.columns.reduce((result, metric) => {
  const values = filteredRows.value.map(row => row.metrics[metric]).filter((value): value is number => value != null)
  result[metric] = values.length ? values.reduce((sum, value) => sum + value, 0) : null
  return result
}, {} as Partial<Record<TrendMetric, number | null>>))

watch([query, attentionOnly, () => props.rows.length], () => { currentPage.value = 1 })
watch(pageCount, count => { if (currentPage.value > count) currentPage.value = count })
const labelFor = (metric: TrendMetric) => ({
  spend: '花费', conversion_value: '转化价值', conversions: '转化', roas: 'ROAS',
  clicks: '点击', ctr: 'CTR', impressions: '曝光', result_cost: '结果成本',
}[metric] ?? metric)
</script>

<template>
  <section class="analysis-table-card" :aria-label="props.title">
    <header class="analysis-table-titlebar">
      <div><h2>{{ props.title }}</h2><p>{{ props.subtitle }}</p></div>
      <div class="analysis-table-header-actions">
        <label class="analysis-table-search"><span class="material-symbols-outlined" aria-hidden="true">search</span><input v-model="query" type="search" :placeholder="props.searchPlaceholder" :aria-label="props.searchPlaceholder"></label>
        <span class="analysis-table-count">{{ props.entityLabel }} · {{ filteredRows.length }}</span>
        <button type="button" class="analysis-attention-button" :class="{ active: attentionOnly }" :aria-pressed="attentionOnly" @click="attentionOnly = !attentionOnly">{{ attentionOnly ? '查看全部' : '只看需要处理' }}</button>
      </div>
    </header>
    <div class="analysis-table-scroll">
      <table class="analysis-table">
        <thead><tr><th>{{ props.entityLabel }}</th><th v-for="metric in props.columns" :key="metric">{{ labelFor(metric) }}</th><th>环比</th><th>状态</th></tr></thead>
        <tbody>
          <tr v-for="row in pagedRows" :key="row.id">
            <td><strong>{{ row.name }}</strong><small>{{ row.detail }}</small></td>
            <td v-for="metric in props.columns" :key="metric">{{ formatTrendMetricValue(metric, row.metrics[metric], props.currency, props.mixedCurrency) }}</td>
            <td :class="row.delta != null && row.delta < 0 ? 'down' : 'up'">{{ row.delta == null ? '—' : `${row.delta >= 0 ? '▲' : '▼'} ${Math.abs(row.delta).toFixed(1)}%` }}</td>
            <td><span class="analysis-status" :class="row.statusTone">{{ row.status || '正常' }}</span></td>
          </tr>
          <tr v-if="!pagedRows.length"><td :colspan="props.columns.length + 3" class="analysis-table-empty">没有匹配的数据</td></tr>
        </tbody>
        <tfoot v-if="filteredRows.length"><tr><th>合计</th><th v-for="metric in props.columns" :key="metric">{{ formatTrendMetricValue(metric, totals[metric], props.currency, props.mixedCurrency) }}</th><th>—</th><th></th></tr></tfoot>
      </table>
    </div>
    <footer class="analysis-table-pagination"><span>共 {{ filteredRows.length }} 条 · 每页 {{ props.pageSize }} 条</span><div class="analysis-table-pagination__controls"><button type="button" :disabled="currentPage === 1" aria-label="上一页" @click="currentPage--"><span class="material-symbols-outlined" aria-hidden="true">chevron_left</span></button><strong>第 {{ currentPage }} / {{ pageCount }} 页</strong><button type="button" :disabled="currentPage === pageCount" aria-label="下一页" @click="currentPage++"><span class="material-symbols-outlined" aria-hidden="true">chevron_right</span></button></div></footer>
  </section>
</template>

<style scoped>
.analysis-table-card { margin-top: 20px; overflow: hidden; border: 1px solid #e5e3df; border-radius: 10px; background: #fff; color: #37352f; }
.analysis-table-titlebar { min-height: 62px; display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 12px 18px; border-bottom: 1px solid #ede9e4; }
.analysis-table-titlebar h2 { margin: 0; color: #202020; font-size: 16px; font-weight: 650; }.analysis-table-titlebar p { margin: 5px 0 0; color: #787774; font-size: 12px; }
.analysis-table-header-actions { display: flex; align-items: center; gap: 8px; }.analysis-table-search { width: 220px; display: flex; align-items: center; gap: 6px; padding: 8px 10px; border: 1px solid #d8d5d0; border-radius: 8px; color: #9b9a97; }.analysis-table-search input { width: 100%; border: 0; outline: 0; font: inherit; font-size: 12px; }.analysis-table-search .material-symbols-outlined { font-size: 17px; }.analysis-table-count { padding: 8px 10px; border-radius: 7px; background: #f6f5f4; font-size: 12px; white-space: nowrap; }.analysis-attention-button { padding: 7px 10px; border: 1px solid #d8d5d0; border-radius: 7px; background: #fff; color: #56534f; font: inherit; font-size: 11px; cursor: pointer; white-space: nowrap; }.analysis-attention-button.active { background: #f3eee6; border-color: #cbb796; }.analysis-table { width: 100%; border-collapse: collapse; table-layout: auto; font-size: 12px; }.analysis-table th,.analysis-table td { padding: 11px 12px; border-bottom: 1px solid #ede9e4; text-align: right; white-space: nowrap; }.analysis-table th:first-child,.analysis-table td:first-child { width: 28%; text-align: left; }.analysis-table thead { background: #fafaf9; color: #787774; font-size: 11px; }.analysis-table td:first-child strong,.analysis-table td:first-child small { display: block; overflow: hidden; text-overflow: ellipsis; }.analysis-table td:first-child small { margin-top: 3px; color: #9b9a97; font-size: 10px; }.analysis-table td.up { color: #12804a; }.analysis-table td.down { color: #c73c36; }.analysis-status { color: #12804a; }.analysis-status.warning { color: #a86400; }.analysis-status.danger { color: #c73c36; }.analysis-table-empty { height: 130px; text-align: center !important; color: #787774; }.analysis-table tfoot th { background: #fafaf9; font-weight: 650; }.analysis-table-pagination { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px; color: #787774; font-size: 11px; }.analysis-table-pagination__controls { display: flex; align-items: center; gap: 18px; }.analysis-table-pagination__controls strong { min-width: 70px; color: #56534f; font-size: 13px; font-weight: 650; text-align: center; }.analysis-table-pagination__controls button { width: 30px; height: 30px; display: grid; place-items: center; padding: 0; border: 1px solid #c8c4be; border-radius: 7px; background: #fff; color: #56534f; cursor: pointer; }.analysis-table-pagination__controls button:hover:not(:disabled) { border-color: #a9cef8; background: #f7fbff; color: #137fec; }.analysis-table-pagination__controls button:disabled { border-color: #e5e3df; color: #a4a097; cursor: not-allowed; opacity: .55; }.analysis-table-pagination__controls .material-symbols-outlined { font-size: 18px; }
@media (max-width: 860px) { .analysis-table-titlebar,.analysis-table-pagination { align-items: stretch; flex-direction: column; }.analysis-table-header-actions { flex-wrap: wrap; }.analysis-table-search { flex: 1 1 200px; width: auto; }.analysis-table-scroll { overflow-x: auto; }.analysis-table-pagination__controls { justify-content: space-between; } }
</style>
