<script setup lang="ts">
import { computed, ref, watch } from 'vue'

type AnalysisTableRow = {
  id: string
  name: string
  detail: string
  spend: number
  revenue: number
  orders: number
  roas: number
  delta: number
  clicks: number
  ctr: number
  status: string
  statusTone: 'normal' | 'warning' | 'danger'
}

const props = withDefaults(defineProps<{
  title: string
  subtitle: string
  entityLabel: string
  searchPlaceholder: string
  rows: AnalysisTableRow[]
  pageSize?: number
  dateFilter?: boolean
  dateStart?: string
  dateEnd?: string
  maxDate?: string
}>(), {
  pageSize: 10,
  dateFilter: false,
  dateStart: '',
  dateEnd: '',
  maxDate: '',
})

const emit = defineEmits<{
  'update:dateStart': [value: string]
  'update:dateEnd': [value: string]
}>()

const query = ref('')
const attentionOnly = ref(false)
const currentPage = ref(1)
const moduleStartInput = ref<HTMLInputElement | null>(null)
const moduleEndInput = ref<HTMLInputElement | null>(null)
const openModuleDatePicker = (boundary: 'start' | 'end') => {
  const input = boundary === 'start' ? moduleStartInput.value : moduleEndInput.value
  if (!input) return
  input.focus()
  if (typeof input.showPicker === 'function') input.showPicker()
}
const updateModuleDate = (boundary: 'start' | 'end', event: Event) => {
  emit(boundary === 'start' ? 'update:dateStart' : 'update:dateEnd', (event.target as HTMLInputElement).value)
}

