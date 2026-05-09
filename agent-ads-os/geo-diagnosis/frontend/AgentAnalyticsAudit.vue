<script setup lang="ts">
import { computed, ref } from 'vue'
import { GeoDiagnosisClient } from './client'
import type { GeoAuditReport } from './types'

const client = new GeoDiagnosisClient()
const form = ref({
  brand: 'Candy Blast',
  url: 'https://candyblast.example',
  category: 'Mobile Puzzle Game',
  competitors: 'Royal Match, Candy Crush',
  market: 'US casual gamers',
})
const loading = ref(false)
const error = ref('')
const report = ref<GeoAuditReport | null>(null)
const competitors = computed(() => form.value.competitors.split(/[,，\n]/).map(item => item.trim()).filter(Boolean))

const generateReport = async () => {
  loading.value = true
  error.value = ''
  try {
    report.value = await client.createAudit({
      brand: form.value.brand,
      url: form.value.url,
      category: form.value.category,
      competitors: competitors.value,
      market: form.value.market,
    })
  } catch (err: any) {
    error.value = err?.message || '生成 GEO 诊断失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="min-h-screen bg-slate-950 p-6 text-slate-100">
    <section class="mx-auto grid max-w-6xl grid-cols-[320px_1fr] gap-6">
      <form class="space-y-4" @submit.prevent="generateReport">
        <input v-model="form.brand" class="w-full rounded-md border border-slate-700 bg-slate-900 p-3" />
        <input v-model="form.url" class="w-full rounded-md border border-slate-700 bg-slate-900 p-3" />
        <input v-model="form.category" class="w-full rounded-md border border-slate-700 bg-slate-900 p-3" />
        <textarea v-model="form.competitors" class="min-h-24 w-full rounded-md border border-slate-700 bg-slate-900 p-3" />
        <input v-model="form.market" class="w-full rounded-md border border-slate-700 bg-slate-900 p-3" />
        <button class="w-full rounded-md bg-emerald-400 p-3 font-bold text-slate-950">
          {{ loading ? '生成中...' : '生成 GEO 诊断' }}
        </button>
        <p v-if="error" class="text-sm text-red-300">{{ error }}</p>
      </form>

      <section class="rounded-md border border-slate-800 bg-slate-900 p-5">
        <div v-if="!report" class="text-slate-500">生成后显示诊断报告。</div>
        <div v-else>
          <h1 class="text-2xl font-bold">{{ report.input.brand }} GEO Diagnosis</h1>
          <div class="mt-5 grid grid-cols-4 gap-3">
            <div class="rounded-md border border-slate-800 p-3">Readiness: {{ report.scores.geo_readiness }}</div>
            <div class="rounded-md border border-slate-800 p-3">Mention: {{ report.scores.mention_rate }}%</div>
            <div class="rounded-md border border-slate-800 p-3">Citation: {{ report.scores.citation_rate }}%</div>
            <div class="rounded-md border border-slate-800 p-3">Leader: {{ report.competitor_leader }}</div>
          </div>
          <pre class="mt-5 max-h-96 overflow-auto rounded-md bg-slate-950 p-4 text-xs">{{ JSON.stringify(report.offer_json, null, 2) }}</pre>
        </div>
      </section>
    </section>
  </main>
</template>