const formatMoney = (value: number) => `US$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const formatNumber = (value: number) => Math.round(value).toLocaleString('zh-CN')
const filteredRows = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  return props.rows.filter((row) => {
    const matchesKeyword = !keyword || `${row.name} ${row.id} ${row.detail}`.toLowerCase().includes(keyword)
    const matchesAttention = !attentionOnly.value || row.statusTone !== 'normal'
    return matchesKeyword && matchesAttention
  })
})
const pageCount = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / props.pageSize)))
const pagedRows = computed(() => {
  const start = (currentPage.value - 1) * props.pageSize
  return filteredRows.value.slice(start, start + props.pageSize)
})
const totals = computed(() => filteredRows.value.reduce((result, row) => ({
  spend: result.spend + row.spend,
  revenue: result.revenue + row.revenue,
  orders: result.orders + row.orders,
  clicks: result.clicks + row.clicks,
}), { spend: 0, revenue: 0, orders: 0, clicks: 0 }))
const totalRoas = computed(() => totals.value.spend ? totals.value.revenue / totals.value.spend : 0)
const totalCtr = computed(() => {
  const estimatedImpressions = filteredRows.value.reduce((total, row) => total + (row.ctr ? row.clicks / (row.ctr / 100) : 0), 0)
  return estimatedImpressions ? totals.value.clicks / estimatedImpressions * 100 : 0
})

watch([query, attentionOnly, () => props.rows.length], () => { currentPage.value = 1 })
watch(pageCount, (count) => {
  if (currentPage.value > count) currentPage.value = count
})
</script>

<template>
  <section class="analysis-table-card" :aria-label="props.title">
    <header class="analysis-table-titlebar">
      <div>
        <h2>{{ props.title }}</h2>
        <p>{{ props.subtitle }}</p>
      </div>
      <div class="analysis-table-header-actions">
        <div v-if="props.dateFilter" class="module-date-filter" role="group" aria-label="模块时间筛选">
          <span class="material-symbols-outlined" aria-hidden="true">calendar_today</span>
          <div class="module-date-hotspot" role="button" tabindex="0" aria-label="修改模块开始日期" @click="openModuleDatePicker('start')" @keydown.enter.prevent="openModuleDatePicker('start')" @keydown.space.prevent="openModuleDatePicker('start')">
            <input ref="moduleStartInput" tabindex="-1" type="date" :value="props.dateStart" :max="props.dateEnd" aria-label="模块开始日期" @change="updateModuleDate('start', $event)">
          </div>
          <span>至</span>
          <div class="module-date-hotspot" role="button" tabindex="0" aria-label="修改模块结束日期" @click="openModuleDatePicker('end')" @keydown.enter.prevent="openModuleDatePicker('end')" @keydown.space.prevent="openModuleDatePicker('end')">
            <input ref="moduleEndInput" tabindex="-1" type="date" :value="props.dateEnd" :min="props.dateStart" :max="props.maxDate" aria-label="模块结束日期" @change="updateModuleDate('end', $event)">
          </div>
        </div>
        <div v-else class="analysis-table-tools">
          <label class="analysis-table-search">
            <span class="material-symbols-outlined" aria-hidden="true">search</span>
            <input v-model="query" type="search" :placeholder="props.searchPlaceholder" :aria-label="props.searchPlaceholder">
          </label>
          <span class="analysis-table-count">{{ props.entityLabel }} · {{ filteredRows.length }}</span>
        </div>
        <div class="analysis-attention-control">
          <button type="button" :class="{ active: attentionOnly }" :aria-pressed="attentionOnly" @click="attentionOnly = !attentionOnly">{{ attentionOnly ? '查看全部' : '只看需要处理' }}</button>
        </div>
      </div>
    </header>

    <div class="analysis-table-scroll">
      <div class="analysis-table-head" role="row">
        <span>{{ props.entityLabel }}</span><span>花费</span><span>收入</span><span>订单</span><span>ROAS</span><span>环比</span><span>点击</span><span>CTR</span><span>状态</span>
      </div>
      <div class="analysis-table-body">
        <div v-for="row in pagedRows" :key="row.id" class="analysis-table-row" role="row">
          <div class="analysis-entity"><strong>{{ row.name }}</strong><small>{{ row.detail }}</small></div>
          <span data-label="花费">{{ formatMoney(row.spend) }}</span>
          <span data-label="收入">{{ formatMoney(row.revenue) }}</span>
          <span data-label="订单">{{ formatNumber(row.orders) }}</span>
          <span data-label="ROAS">{{ row.roas.toFixed(2) }}x</span>
          <span data-label="环比" class="analysis-delta" :class="row.delta >= 0 ? 'up' : 'down'">{{ row.delta >= 0 ? '▲' : '▼' }} {{ Math.abs(row.delta).toFixed(1) }}%</span>
          <span data-label="点击">{{ formatNumber(row.clicks) }}</span>
          <span data-label="CTR">{{ row.ctr.toFixed(2) }}%</span>
          <span data-label="状态" class="analysis-status" :class="row.statusTone"><i></i>{{ row.status }}</span>
        </div>
        <div v-if="!pagedRows.length" class="analysis-table-empty">没有匹配的数据</div>
      </div>
      <div v-if="filteredRows.length" class="analysis-table-total" role="row">
        <strong>合计</strong><b data-label="花费">{{ formatMoney(totals.spend) }}</b><b data-label="收入">{{ formatMoney(totals.revenue) }}</b><b data-label="订单">{{ formatNumber(totals.orders) }}</b><b data-label="ROAS">{{ totalRoas.toFixed(2) }}x</b><span data-label="环比">—</span><b data-label="点击">{{ formatNumber(totals.clicks) }}</b><b data-label="CTR">{{ totalCtr.toFixed(2) }}%</b><span></span>
      </div>
    </div>

    <footer class="analysis-table-pagination">
      <span>共 {{ filteredRows.length }} 条 · 每页 {{ props.pageSize }} 条</span>
      <div>
        <button type="button" :disabled="currentPage === 1" @click="currentPage--">上一页</button>
        <span>第 {{ currentPage }} / {{ pageCount }} 页</span>
        <button type="button" :disabled="currentPage === pageCount" @click="currentPage++">下一页</button>
      </div>
    </footer>
  </section>
</template>

<style scoped>
.analysis-table-card { margin-top: 16px; overflow: hidden; border: 1px solid #e5e3df; border-radius: 12px; background: #fff; color: #37352f; }
.analysis-table-titlebar { min-height: 72px; display: flex; align-items: center; justify-content: space-between; gap: 18px; padding: 12px 16px; border-bottom: 1px solid #ede9e4; }
.analysis-table-titlebar h2 { margin: 0; color: #202020; font-size: 16px; line-height: 1.3; font-weight: 650; }
.analysis-table-titlebar p { margin: 5px 0 0; color: #787774; font-size: 12px; }
.analysis-table-header-actions { min-width: 0; display: flex; align-items: center; justify-content: flex-end; gap: 9px; }
.analysis-table-tools { display: flex; align-items: center; gap: 9px; }
.module-date-filter { min-width: 330px; height: 38px; display: flex; align-items: center; gap: 7px; padding: 0 10px; border: 1px solid #d8d5d0; border-radius: 8px; background: #fff; color: #787774; font-size: 11px; }
.module-date-filter > .material-symbols-outlined { flex: 0 0 auto; font-size: 16px; }
.module-date-hotspot { min-width: 0; flex: 1 1 0; display: flex; align-items: center; border-radius: 5px; cursor: pointer; }
.module-date-hotspot:focus-visible { outline: 2px solid rgb(50 118 204 / 24%); outline-offset: 1px; }
.module-date-hotspot input { width: 100%; min-width: 0; height: 26px; padding: 0 1px; border: 0; outline: 0; background: transparent; color: #37352f; color-scheme: light; font: inherit; font-size: 11px; font-weight: 600; pointer-events: none; cursor: pointer; }
.module-date-hotspot input::-webkit-calendar-picker-indicator { width: 13px; height: 13px; margin-left: 1px; padding: 0; opacity: .6; }
.analysis-table-search { width: 230px; height: 38px; display: flex; align-items: center; gap: 7px; padding: 0 11px; border: 1px solid #d8d5d0; border-radius: 8px; background: #fff; color: #9b9a97; }
.analysis-table-search:focus-within { border-color: #9fc9fb; box-shadow: 0 0 0 2px rgb(50 118 204 / 10%); }
.analysis-table-search .material-symbols-outlined { font-size: 18px; }
.analysis-table-search input { width: 100%; min-width: 0; border: 0; outline: 0; background: transparent; color: #37352f; font: inherit; font-size: 12px; }
.analysis-table-count { min-height: 34px; display: inline-flex; align-items: center; padding: 0 11px; border-radius: 7px; background: #f6f5f4; color: #56534f; font-size: 12px; font-weight: 600; white-space: nowrap; }
.analysis-attention-control { display: inline-flex; align-items: center; white-space: nowrap; }
.analysis-attention-control button { height: 38px; padding: 0 15px; border: 1px solid #d8c7ad; border-radius: 8px; background: #f3eee6; color: #76552a; box-shadow: 0 1px 2px rgb(55 53 47 / 6%); font: inherit; font-size: 11px; font-weight: 650; white-space: nowrap; cursor: pointer; transition: background-color .16s ease,border-color .16s ease,color .16s ease; }
.analysis-attention-control button:hover { border-color: #cbb796; background: #ece4d8; color: #65461f; }
.analysis-attention-control button.active { border-color: #bba681; background: #e4d9c8; color: #563b1c; }
.analysis-attention-control button:focus-visible { outline: 2px solid rgb(118 85 42 / 18%); outline-offset: 2px; }
.analysis-table-scroll { width: 100%; overflow: hidden; }
.analysis-table-head,.analysis-table-row,.analysis-table-total { width: 100%; min-width: 0; display: grid; grid-template-columns: minmax(150px,1.55fr) minmax(76px,.78fr) minmax(82px,.84fr) minmax(48px,.48fr) minmax(52px,.52fr) minmax(58px,.58fr) minmax(54px,.54fr) minmax(48px,.48fr) minmax(68px,.7fr); align-items: center; gap: clamp(4px,.65vw,10px); padding: 0 clamp(9px,1.05vw,16px); }
.analysis-table-head { min-height: 44px; border-bottom: 1px solid #e5e3df; background: #fafaf9; color: #787774; font-size: clamp(9px,.72vw,11px); font-weight: 600; }
.analysis-table-head span:not(:first-child),.analysis-table-row > span:not(:last-child),.analysis-table-total > :not(:first-child) { text-align: right; }
.analysis-table-row { min-height: 62px; border-bottom: 1px solid #ede9e4; color: #37352f; font-size: clamp(10px,.78vw,12px); font-variant-numeric: tabular-nums; }
.analysis-table-row:hover { background: #fafcff; }
.analysis-entity { min-width: 0; }
.analysis-entity strong,.analysis-entity small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.analysis-entity strong { color: #202020; font-size: clamp(11px,.85vw,13px); font-weight: 650; }
.analysis-entity small { margin-top: 4px; color: #9b9a97; font-size: clamp(9px,.72vw,11px); }
.analysis-delta { font-weight: 600; }.analysis-delta.up { color: #12804a; }.analysis-delta.down { color: #c73c36; }
.analysis-status { width: fit-content; max-width: 100%; justify-self: end; display: inline-flex; align-items: center; gap: 4px; padding: 4px clamp(5px,.5vw,8px); border-radius: 999px; background: #e8f7ee; color: #12804a; font-size: clamp(9px,.7vw,11px); font-weight: 600; white-space: nowrap; }
.analysis-status i { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
.analysis-status.warning { background: #fff4df; color: #a86400; }.analysis-status.danger { background: #fdecec; color: #c73c36; }
.analysis-table-empty { min-width: 0; min-height: 150px; display: grid; place-items: center; color: #787774; font-size: 12px; }
.analysis-table-total { min-height: 52px; background: #fff; color: #202020; font-size: 12px; }
.analysis-table-total b { font-weight: 650; }
.analysis-table-pagination { min-height: 54px; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 9px 16px; border-top: 1px solid #e5e3df; background: #fafaf9; color: #787774; font-size: 11px; }
.analysis-table-pagination > div { display: flex; align-items: center; gap: 10px; }
.analysis-table-pagination button { height: 30px; padding: 0 11px; border: 1px solid #d8d5d0; border-radius: 7px; background: #fff; color: #37352f; font: inherit; font-size: 11px; cursor: pointer; }
.analysis-table-pagination button:disabled { color: #b8b6b2; cursor: not-allowed; background: #f6f5f4; }
@media (max-width: 980px) {
  .analysis-table-titlebar { align-items: stretch; flex-direction: column; }.analysis-table-header-actions { width: 100%; justify-content: space-between; flex-wrap: wrap; }.analysis-table-tools { min-width: min(100%,310px); flex: 1 1 310px; }.module-date-filter { min-width: 0; flex: 1 1 330px; }.analysis-table-search { width: 100%; }.analysis-attention-control { margin-left: auto; }.analysis-table-head { display: none; }.analysis-table-row,.analysis-table-total { grid-template-columns: repeat(3,minmax(0,1fr)); gap: 10px 12px; padding: 12px 14px; }.analysis-entity,.analysis-table-total > :first-child { grid-column: 1 / -1; }.analysis-table-row > span,.analysis-table-total > :not(:first-child) { min-width: 0; display: flex; align-items: center; justify-content: space-between; gap: 6px; text-align: right !important; }.analysis-table-row > span::before,.analysis-table-total > :not(:first-child)::before { content: attr(data-label); color: #9b9a97; font-size: 9px; font-weight: 500; }.analysis-status { justify-self: stretch; width: 100%; justify-content: flex-end; }.analysis-table-pagination { align-items: flex-start; flex-direction: column; }
}
@media (max-width: 480px) {
  .analysis-table-row,.analysis-table-total { grid-template-columns: repeat(2,minmax(0,1fr)); }.analysis-table-tools { align-items: stretch; flex-direction: column; }.analysis-table-count { width: fit-content; }.analysis-attention-control { width: 100%; justify-content: space-between; margin-left: 0; }
}
</style>
